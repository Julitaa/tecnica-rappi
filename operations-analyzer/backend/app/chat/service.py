"""ChatService: orchestrates LLM + toolbox tool-calling loop."""
from __future__ import annotations
import json
import logging
from collections import defaultdict
from typing import AsyncIterator
from app.chat.toolbox import Toolbox
from app.chat.sandbox import SqlSandbox, SqlValidationError
from app.chat.schemas import TOOL_SCHEMAS
from app.chat.prompts import build_system_prompt
from app.data.repository import Repository
from app.llm.client import get_llm

log = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5
MAX_HISTORY_MESSAGES = 10


class ChatService:
    def __init__(self, repo: Repository):
        self.repo = repo
        self.toolbox = Toolbox(repo)
        self.sandbox = SqlSandbox(repo.metrics, repo.orders)
        self.llm = get_llm()
        self._history: dict[str, list[dict]] = defaultdict(list)
        self._system = {"role": "system", "content": build_system_prompt()}

    def reset(self, session_id: str) -> None:
        self._history.pop(session_id, None)

    def _dispatch_tool(self, name: str, args: dict) -> dict:
        try:
            if name == "top_n_zones":
                return self.toolbox.top_n_zones(**args)
            if name == "compare_segments":
                return self.toolbox.compare_segments(**args)
            if name == "metric_trend":
                return self.toolbox.metric_trend(**args)
            if name == "aggregate":
                return self.toolbox.aggregate(**args)
            if name == "multivariable_filter":
                return self.toolbox.multivariable_filter(**args)
            if name == "correlate_metrics":
                return self.toolbox.correlate_metrics(**args)
            if name == "growth_explainer":
                return self.toolbox.growth_explainer(**args)
            if name == "run_sql":
                return self.sandbox.run(**args)
            return {"error": f"Tool desconocida: {name}"}
        except SqlValidationError as e:
            return {"error": f"SQL inválido: {e}"}
        except Exception as e:
            log.exception("Tool %s failed", name)
            return {"error": f"Error ejecutando {name}: {e}"}

    async def chat_stream(self, session_id: str, user_msg: str) -> AsyncIterator[dict]:
        """Yields events: {type: 'token', content: str} | {type: 'tool', name: str}
        | {type: 'done', sources: [...], suggestions: [...]}"""
        history = self._history[session_id]
        history.append({"role": "user", "content": user_msg})
        history[:] = history[-MAX_HISTORY_MESSAGES:]
        messages = [self._system] + history
        tools_used: list[str] = []

        for iteration in range(MAX_TOOL_ITERATIONS):
            resp = await self.llm.chat(
                messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto",
            )
            choice = resp.choices[0]
            msg = choice.message
            if msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name,
                                      "arguments": tc.function.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments or "{}")
                    tools_used.append(name)
                    yield {"type": "tool", "name": name, "args": args}
                    result = self._dispatch_tool(name, args)
                    messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str)[:8000],
                    })
                continue
            # No more tool calls → final answer
            final_text = msg.content or ""
            yield {"type": "token", "content": final_text}
            history.append({"role": "assistant", "content": final_text})
            suggestions = await self._suggest_followups(user_msg, tools_used)
            yield {"type": "done", "sources": tools_used,
                   "suggestions": suggestions}
            return

        yield {"type": "token",
               "content": "(Se alcanzó el límite de iteraciones de tools.)"}
        yield {"type": "done", "sources": tools_used, "suggestions": []}

    async def _suggest_followups(self, last_q: str, tools: list[str]) -> list[str]:
        try:
            resp = await self.llm.chat(
                messages=[
                    {"role": "system",
                     "content": "Devolvé JSON con sugerencias de follow-up."},
                    {"role": "user",
                     "content": f"Pregunta: {last_q}\nTools usadas: {tools}\n"
                                f"Devolvé {{\"suggestions\": [\"...\", \"...\"]}} "
                                f"con 2 follow-ups cortos en español."},
                ],
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            return json.loads(content).get("suggestions", [])[:2]
        except Exception:
            return []
