import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.data.loader import load_data
from app.data.repository import Repository
from app.chat.service import ChatService
from app.api.schemas import ChatRequest, ResetRequest

logging.basicConfig(level=settings.log_level)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading data...")
    metrics_df, orders_df = load_data(settings.data_path, settings.cache_path)
    app.state.repo = Repository(metrics_df, orders_df)
    app.state.chat = ChatService(app.state.repo)
    log.info("Data loaded: metrics=%s orders=%s", metrics_df.shape, orders_df.shape)
    yield


app = FastAPI(title="Operations Analyzer API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"], allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats(request: Request):
    repo: Repository = request.app.state.repo
    return {
        "countries": repo.list_countries(),
        "zones_count": len(repo.list_zones()),
        "metrics": repo.list_metrics(),
    }


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    chat_service: ChatService = request.app.state.chat

    async def event_gen():
        async for ev in chat_service.chat_stream(req.session_id, req.message):
            yield {"data": json.dumps(ev, ensure_ascii=False)}

    return EventSourceResponse(event_gen())


@app.post("/chat/reset")
def chat_reset(req: ResetRequest, request: Request):
    request.app.state.chat.reset(req.session_id)
    return {"ok": True}
