import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data.loader import load_data
from app.data.repository import Repository

logging.basicConfig(level=settings.log_level)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading data...")
    metrics_df, orders_df = load_data(settings.data_path, settings.cache_path)
    app.state.repo = Repository(metrics_df, orders_df)
    log.info("Data loaded: metrics=%s orders=%s", metrics_df.shape, orders_df.shape)
    yield


app = FastAPI(title="Operations Analyzer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
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
