"""Run the 6 brief questions against the chat service and print answers."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.data.loader import load_data
from app.data.repository import Repository
from app.chat.service import ChatService

QUESTIONS = [
    "¿Cuáles son las 5 zonas con mayor % Lead Penetration esta semana?",
    "Compará el Perfect Order entre zonas Wealthy y Non Wealthy en México",
    "Mostrá la evolución de Gross Profit UE en Chapinero últimas 8 semanas",
    "¿Cuál es el promedio de Lead Penetration por país?",
    "¿Qué zonas tienen alto Lead Penetration pero bajo Perfect Order?",
    "¿Cuáles son las zonas que más crecen en órdenes en las últimas 5 semanas y qué podría explicar el crecimiento?",
]


async def main():
    metrics_df, orders_df = load_data(settings.data_path, settings.cache_path)
    repo = Repository(metrics_df, orders_df)
    chat = ChatService(repo)
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n===== Q{i}: {q} =====")
        answer = ""
        tools: list[str] = []
        async for ev in chat.chat_stream(f"smoke-{i}", q):
            if ev["type"] == "token":
                answer += ev["content"]
            elif ev["type"] == "tool":
                tools.append(ev["name"])
        print(f"Tools: {tools}")
        print(f"Answer:\n{answer}")


if __name__ == "__main__":
    asyncio.run(main())
