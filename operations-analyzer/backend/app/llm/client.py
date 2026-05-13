"""Thin wrapper over OpenAI client with a mock mode for development."""
from __future__ import annotations
from typing import Any, AsyncIterator
import logging
from openai import AsyncOpenAI
from app.config import settings

log = logging.getLogger(__name__)


class LLMClient:
    """Wrapper over AsyncOpenAI.

    When ``settings.use_mock_llm`` is True, the client does not make any
    network calls; chat() and chat_stream() return deterministic placeholders.
    This allows the rest of the system to be built and tested without
    consuming API credits.
    """

    def __init__(self) -> None:
        self.model = settings.openai_model
        self.mock = settings.use_mock_llm
        self._client: AsyncOpenAI | None = (
            None if self.mock else AsyncOpenAI(api_key=settings.openai_api_key)
        )

    @property
    def client(self) -> AsyncOpenAI:
        """Underlying AsyncOpenAI; raises if running in mock mode."""
        if self._client is None:
            raise RuntimeError(
                "LLMClient is in mock mode; use chat()/chat_stream() instead "
                "of accessing the underlying client directly."
            )
        return self._client

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        if self.mock:
            return self._mock_completion()
        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            params["tools"] = tools
        params.update(kwargs)
        return await self._client.chat.completions.create(**params)

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[Any]:
        if self.mock:
            for chunk in self._mock_stream():
                yield chunk
            return
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
        resp = await self._client.chat.completions.create(**kwargs)
        async for chunk in resp:
            yield chunk

    # ----- mock helpers -----------------------------------------------
    @staticmethod
    def _mock_completion() -> Any:
        message = type(
            "MockMessage",
            (),
            {"content": "[mock] respuesta de prueba", "tool_calls": None},
        )
        choice = type("MockChoice", (), {"message": message})
        return type("MockCompletion", (), {"choices": [choice]})

    @staticmethod
    def _mock_stream() -> list[dict]:
        return [
            {"type": "content", "delta": "[mock] respuesta"},
            {"type": "done"},
        ]


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    """Return the process-wide LLMClient singleton."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
