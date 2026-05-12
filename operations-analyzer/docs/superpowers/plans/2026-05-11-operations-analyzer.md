# Operations Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir bot conversacional de datos + sistema de insights automáticos sobre métricas operacionales Rappi, con frontend Next.js y backend FastAPI.

**Architecture:** Backend FastAPI con tool-calling híbrido (toolbox de 8 funciones + sandbox SQL DuckDB) sobre pandas in-memory. Insights determinísticos en pandas + LLM redacta narrativa → PDF. Frontend Next.js consume SSE para chat y endpoint REST para reporte.

**Tech Stack:** Python 3.11, FastAPI, pandas, DuckDB, OpenAI (gpt-4o), weasyprint, sqlglot, pytest, uv. Next.js 14 (App Router), TypeScript, TailwindCSS, shadcn/ui, react-markdown, pnpm.

**Spec:** [docs/superpowers/specs/2026-05-11-operations-analyzer-design.md](../specs/2026-05-11-operations-analyzer-design.md)

---

## Phases

- **Phase 0** — Project scaffolding (backend + frontend skeletons)
- **Phase 1** — Data layer (loader, glossary, repository)
- **Phase 2** — LLM client + chat toolbox (8 tools)
- **Phase 3** — SQL sandbox + ChatService
- **Phase 4** — FastAPI chat endpoint (SSE streaming)
- **Phase 5** — Insights detectors (5 categorías)
- **Phase 6** — Insights ranker + reporter + PDF
- **Phase 7** — FastAPI report endpoint
- **Phase 8** — Frontend chat UI
- **Phase 9** — Frontend report panel
- **Phase 10** — Smoke test + README + polish

Each phase is committable independently. Recommended commit per task.

---

## Phase 0 — Scaffolding

### Task 0.1: Backend project skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/app/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/main.py`

- [ ] **Step 1: Init backend with uv**

Run from `operations-analyzer/`:
```powershell
cd backend
uv init --no-readme --no-pin-python
```

- [ ] **Step 2: Edit `backend/pyproject.toml`**

```toml
[project]
name = "operations-analyzer-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pandas>=2.2",
    "openpyxl>=3.1",
    "pyarrow>=18.0",
    "duckdb>=1.1",
    "sqlglot>=25.0",
    "openai>=1.54",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "python-dotenv>=1.0",
    "markdown>=3.7",
    "weasyprint>=63.0",
    "sse-starlette>=2.1",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "ruff>=0.7",
]

[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
```

- [ ] **Step 3: Create `.env.example`**

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
USE_MOCK_LLM=false
DATA_PATH=data/source.xlsx
CACHE_PATH=data/cache.parquet
LOG_LEVEL=INFO
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.env
data/cache.parquet
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 5: Create FastAPI hello-world in `backend/app/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Operations Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Install deps and run server**

```powershell
uv sync
uv run uvicorn app.api.main:app --reload
```

Expected: server starts on `http://127.0.0.1:8000`, `GET /health` returns `{"status":"ok"}`.

- [ ] **Step 7: Commit**

```powershell
cd ..
git add backend/
git commit -m "chore: backend scaffolding with FastAPI hello-world"
```

---

### Task 0.2: Move source Excel into backend/data

**Files:**
- Move: existing `.xlsx` → `backend/data/source.xlsx`

- [ ] **Step 1: Move file**

```powershell
mkdir backend/data
Move-Item "Sistema de Análisis Inteligente para Operaciones Rappi - Dummy Data*.xlsx" backend/data/source.xlsx
```

- [ ] **Step 2: Commit**

```powershell
git add backend/data/source.xlsx
git commit -m "chore: move source xlsx into backend/data"
```

---

### Task 0.3: Frontend project skeleton

**Files:**
- Create: `frontend/` (via `create-next-app`)

- [ ] **Step 1: Scaffold Next.js**

```powershell
cd operations-analyzer
pnpm create next-app@latest frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*" --eslint --turbopack
```

- [ ] **Step 2: Add shadcn/ui + extra deps**

```powershell
cd frontend
pnpm dlx shadcn@latest init -d
pnpm dlx shadcn@latest add button input card scroll-area
pnpm add react-markdown remark-gfm uuid
pnpm add -D @types/uuid
```

- [ ] **Step 3: Configure Rappi palette in `frontend/tailwind.config.ts`**

Edit `theme.extend.colors`:
```ts
colors: {
  rappi: {
    DEFAULT: "#FF441F",
    primary: "#FF441F",
    primaryDark: "#E03515",
  },
},
```

- [ ] **Step 4: Verify dev server runs**

```powershell
pnpm dev
```

Open `http://localhost:3000`. Default Next.js page should load.

- [ ] **Step 5: Commit**

```powershell
cd ..
git add frontend/
git commit -m "chore: frontend scaffolding with Next.js + shadcn + Rappi palette"
```

---

## Phase 1 — Data layer

### Task 1.1: Glossary (`data/glossary.py`)

**Files:**
- Create: `backend/app/data/__init__.py`
- Create: `backend/app/data/glossary.py`
- Test: `backend/tests/test_glossary.py`

- [ ] **Step 1: Write failing test `backend/tests/test_glossary.py`**

```python
from app.data.glossary import GLOSSARY, get_glossary_entry

def test_glossary_has_all_required_metrics():
    required = {
        "% PRO Users Who Breakeven",
        "% Restaurants Sessions With Optimal Assortment",
        "Gross Profit UE",
        "Lead Penetration",
        "MLTV Top Verticals Adoption",
        "Non-Pro PTC > OP",
        "Perfect Orders",
        "Pro Adoption",
        "Restaurants Markdowns / GMV",
        "Restaurants SS > ATC CVR",
        "Restaurants SST > SS CVR",
        "Retail SST > SS CVR",
        "Turbo Adoption",
    }
    assert required.issubset(set(GLOSSARY.keys()))

def test_each_entry_has_required_fields():
    for name, entry in GLOSSARY.items():
        assert "description" in entry, f"{name} missing description"
        assert "higher_is_better" in entry, f"{name} missing higher_is_better"
        assert "format" in entry, f"{name} missing format"

def test_get_glossary_entry_returns_none_for_unknown():
    assert get_glossary_entry("Nonexistent Metric") is None

def test_get_glossary_entry_returns_dict_for_known():
    entry = get_glossary_entry("Lead Penetration")
    assert entry is not None
    assert entry["higher_is_better"] is True
```

- [ ] **Step 2: Run test, verify fails**

```powershell
cd backend
uv run pytest tests/test_glossary.py -v
```

Expected: ImportError / ModuleNotFoundError.

- [ ] **Step 3: Implement `backend/app/data/glossary.py`**

```python
"""Metric glossary with business semantics."""

GLOSSARY: dict[str, dict] = {
    "% PRO Users Who Breakeven": {
        "description": "Usuarios Pro cuyo valor generado cubre el costo de su membresía / Total usuarios Pro.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Pro",
    },
    "% Restaurants Sessions With Optimal Assortment": {
        "description": "Sesiones con ≥40 restaurantes / Total sesiones.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Restaurants",
    },
    "Gross Profit UE": {
        "description": "Margen bruto de ganancia / Total de órdenes.",
        "higher_is_better": True,
        "format": "currency",
        "category": "Unit Economics",
    },
    "Lead Penetration": {
        "description": "Tiendas habilitadas / (leads + habilitadas + salidas).",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Supply",
    },
    "MLTV Top Verticals Adoption": {
        "description": "Usuarios con órdenes en múltiples verticales / Total usuarios.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Verticals",
    },
    "Non-Pro PTC > OP": {
        "description": "Conversión No-Pro de Proceed to Checkout a Order Placed.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Conversion",
    },
    "Perfect Orders": {
        "description": "Órdenes sin cancelaciones/defectos/demoras / Total órdenes.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Quality",
    },
    "Pro Adoption": {
        "description": "Usuarios Pro / Total usuarios.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Pro",
    },
    "Restaurants Markdowns / GMV": {
        "description": "Descuentos en órdenes restaurantes / GMV Restaurantes.",
        "higher_is_better": False,
        "format": "percentage",
        "category": "Restaurants",
    },
    "Restaurants SS > ATC CVR": {
        "description": "Conversión Select Store a Add to Cart en restaurantes.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Conversion",
    },
    "Restaurants SST > SS CVR": {
        "description": "Conversión Store Selection Type a Select Store en restaurantes.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Conversion",
    },
    "Retail SST > SS CVR": {
        "description": "Conversión Store Selection Type a Select Store en retail.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Conversion",
    },
    "Turbo Adoption": {
        "description": "Usuarios que compran en Turbo / Total usuarios con Turbo disponible.",
        "higher_is_better": True,
        "format": "percentage",
        "category": "Verticals",
    },
    "Orders": {
        "description": "Volumen total de órdenes en la zona.",
        "higher_is_better": True,
        "format": "integer",
        "category": "Volume",
    },
}


def get_glossary_entry(metric_name: str) -> dict | None:
    return GLOSSARY.get(metric_name)


def glossary_for_prompt() -> str:
    """Format glossary as compact string for LLM system prompt."""
    lines = []
    for name, entry in GLOSSARY.items():
        direction = "↑ mejor" if entry["higher_is_better"] else "↓ mejor"
        lines.append(f"- **{name}** ({direction}): {entry['description']}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests, verify pass**

```powershell
uv run pytest tests/test_glossary.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
cd ..
git add backend/app/data/ backend/tests/
git commit -m "feat(data): metric glossary with business semantics"
```

---

### Task 1.2: Loader (`data/loader.py`)

**Files:**
- Create: `backend/app/data/loader.py`
- Test: `backend/tests/test_loader.py`

- [ ] **Step 1: Write failing test `backend/tests/test_loader.py`**

```python
import pandas as pd
from pathlib import Path
from app.data.loader import load_data, pivot_wide_to_long

def test_pivot_wide_to_long():
    wide = pd.DataFrame([{
        "COUNTRY": "CO", "CITY": "Bogota", "ZONE": "Chapinero",
        "ZONE_TYPE": "Wealthy", "ZONE_PRIORITIZATION": "High Priority",
        "METRIC": "Lead Penetration",
        "L8W_VALUE": 0.1, "L7W_VALUE": 0.2, "L6W_VALUE": 0.3,
        "L5W_VALUE": 0.4, "L4W_VALUE": 0.5, "L3W_VALUE": 0.6,
        "L2W_VALUE": 0.7, "L1W_VALUE": 0.8, "L0W_VALUE": 0.9,
    }])
    long = pivot_wide_to_long(wide)
    assert len(long) == 9
    assert set(long["week_offset"]) == set(range(9))
    row_l0w = long[long["week_offset"] == 0].iloc[0]
    assert row_l0w["value"] == 0.9
    row_l8w = long[long["week_offset"] == 8].iloc[0]
    assert row_l8w["value"] == 0.1

def test_load_data_returns_two_dataframes(tmp_path):
    # Build a tiny xlsx fixture
    metrics_wide = pd.DataFrame([{
        "COUNTRY": "CO", "CITY": "Bogota", "ZONE": "Chapinero",
        "ZONE_TYPE": "Wealthy", "ZONE_PRIORITIZATION": "High Priority",
        "METRIC": "Lead Penetration",
        **{f"L{i}W_VALUE": 0.5 for i in range(9)},
    }])
    orders_wide = pd.DataFrame([{
        "COUNTRY": "CO", "CITY": "Bogota", "ZONE": "Chapinero",
        "METRIC": "Orders",
        **{f"L{i}W": 1000 for i in range(9)},
    }])
    xlsx_path = tmp_path / "fixture.xlsx"
    with pd.ExcelWriter(xlsx_path) as w:
        metrics_wide.to_excel(w, sheet_name="RAW_INPUT_METRICS", index=False)
        orders_wide.to_excel(w, sheet_name="RAW_ORDERS", index=False)
    cache_path = tmp_path / "cache.parquet"
    metrics_df, orders_df = load_data(xlsx_path, cache_path)
    assert len(metrics_df) == 9
    assert len(orders_df) == 9
    assert "week_offset" in metrics_df.columns
    assert "value" in metrics_df.columns
```

- [ ] **Step 2: Run test, verify fails**

```powershell
uv run pytest tests/test_loader.py -v
```

- [ ] **Step 3: Implement `backend/app/data/loader.py`**

```python
"""Load Excel source, pivot wide→long, cache to Parquet."""
from pathlib import Path
import logging
import pandas as pd

log = logging.getLogger(__name__)

METRICS_SHEET = "RAW_INPUT_METRICS"
ORDERS_SHEET = "RAW_ORDERS"

WEEK_COLS_METRICS = [f"L{i}W_VALUE" for i in range(9)]  # rolling cols use _VALUE or _ROLL
WEEK_COLS_METRICS_ALT = [f"L{i}W_ROLL" for i in range(9)]
WEEK_COLS_ORDERS = [f"L{i}W" for i in range(9)]


def _detect_week_cols(df: pd.DataFrame) -> list[str]:
    if all(c in df.columns for c in WEEK_COLS_METRICS):
        return WEEK_COLS_METRICS
    if all(c in df.columns for c in WEEK_COLS_METRICS_ALT):
        return WEEK_COLS_METRICS_ALT
    if all(c in df.columns for c in WEEK_COLS_ORDERS):
        return WEEK_COLS_ORDERS
    raise ValueError(f"No week columns recognized. Got: {list(df.columns)}")


def pivot_wide_to_long(df: pd.DataFrame) -> pd.DataFrame:
    week_cols = _detect_week_cols(df)
    id_cols = [c for c in df.columns if c not in week_cols]
    long = df.melt(id_vars=id_cols, value_vars=week_cols,
                   var_name="week_col", value_name="value")
    # Extract offset: "L3W_VALUE" -> 3
    long["week_offset"] = long["week_col"].str.extract(r"L(\d+)W").astype(int)
    long = long.drop(columns=["week_col"])
    # Normalize column names to lowercase snake
    rename_map = {
        "COUNTRY": "country", "CITY": "city", "ZONE": "zone",
        "ZONE_TYPE": "zone_type", "ZONE_PRIORITIZATION": "zone_prioritization",
        "METRIC": "metric",
    }
    long = long.rename(columns={k: v for k, v in rename_map.items() if k in long.columns})
    return long


def _validate(df: pd.DataFrame, name: str) -> None:
    nulls = df["value"].isna().sum()
    if nulls:
        log.warning("%s: %d null values", name, nulls)
    negatives = (df["value"] < 0).sum()
    if negatives:
        log.warning("%s: %d negative values", name, negatives)


def load_data(xlsx_path: Path, cache_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    xlsx_path, cache_path = Path(xlsx_path), Path(cache_path)
    metrics_cache = cache_path.with_name("metrics_" + cache_path.name)
    orders_cache = cache_path.with_name("orders_" + cache_path.name)
    if metrics_cache.exists() and orders_cache.exists():
        log.info("Loading from parquet cache")
        return pd.read_parquet(metrics_cache), pd.read_parquet(orders_cache)
    log.info("Loading from xlsx and caching")
    metrics_wide = pd.read_excel(xlsx_path, sheet_name=METRICS_SHEET)
    orders_wide = pd.read_excel(xlsx_path, sheet_name=ORDERS_SHEET)
    metrics_df = pivot_wide_to_long(metrics_wide)
    orders_df = pivot_wide_to_long(orders_wide)
    _validate(metrics_df, "metrics")
    _validate(orders_df, "orders")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_parquet(metrics_cache)
    orders_df.to_parquet(orders_cache)
    return metrics_df, orders_df
```

- [ ] **Step 4: Run tests, verify pass**

```powershell
uv run pytest tests/test_loader.py -v
```

- [ ] **Step 5: Smoke-test against real Excel**

```powershell
uv run python -c "from pathlib import Path; from app.data.loader import load_data; m, o = load_data(Path('data/source.xlsx'), Path('data/cache.parquet')); print('metrics:', m.shape, 'orders:', o.shape); print(m.head())"
```

Expected: prints shapes and head with `week_offset`, `value` cols.

- [ ] **Step 6: Commit**

```powershell
cd ..
git add backend/app/data/loader.py backend/tests/test_loader.py
git commit -m "feat(data): excel loader with wide→long pivot and parquet cache"
```

---

### Task 1.3: Repository (`data/repository.py`)

**Files:**
- Create: `backend/app/data/repository.py`
- Test: `backend/tests/test_repository.py`

- [ ] **Step 1: Write failing test `backend/tests/test_repository.py`**

```python
import pandas as pd
import pytest
from app.data.repository import Repository

@pytest.fixture
def repo():
    metrics = pd.DataFrame([
        {"country": "CO", "city": "Bogota", "zone": "Chapinero",
         "zone_type": "Wealthy", "zone_prioritization": "High Priority",
         "metric": "Lead Penetration", "week_offset": w, "value": 0.5 + w*0.01}
        for w in range(9)
    ] + [
        {"country": "MX", "city": "CDMX", "zone": "Roma",
         "zone_type": "Wealthy", "zone_prioritization": "Prioritized",
         "metric": "Lead Penetration", "week_offset": w, "value": 0.7}
        for w in range(9)
    ])
    orders = pd.DataFrame([
        {"country": "CO", "city": "Bogota", "zone": "Chapinero",
         "metric": "Orders", "week_offset": w, "value": 1000 + w*10}
        for w in range(9)
    ])
    return Repository(metrics, orders)

def test_list_countries(repo):
    assert set(repo.list_countries()) == {"CO", "MX"}

def test_list_zones_filtered(repo):
    zones = repo.list_zones(country="CO")
    assert zones == ["Chapinero"]

def test_get_metric_series(repo):
    series = repo.get_metric_series("CO", "Chapinero", "Lead Penetration")
    assert len(series) == 9
    assert series[0] == pytest.approx(0.5)  # L8W
    assert series[8] == pytest.approx(0.58)  # L0W

def test_get_metric_series_unknown_returns_empty(repo):
    assert repo.get_metric_series("XX", "Nowhere", "Lead Penetration") == []

def test_combined_view_joins_zone_metadata_to_orders(repo):
    view = repo.combined_view()
    chap = view[(view["zone"] == "Chapinero") & (view["metric"] == "Orders")]
    assert (chap["zone_type"] == "Wealthy").all()
```

- [ ] **Step 2: Run test, verify fails**

- [ ] **Step 3: Implement `backend/app/data/repository.py`**

```python
"""Typed facade over the two pandas DataFrames."""
from __future__ import annotations
import pandas as pd


class Repository:
    def __init__(self, metrics_df: pd.DataFrame, orders_df: pd.DataFrame):
        self._metrics = metrics_df
        self._orders = orders_df

    @property
    def metrics(self) -> pd.DataFrame:
        return self._metrics

    @property
    def orders(self) -> pd.DataFrame:
        return self._orders

    def list_countries(self) -> list[str]:
        return sorted(self._metrics["country"].unique().tolist())

    def list_zones(self, country: str | None = None,
                   zone_type: str | None = None) -> list[str]:
        df = self._metrics
        if country:
            df = df[df["country"] == country]
        if zone_type:
            df = df[df["zone_type"] == zone_type]
        return sorted(df["zone"].unique().tolist())

    def list_metrics(self) -> list[str]:
        return sorted(self._metrics["metric"].unique().tolist())

    def get_metric_series(self, country: str, zone: str, metric: str) -> list[float]:
        """Return list of 9 values ordered from L8W (oldest) to L0W (latest)."""
        df = self._metrics[
            (self._metrics["country"] == country)
            & (self._metrics["zone"] == zone)
            & (self._metrics["metric"] == metric)
        ].sort_values("week_offset", ascending=False)
        return df["value"].tolist()

    def combined_view(self) -> pd.DataFrame:
        """Orders joined with zone metadata from metrics."""
        zone_meta = (self._metrics[["country", "city", "zone",
                                    "zone_type", "zone_prioritization"]]
                     .drop_duplicates())
        return self._orders.merge(zone_meta, on=["country", "city", "zone"], how="left")
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```powershell
cd ..
git add backend/app/data/repository.py backend/tests/test_repository.py
git commit -m "feat(data): repository facade over pandas DataFrames"
```

---

### Task 1.4: Wire data loading into FastAPI lifespan

**Files:**
- Modify: `backend/app/api/main.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: Create `backend/app/config.py`**

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    use_mock_llm: bool = False
    data_path: Path = Path("data/source.xlsx")
    cache_path: Path = Path("data/cache.parquet")
    log_level: str = "INFO"


settings = Settings()
```

- [ ] **Step 2: Update `backend/app/api/main.py`**

```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
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
def stats(request):
    repo = request.app.state.repo
    return {
        "countries": repo.list_countries(),
        "zones_count": len(repo.list_zones()),
        "metrics": repo.list_metrics(),
    }
```

Note: FastAPI requires `Request` injection for state access. Fix the import.

```python
from fastapi import FastAPI, Request
# ...
@app.get("/stats")
def stats(request: Request):
    ...
```

- [ ] **Step 3: Start server and check**

```powershell
uv run uvicorn app.api.main:app --reload
```

Visit `http://127.0.0.1:8000/stats`. Expected: JSON with countries list, zone count >0, ~13-14 metrics.

- [ ] **Step 4: Commit**

```powershell
cd ..
git add backend/app/config.py backend/app/api/main.py
git commit -m "feat(api): wire data loader into FastAPI lifespan"
```

---

## Phase 2 — LLM client + Chat Toolbox

### Task 2.1: LLM client wrapper

**Files:**
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/client.py`

- [ ] **Step 1: Implement `backend/app/llm/client.py`**

```python
"""Thin wrapper over OpenAI client with mock mode."""
from __future__ import annotations
from typing import Any, AsyncIterator
import json
import logging
from openai import AsyncOpenAI
from app.config import settings

log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.model = settings.openai_model
        self.mock = settings.use_mock_llm
        self._client = None if self.mock else AsyncOpenAI(api_key=settings.openai_api_key)

    async def chat(self, messages: list[dict], tools: list[dict] | None = None,
                   stream: bool = False) -> Any:
        if self.mock:
            return self._mock_response(messages, tools)
        return await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=stream,
        )

    async def chat_stream(self, messages: list[dict],
                          tools: list[dict] | None = None) -> AsyncIterator:
        if self.mock:
            yield {"type": "content", "delta": "[mock] respuesta de demo"}
            yield {"type": "done"}
            return
        resp = await self._client.chat.completions.create(
            model=self.model, messages=messages, tools=tools, stream=True,
        )
        async for chunk in resp:
            yield chunk

    def _mock_response(self, messages, tools):
        # Minimal: pretend the LLM called the first tool with empty args
        class _Mock:
            choices = [type("C", (), {"message": type("M", (), {
                "content": "[mock] respuesta",
                "tool_calls": None,
            })})]
        return _Mock()


_client: LLMClient | None = None

def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
```

- [ ] **Step 2: Commit**

```powershell
git add backend/app/llm/
git commit -m "feat(llm): OpenAI client wrapper with mock mode"
```

---

### Task 2.2: Toolbox skeleton + schemas

**Files:**
- Create: `backend/app/chat/__init__.py`
- Create: `backend/app/chat/toolbox.py`
- Test: `backend/tests/test_toolbox.py`

- [ ] **Step 1: Write failing test (only first tool) `backend/tests/test_toolbox.py`**

```python
import pandas as pd
import pytest
from app.data.repository import Repository
from app.chat.toolbox import Toolbox

@pytest.fixture
def repo():
    rows = []
    for country in ["CO", "MX"]:
        for zone_n in range(3):
            for w in range(9):
                rows.append({
                    "country": country, "city": f"City-{country}",
                    "zone": f"{country}_zone_{zone_n}",
                    "zone_type": "Wealthy" if zone_n % 2 == 0 else "Non Wealthy",
                    "zone_prioritization": "High Priority",
                    "metric": "Lead Penetration",
                    "week_offset": w,
                    "value": 0.1 * (zone_n + 1) + 0.01 * (8 - w),
                })
    metrics = pd.DataFrame(rows)
    orders = pd.DataFrame()
    return Repository(metrics, orders)

@pytest.fixture
def toolbox(repo):
    return Toolbox(repo)

def test_top_n_zones_returns_n(toolbox):
    result = toolbox.top_n_zones(metric="Lead Penetration", n=3)
    assert len(result["data"]) == 3
    assert "summary" in result

def test_top_n_zones_orders_descending(toolbox):
    result = toolbox.top_n_zones(metric="Lead Penetration", n=5, order="desc")
    values = [row["value"] for row in result["data"]]
    assert values == sorted(values, reverse=True)

def test_top_n_zones_with_country_filter(toolbox):
    result = toolbox.top_n_zones(metric="Lead Penetration", n=10,
                                  filters={"country": "CO"})
    countries = {row["country"] for row in result["data"]}
    assert countries == {"CO"}
```

- [ ] **Step 2: Run test, verify fails**

- [ ] **Step 3: Implement scaffold of Toolbox with `top_n_zones`**

```python
"""Toolbox of analysis functions callable by the LLM."""
from __future__ import annotations
from typing import Any
import pandas as pd
from app.data.repository import Repository


class Toolbox:
    def __init__(self, repo: Repository):
        self.repo = repo

    # ---- Tool 1: top_n_zones ----------------------------------------
    def top_n_zones(self, metric: str, n: int = 5, week_offset: int = 0,
                    filters: dict | None = None, order: str = "desc") -> dict:
        df = self._metrics_slice(metric, week_offset, filters)
        ascending = (order == "asc")
        df = df.sort_values("value", ascending=ascending).head(n)
        data = df[["country", "city", "zone", "zone_type", "value"]].to_dict("records")
        summary = (f"Top {n} zonas por {metric} (semana L{week_offset}W, orden={order}). "
                   f"{len(data)} resultados.")
        return {"data": data, "summary": summary, "metadata": {"metric": metric}}

    def _metrics_slice(self, metric: str, week_offset: int = 0,
                       filters: dict | None = None) -> pd.DataFrame:
        df = self.repo.metrics
        df = df[(df["metric"] == metric) & (df["week_offset"] == week_offset)]
        for k, v in (filters or {}).items():
            if k in df.columns:
                df = df[df[k] == v]
        return df
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```powershell
git add backend/app/chat/toolbox.py backend/tests/test_toolbox.py
git commit -m "feat(chat): toolbox scaffold with top_n_zones"
```

---

### Task 2.3: Add `compare_segments` + `metric_trend` + `aggregate`

**Files:**
- Modify: `backend/app/chat/toolbox.py`
- Modify: `backend/tests/test_toolbox.py`

- [ ] **Step 1: Add failing tests**

Append to `test_toolbox.py`:
```python
def test_compare_segments(toolbox):
    result = toolbox.compare_segments(
        metric="Lead Penetration",
        group_by="zone_type",
        filters={"country": "CO"},
    )
    groups = {row["zone_type"] for row in result["data"]}
    assert groups == {"Wealthy", "Non Wealthy"}
    for row in result["data"]:
        assert "mean" in row and "count" in row

def test_metric_trend_returns_9_weeks(toolbox):
    result = toolbox.metric_trend(
        metric="Lead Penetration", country="CO", zone="CO_zone_0",
    )
    assert len(result["data"]) == 9
    # ordered chronologically: L8W..L0W
    offsets = [row["week_offset"] for row in result["data"]]
    assert offsets == list(range(8, -1, -1))

def test_aggregate_by_country(toolbox):
    result = toolbox.aggregate(
        metric="Lead Penetration", group_by="country", agg="mean",
    )
    countries = {row["country"] for row in result["data"]}
    assert countries == {"CO", "MX"}
```

- [ ] **Step 2: Run tests, verify fail**

- [ ] **Step 3: Implement methods in `toolbox.py`**

```python
    # ---- Tool 2: compare_segments -----------------------------------
    def compare_segments(self, metric: str, group_by: str,
                         filters: dict | None = None,
                         week_offset: int = 0) -> dict:
        df = self._metrics_slice(metric, week_offset, filters)
        if group_by not in df.columns:
            return {"data": [], "summary": f"Columna {group_by} no existe.",
                    "metadata": {}}
        grouped = (df.groupby(group_by)["value"]
                     .agg(["mean", "median", "std", "count"])
                     .reset_index())
        data = grouped.to_dict("records")
        summary = f"Comparación de {metric} agrupado por {group_by}: {len(data)} segmentos."
        return {"data": data, "summary": summary, "metadata": {"metric": metric}}

    # ---- Tool 3: metric_trend ---------------------------------------
    def metric_trend(self, metric: str, country: str, zone: str,
                     weeks: int = 9) -> dict:
        df = self.repo.metrics
        df = df[(df["metric"] == metric)
                & (df["country"] == country)
                & (df["zone"] == zone)]
        df = df.sort_values("week_offset", ascending=False).head(weeks)
        data = df[["week_offset", "value"]].to_dict("records")
        if not data:
            return {"data": [], "summary": f"Sin datos para {zone}/{metric}.",
                    "metadata": {}}
        delta = data[-1]["value"] - data[0]["value"]
        summary = (f"Evolución de {metric} en {zone} ({country}), "
                   f"últimas {len(data)} semanas. Δ total: {delta:+.4f}.")
        return {"data": data, "summary": summary, "metadata": {"metric": metric}}

    # ---- Tool 4: aggregate ------------------------------------------
    def aggregate(self, metric: str, group_by: str, agg: str = "mean",
                  filters: dict | None = None, week_offset: int = 0) -> dict:
        df = self._metrics_slice(metric, week_offset, filters)
        if group_by not in df.columns:
            return {"data": [], "summary": f"Columna {group_by} no existe.",
                    "metadata": {}}
        valid_aggs = {"mean", "median", "sum", "min", "max", "std"}
        if agg not in valid_aggs:
            agg = "mean"
        grouped = df.groupby(group_by)["value"].agg(agg).reset_index()
        data = grouped.to_dict("records")
        summary = f"{agg.capitalize()} de {metric} por {group_by}: {len(data)} grupos."
        return {"data": data, "summary": summary,
                "metadata": {"metric": metric, "agg": agg}}
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```powershell
git add backend/app/chat/toolbox.py backend/tests/test_toolbox.py
git commit -m "feat(chat): add compare_segments, metric_trend, aggregate tools"
```

---

### Task 2.4: Add `multivariable_filter` + `correlate_metrics`

**Files:**
- Modify: `backend/app/chat/toolbox.py`
- Modify: `backend/tests/test_toolbox.py`

- [ ] **Step 1: Add failing tests**

```python
def test_multivariable_filter(toolbox):
    # Need 2 metrics in fixture. Adjust fixture or use existing.
    # We have only Lead Penetration; add another metric in a local fixture:
    import pandas as pd
    from app.data.repository import Repository
    from app.chat.toolbox import Toolbox
    rows = []
    for country in ["CO"]:
        for zn in range(4):
            for metric, base in [("Lead Penetration", 0.1*(zn+1)),
                                 ("Perfect Orders", 0.9 - 0.1*zn)]:
                for w in range(9):
                    rows.append({
                        "country": country, "city": "X", "zone": f"z{zn}",
                        "zone_type": "Wealthy", "zone_prioritization": "Prioritized",
                        "metric": metric, "week_offset": w,
                        "value": base,
                    })
    repo = Repository(pd.DataFrame(rows), pd.DataFrame())
    tb = Toolbox(repo)
    result = tb.multivariable_filter(conditions=[
        {"metric": "Lead Penetration", "op": ">", "value": 0.2},
        {"metric": "Perfect Orders", "op": "<", "value": 0.85},
    ])
    zones = {row["zone"] for row in result["data"]}
    assert "z0" not in zones  # LP=0.1, fails first
    assert "z3" in zones      # LP=0.4>0.2 and PO=0.6<0.85

def test_correlate_metrics(toolbox):
    # Add a second metric inversely correlated to Lead Penetration
    import pandas as pd
    from app.data.repository import Repository
    from app.chat.toolbox import Toolbox
    rows = []
    for zn in range(20):
        lp = 0.1 + 0.04 * zn
        po = 0.9 - 0.03 * zn
        for w in range(9):
            for metric, val in [("Lead Penetration", lp), ("Perfect Orders", po)]:
                rows.append({
                    "country": "CO", "city": "X", "zone": f"z{zn}",
                    "zone_type": "Wealthy", "zone_prioritization": "P",
                    "metric": metric, "week_offset": w, "value": val,
                })
    repo = Repository(pd.DataFrame(rows), pd.DataFrame())
    tb = Toolbox(repo)
    result = tb.correlate_metrics(
        metric_a="Lead Penetration", metric_b="Perfect Orders",
    )
    assert result["data"]["correlation"] < -0.9
    assert result["data"]["n"] == 20
```

- [ ] **Step 2: Implement**

```python
    # ---- Tool 5: multivariable_filter -------------------------------
    def multivariable_filter(self, conditions: list[dict],
                             week_offset: int = 0) -> dict:
        """conditions = [{metric, op, value}], op in {>, <, >=, <=, ==}."""
        repo_metrics = self.repo.metrics
        zones = None
        for cond in conditions:
            df = repo_metrics[(repo_metrics["metric"] == cond["metric"])
                              & (repo_metrics["week_offset"] == week_offset)]
            op = cond["op"]
            v = cond["value"]
            if op == ">":   match = df[df["value"] > v]
            elif op == "<": match = df[df["value"] < v]
            elif op == ">=":match = df[df["value"] >= v]
            elif op == "<=":match = df[df["value"] <= v]
            elif op == "==":match = df[df["value"] == v]
            else:           match = df.iloc[0:0]
            keys = set(zip(match["country"], match["zone"]))
            zones = keys if zones is None else zones & keys
        zones = zones or set()
        data = [{"country": c, "zone": z} for c, z in sorted(zones)]
        summary = f"{len(data)} zonas cumplen las {len(conditions)} condiciones."
        return {"data": data, "summary": summary,
                "metadata": {"conditions": conditions}}

    # ---- Tool 6: correlate_metrics ----------------------------------
    def correlate_metrics(self, metric_a: str, metric_b: str,
                          scope: dict | None = None,
                          week_offset: int = 0) -> dict:
        df = self.repo.metrics
        df = df[df["week_offset"] == week_offset]
        for k, v in (scope or {}).items():
            if k in df.columns:
                df = df[df[k] == v]
        pivot = df.pivot_table(index=["country", "zone"],
                                columns="metric", values="value",
                                aggfunc="first")
        if metric_a not in pivot.columns or metric_b not in pivot.columns:
            return {"data": {"correlation": None, "n": 0},
                    "summary": "Métricas no disponibles en el panel.",
                    "metadata": {}}
        pair = pivot[[metric_a, metric_b]].dropna()
        if len(pair) < 3:
            return {"data": {"correlation": None, "n": len(pair)},
                    "summary": "Datos insuficientes.", "metadata": {}}
        r = pair[metric_a].corr(pair[metric_b])
        summary = (f"Correlación Pearson entre {metric_a} y {metric_b}: "
                   f"r={r:+.3f} (n={len(pair)} zonas).")
        return {"data": {"correlation": float(r), "n": int(len(pair))},
                "summary": summary,
                "metadata": {"metric_a": metric_a, "metric_b": metric_b}}
```

- [ ] **Step 3: Run tests, verify pass**

- [ ] **Step 4: Commit**

```powershell
git add backend/app/chat/toolbox.py backend/tests/test_toolbox.py
git commit -m "feat(chat): add multivariable_filter and correlate_metrics tools"
```

---

### Task 2.5: Add `growth_explainer`

**Files:**
- Modify: `backend/app/chat/toolbox.py`
- Modify: `backend/tests/test_toolbox.py`

- [ ] **Step 1: Add failing test**

```python
def test_growth_explainer_returns_top_growing_zones():
    import pandas as pd
    from app.data.repository import Repository
    from app.chat.toolbox import Toolbox
    # 5 zones with varying order growth
    rows = []
    for zn in range(5):
        # zone with index zn has order growth proportional to zn over last 5 weeks
        for w in range(9):
            # value at L8W = 100; at L0W = 100 + zn*50 (so zn=4 grows the most)
            growth = zn * 50 * ((8 - w) / 8)
            rows.append({
                "country": "CO", "city": "X", "zone": f"z{zn}",
                "metric": "Orders", "week_offset": w,
                "value": 100 + growth,
            })
        for w in range(9):
            rows.append({
                "country": "CO", "city": "X", "zone": f"z{zn}",
                "zone_type": "Wealthy", "zone_prioritization": "P",
                "metric": "Lead Penetration", "week_offset": w,
                "value": 0.5 + 0.05 * zn,
            })
    metrics = pd.DataFrame([r for r in rows if r["metric"] != "Orders"])
    orders = pd.DataFrame([r for r in rows if r["metric"] == "Orders"])
    repo = Repository(metrics, orders)
    tb = Toolbox(repo)
    result = tb.growth_explainer(weeks=5, top_n=3)
    top_zones = [row["zone"] for row in result["data"]["top_growth"]]
    assert top_zones[0] == "z4"
    assert "correlated_metrics" in result["data"]
```

- [ ] **Step 2: Implement**

```python
    # ---- Tool 7: growth_explainer -----------------------------------
    def growth_explainer(self, metric: str = "Orders", weeks: int = 5,
                         top_n: int = 10) -> dict:
        """Find top-growing zones in `metric` over `weeks` and compare
        their other metrics vs the average to hypothesize causes."""
        src = self.repo.orders if metric == "Orders" else self.repo.metrics
        df = src[src["metric"] == metric]
        df = df[df["week_offset"] < weeks]
        pivot = df.pivot_table(index=["country", "zone"],
                               columns="week_offset", values="value")
        # L0W is column 0, latest. Older is bigger index.
        if pivot.empty:
            return {"data": {"top_growth": [], "correlated_metrics": []},
                    "summary": "Sin datos.", "metadata": {}}
        latest = pivot[0] if 0 in pivot.columns else None
        oldest_col = max(c for c in pivot.columns if c < weeks)
        oldest = pivot[oldest_col]
        growth = ((latest - oldest) / oldest.replace(0, 1)).fillna(0)
        top = growth.sort_values(ascending=False).head(top_n)
        top_records = [
            {"country": idx[0], "zone": idx[1],
             "growth_pct": float(top.loc[idx])}
            for idx in top.index
        ]
        # Compare other metrics: avg value at L0W in top vs rest
        top_zones_set = set(top.index)
        all_metrics = self.repo.metrics
        l0w = all_metrics[all_metrics["week_offset"] == 0]
        deltas = []
        for m, sub in l0w.groupby("metric"):
            sub = sub.set_index(["country", "zone"])["value"]
            in_top = sub.loc[sub.index.intersection(top_zones_set)].mean()
            in_rest = sub.loc[~sub.index.isin(top_zones_set)].mean()
            if pd.notna(in_top) and pd.notna(in_rest) and in_rest != 0:
                deltas.append({"metric": m,
                               "top_mean": float(in_top),
                               "rest_mean": float(in_rest),
                               "lift_pct": float((in_top - in_rest) / abs(in_rest))})
        deltas.sort(key=lambda d: abs(d["lift_pct"]), reverse=True)
        summary = (f"Top {top_n} zonas en crecimiento de {metric} "
                   f"sobre {weeks} semanas. Sus métricas se comparan al resto "
                   f"para sugerir hipótesis de causa.")
        return {"data": {"top_growth": top_records,
                          "correlated_metrics": deltas[:5]},
                "summary": summary,
                "metadata": {"metric": metric, "weeks": weeks}}
```

- [ ] **Step 3: Run tests, verify pass**

- [ ] **Step 4: Commit**

```powershell
git add backend/app/chat/toolbox.py backend/tests/test_toolbox.py
git commit -m "feat(chat): add growth_explainer tool"
```

---

### Task 2.6: Tool schemas for OpenAI function-calling

**Files:**
- Create: `backend/app/chat/schemas.py`

- [ ] **Step 1: Implement `backend/app/chat/schemas.py`**

```python
"""OpenAI function-calling schemas for each toolbox method."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "top_n_zones",
            "description": "Devuelve top N zonas para una métrica en una semana dada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "n": {"type": "integer", "default": 5},
                    "week_offset": {"type": "integer", "default": 0,
                                    "description": "0=L0W (semana actual), 8=L8W"},
                    "filters": {"type": "object",
                                "description": "ej {country: 'CO', zone_type: 'Wealthy'}"},
                    "order": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_segments",
            "description": "Compara una métrica entre segmentos (group_by puede ser country, zone_type, zone_prioritization).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "group_by": {"type": "string"},
                    "filters": {"type": "object"},
                    "week_offset": {"type": "integer", "default": 0},
                },
                "required": ["metric", "group_by"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "metric_trend",
            "description": "Evolución temporal de una métrica en una zona específica (últimas N semanas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "country": {"type": "string"},
                    "zone": {"type": "string"},
                    "weeks": {"type": "integer", "default": 9},
                },
                "required": ["metric", "country", "zone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate",
            "description": "Agrega una métrica por una dimensión (mean/median/sum/min/max/std).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "group_by": {"type": "string"},
                    "agg": {"type": "string",
                            "enum": ["mean", "median", "sum", "min", "max", "std"],
                            "default": "mean"},
                    "filters": {"type": "object"},
                    "week_offset": {"type": "integer", "default": 0},
                },
                "required": ["metric", "group_by"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multivariable_filter",
            "description": "Encuentra zonas que cumplen múltiples condiciones sobre distintas métricas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "metric": {"type": "string"},
                                "op": {"type": "string",
                                       "enum": [">", "<", ">=", "<=", "=="]},
                                "value": {"type": "number"},
                            },
                            "required": ["metric", "op", "value"],
                        },
                    },
                    "week_offset": {"type": "integer", "default": 0},
                },
                "required": ["conditions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "correlate_metrics",
            "description": "Correlación de Pearson entre dos métricas a través del panel de zonas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_a": {"type": "string"},
                    "metric_b": {"type": "string"},
                    "scope": {"type": "object",
                              "description": "filtros opcionales: country, zone_type, ..."},
                    "week_offset": {"type": "integer", "default": 0},
                },
                "required": ["metric_a", "metric_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "growth_explainer",
            "description": "Identifica zonas con mayor crecimiento en órdenes y compara sus métricas vs el resto para hipotetizar causas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "default": "Orders"},
                    "weeks": {"type": "integer", "default": 5},
                    "top_n": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": (
                "Fallback: ejecuta un SELECT SQL sobre las tablas metrics_df y "
                "orders_df (ver schemas más abajo). Usar solo si las otras "
                "tools no cubren la pregunta. Tablas disponibles:\n"
                "metrics_df(country, city, zone, zone_type, zone_prioritization, metric, week_offset, value)\n"
                "orders_df(country, city, zone, metric, week_offset, value)"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string",
                              "description": "SQL SELECT (DuckDB syntax)"},
                },
                "required": ["query"],
            },
        },
    },
]
```

- [ ] **Step 2: Commit**

```powershell
git add backend/app/chat/schemas.py
git commit -m "feat(chat): OpenAI function-calling schemas for toolbox"
```

---

## Phase 3 — SQL Sandbox + ChatService

### Task 3.1: SQL sandbox with sqlglot validation

**Files:**
- Create: `backend/app/chat/sandbox.py`
- Test: `backend/tests/test_sandbox.py`

- [ ] **Step 1: Write failing tests**

```python
import pandas as pd
import pytest
from app.chat.sandbox import SqlSandbox, SqlValidationError

@pytest.fixture
def sandbox():
    metrics_df = pd.DataFrame([
        {"country": "CO", "zone": "Chapinero", "metric": "Lead Penetration",
         "week_offset": 0, "value": 0.5}
    ])
    orders_df = pd.DataFrame([
        {"country": "CO", "zone": "Chapinero", "metric": "Orders",
         "week_offset": 0, "value": 1000}
    ])
    return SqlSandbox(metrics_df, orders_df)

def test_select_query_works(sandbox):
    result = sandbox.run("SELECT * FROM metrics_df")
    assert len(result["data"]) == 1

def test_select_with_filter(sandbox):
    result = sandbox.run("SELECT zone, value FROM metrics_df WHERE country = 'CO'")
    assert result["data"][0]["zone"] == "Chapinero"

def test_insert_is_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("INSERT INTO metrics_df VALUES ('X', 'Y', 'Z', 0, 0.1)")

def test_update_is_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("UPDATE metrics_df SET value = 0")

def test_delete_is_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("DELETE FROM metrics_df")

def test_unknown_table_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("SELECT * FROM users")

def test_attach_is_rejected(sandbox):
    with pytest.raises(SqlValidationError):
        sandbox.run("ATTACH 'evil.db' AS evil")
```

- [ ] **Step 2: Run tests, verify fail**

- [ ] **Step 3: Implement `backend/app/chat/sandbox.py`**

```python
"""SQL sandbox: validate with sqlglot, run with DuckDB over pandas."""
from __future__ import annotations
import duckdb
import pandas as pd
import sqlglot
from sqlglot import expressions as exp

ALLOWED_TABLES = {"metrics_df", "orders_df"}
MAX_ROWS = 1000


class SqlValidationError(ValueError):
    pass


class SqlSandbox:
    def __init__(self, metrics_df: pd.DataFrame, orders_df: pd.DataFrame):
        self.metrics_df = metrics_df
        self.orders_df = orders_df

    def _validate(self, sql: str) -> None:
        try:
            parsed = sqlglot.parse(sql, dialect="duckdb")
        except Exception as e:
            raise SqlValidationError(f"Parse error: {e}") from e
        if len(parsed) != 1:
            raise SqlValidationError("Solo se permite una sentencia.")
        stmt = parsed[0]
        # Must be a SELECT or WITH
        if not isinstance(stmt, (exp.Select, exp.With)):
            raise SqlValidationError(
                f"Solo SELECT/WITH permitidos; encontrado {type(stmt).__name__}."
            )
        # Forbidden node types anywhere in the tree
        forbidden_types = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
            exp.Alter, exp.Attach, exp.Pragma, exp.Command, exp.Copy,
        )
        for node in stmt.walk():
            if isinstance(node, forbidden_types):
                raise SqlValidationError(
                    f"Sentencia no permitida: {type(node).__name__}"
                )
        # Tables used must be whitelisted
        for table in stmt.find_all(exp.Table):
            name = table.name.lower()
            if name not in ALLOWED_TABLES:
                raise SqlValidationError(f"Tabla no permitida: {name}")

    def run(self, sql: str) -> dict:
        self._validate(sql)
        con = duckdb.connect(":memory:")
        try:
            con.register("metrics_df", self.metrics_df)
            con.register("orders_df", self.orders_df)
            df = con.execute(sql).fetchdf()
        finally:
            con.close()
        truncated = len(df) > MAX_ROWS
        if truncated:
            df = df.head(MAX_ROWS)
        return {
            "data": df.to_dict("records"),
            "summary": (f"{len(df)} filas devueltas"
                        + (f" (truncado a {MAX_ROWS})" if truncated else "")),
            "metadata": {"rows": len(df), "truncated": truncated},
        }
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```powershell
git add backend/app/chat/sandbox.py backend/tests/test_sandbox.py
git commit -m "feat(chat): DuckDB SQL sandbox with sqlglot whitelist"
```

---

### Task 3.2: System prompt

**Files:**
- Create: `backend/app/chat/prompts.py`

- [ ] **Step 1: Implement**

```python
"""System and helper prompts for the chat service."""
from app.data.glossary import glossary_for_prompt


def build_system_prompt() -> str:
    return f"""Sos un asistente de datos para los equipos de Strategy, Planning & Analytics (SP&A) y Operations de Rappi.
Tu tarea es responder preguntas sobre métricas operacionales por zona en lenguaje natural y claro, pensando en usuarios no técnicos.

## Datos disponibles
- Tabla `metrics_df`: métricas operacionales por (país, ciudad, zona, semana). Columnas: country, city, zone, zone_type (Wealthy/Non Wealthy), zone_prioritization (High Priority/Prioritized/Not Prioritized), metric, week_offset (0=semana actual L0W, 8=hace 8 semanas L8W), value.
- Tabla `orders_df`: volumen de órdenes por (país, ciudad, zona, semana). Mismo formato.

## Glosario de métricas
{glossary_for_prompt()}

## Convenciones de respuesta
1. **Siempre usá tools** para obtener números. Nunca inventes valores.
2. **Citá zona + país + métrica + ventana temporal** en cada respuesta numérica.
3. Si la pregunta es ambigua (p.ej. "zonas problemáticas" sin más contexto), aclará tu interpretación: por ejemplo, "interpreto zonas problemáticas como aquellas con métricas clave deterioradas vs hace 4 semanas".
4. Para preguntas de inferencia/causalidad, sé explícito sobre que son hipótesis, no conclusiones.
5. Al final de cada respuesta, sugerí 1-2 análisis adicionales relacionados como follow-up.
6. Preferí las tools específicas (top_n_zones, compare_segments, ...) antes que `run_sql`. Usá `run_sql` solo si ninguna tool específica cubre la pregunta.

## Formato
- Usá Markdown.
- Para tablas, formato Markdown compacto (3-10 filas máximo en la respuesta visible).
- Porcentajes con 1 decimal, montos con separador de miles."""


def build_suggestions_prompt(last_question: str, tools_used: list[str]) -> str:
    return f"""Dada esta pregunta y las tools usadas, sugerí 2 follow-ups cortos y específicos (máximo 8 palabras cada uno) en español que ayudarían a profundizar el análisis. Devolvé JSON: {{"suggestions": ["...", "..."]}}.

Pregunta original: {last_question}
Tools usadas: {tools_used}"""
```

- [ ] **Step 2: Commit**

```powershell
git add backend/app/chat/prompts.py
git commit -m "feat(chat): system prompt with glossary and conventions"
```

---

### Task 3.3: ChatService — orchestration loop

**Files:**
- Create: `backend/app/chat/service.py`

- [ ] **Step 1: Implement**

```python
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
        # Trim to MAX_HISTORY_MESSAGES
        history[:] = history[-MAX_HISTORY_MESSAGES:]
        messages = [self._system] + history
        tools_used: list[str] = []
        client = self.llm._client  # AsyncOpenAI

        for iteration in range(MAX_TOOL_ITERATIONS):
            resp = await client.chat.completions.create(
                model=self.llm.model, messages=messages,
                tools=TOOL_SCHEMAS, tool_choice="auto",
            )
            choice = resp.choices[0]
            msg = choice.message
            if msg.tool_calls:
                # Append assistant message with tool_calls
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
            # No more tool calls → final answer; stream it token-by-token
            final_text = msg.content or ""
            for ch in final_text:
                yield {"type": "token", "content": ch}
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
            resp = await self.llm._client.chat.completions.create(
                model=self.llm.model,
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
```

- [ ] **Step 2: Commit**

```powershell
git add backend/app/chat/service.py
git commit -m "feat(chat): ChatService with tool-calling loop and follow-ups"
```

---

## Phase 4 — FastAPI chat endpoint

### Task 4.1: SSE chat endpoint

**Files:**
- Modify: `backend/app/api/main.py`
- Create: `backend/app/api/schemas.py`

- [ ] **Step 1: Create `backend/app/api/schemas.py`**

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str
```

- [ ] **Step 2: Update `backend/app/api/main.py` to add `/chat` and `/chat/reset`**

```python
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
```

- [ ] **Step 3: Manual smoke test with curl**

Start server:
```powershell
uv run uvicorn app.api.main:app --reload
```

In another shell:
```powershell
curl -N -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d '{"session_id":"s1","message":"Cuales son las 5 zonas con mayor Lead Penetration esta semana?"}'
```

Expected: SSE stream with `data: {"type":"tool", ...}` and then tokens then `data: {"type":"done", ...}`.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/api/
git commit -m "feat(api): /chat SSE endpoint and /chat/reset"
```

---

## Phase 5 — Insights detectors

### Task 5.1: Finding dataclass + config

**Files:**
- Create: `backend/app/insights/__init__.py`
- Create: `backend/app/insights/config.py`
- Create: `backend/app/insights/models.py`

- [ ] **Step 1: Implement `models.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Literal

Category = Literal["anomaly", "trend", "benchmark", "correlation", "opportunity"]


@dataclass
class Finding:
    category: Category
    severity: float
    metric: str
    headline: str
    zone: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 2: Implement `config.py`**

```python
"""Thresholds for detectors (tunable)."""
ANOMALY_PCT_CHANGE = 0.10           # >10% wow delta
TREND_MIN_STREAK = 3                # ≥3 consecutive weeks of deterioration
CORRELATION_MIN_ABS_R = 0.6
CORRELATION_MIN_N = 30
BENCHMARK_LOW_PCT = 10              # below p10 → flagged
BENCHMARK_HIGH_PCT = 90             # above p90 → flagged
TOP_K_TOTAL = 18                    # findings across categories
PER_CATEGORY_CAP = 5                # max per category
```

- [ ] **Step 3: Commit**

```powershell
git add backend/app/insights/
git commit -m "feat(insights): Finding dataclass and threshold config"
```

---

### Task 5.2: Anomaly + trend detectors

**Files:**
- Create: `backend/app/insights/detector.py`
- Test: `backend/tests/test_detector.py`

- [ ] **Step 1: Write failing tests**

```python
import pandas as pd
import pytest
from app.data.repository import Repository
from app.data.glossary import GLOSSARY
from app.insights.detector import detect_anomalies, detect_negative_trends

def _build_repo(rows):
    metrics = pd.DataFrame(rows)
    return Repository(metrics, pd.DataFrame())

def test_anomaly_detected_when_wow_delta_exceeds_threshold():
    rows = []
    # Stable for 8 weeks, then sudden drop in L0W
    for w in range(9):
        val = 0.5 if w > 0 else 0.3  # L0W=0.3, L1W=0.5 → -40%
        rows.append({"country": "CO", "city": "X", "zone": "A",
                     "zone_type": "Wealthy", "zone_prioritization": "P",
                     "metric": "Lead Penetration", "week_offset": w, "value": val})
    repo = _build_repo(rows)
    findings = detect_anomalies(repo, GLOSSARY)
    assert any(f.category == "anomaly" and f.zone["zone"] == "A" for f in findings)

def test_anomaly_not_detected_when_change_is_small():
    rows = []
    for w in range(9):
        val = 0.50 if w > 0 else 0.51
        rows.append({"country": "CO", "city": "X", "zone": "B",
                     "zone_type": "Wealthy", "zone_prioritization": "P",
                     "metric": "Lead Penetration", "week_offset": w, "value": val})
    repo = _build_repo(rows)
    findings = detect_anomalies(repo, GLOSSARY)
    assert not any(f.zone["zone"] == "B" for f in findings)

def test_negative_trend_detected_with_3_consecutive_deteriorations():
    rows = []
    # Lead Penetration (higher is better) deteriorating last 4 weeks
    values_by_offset = {8: 0.7, 7: 0.7, 6: 0.7, 5: 0.7, 4: 0.7,
                        3: 0.65, 2: 0.6, 1: 0.55, 0: 0.5}
    for w, v in values_by_offset.items():
        rows.append({"country": "CO", "city": "X", "zone": "C",
                     "zone_type": "Wealthy", "zone_prioritization": "P",
                     "metric": "Lead Penetration", "week_offset": w, "value": v})
    repo = _build_repo(rows)
    findings = detect_negative_trends(repo, GLOSSARY)
    assert any(f.zone["zone"] == "C" and f.category == "trend" for f in findings)
```

- [ ] **Step 2: Implement `detector.py` (anomalies + trends)**

```python
"""Insight detectors: pure pandas, no LLM."""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from app.data.repository import Repository
from app.insights.models import Finding
from app.insights import config

log = logging.getLogger(__name__)


def _direction(glossary: dict, metric: str) -> bool:
    return glossary.get(metric, {}).get("higher_is_better", True)


def detect_anomalies(repo: Repository, glossary: dict) -> list[Finding]:
    findings: list[Finding] = []
    df = repo.metrics
    pivot = df.pivot_table(
        index=["country", "city", "zone", "zone_type", "zone_prioritization", "metric"],
        columns="week_offset", values="value",
    )
    for idx, row in pivot.iterrows():
        l0w = row.get(0)
        l1w = row.get(1)
        if pd.isna(l0w) or pd.isna(l1w) or l1w == 0:
            continue
        pct = (l0w - l1w) / abs(l1w)
        if abs(pct) < config.ANOMALY_PCT_CHANGE:
            continue
        # Severity normalized by historical std (z-like)
        history = row.dropna().values
        std = history.std() if len(history) > 1 else 0.0
        sev = float(min(1.0, abs(l0w - l1w) / (std + 1e-9)))
        country, city, zone, ztype, zprior, metric = idx
        improved = (pct > 0) == _direction(glossary, metric)
        direction_word = "mejora" if improved else "deterioro"
        findings.append(Finding(
            category="anomaly",
            severity=sev if not improved else sev * 0.5,
            metric=metric,
            headline=f"{zone} ({country}) muestra {direction_word} de {pct:+.1%} en {metric} (L0W vs L1W).",
            zone={"country": country, "city": city, "zone": zone,
                  "zone_type": ztype, "zone_prioritization": zprior},
            evidence={"l0w": float(l0w), "l1w": float(l1w),
                      "pct_change": float(pct), "improved": improved},
        ))
    return findings


def detect_negative_trends(repo: Repository, glossary: dict) -> list[Finding]:
    findings: list[Finding] = []
    df = repo.metrics
    pivot = df.pivot_table(
        index=["country", "city", "zone", "zone_type", "zone_prioritization", "metric"],
        columns="week_offset", values="value",
    )
    # Streak detection: from L0W back, count consecutive deteriorations.
    for idx, row in pivot.iterrows():
        country, city, zone, ztype, zprior, metric = idx
        higher_better = _direction(glossary, metric)
        offsets = sorted([c for c in row.index if not pd.isna(row[c])])
        # offsets sorted ascending: 0,1,2,..,8 → 0=latest
        if 0 not in offsets:
            continue
        streak = 0
        prev = row[0]
        for off in range(1, max(offsets) + 1):
            if pd.isna(row.get(off)):
                break
            cur = row[off]
            deteriorated = (prev < cur) if higher_better else (prev > cur)
            if deteriorated:
                streak += 1
                prev = cur
            else:
                break
        if streak >= config.TREND_MIN_STREAK:
            l0w = row[0]
            ref = row[streak] if streak in row.index else row[offsets[-1]]
            total_change = (l0w - ref) / abs(ref) if ref else 0.0
            sev = float(min(1.0, abs(total_change) * 2))
            findings.append(Finding(
                category="trend",
                severity=sev,
                metric=metric,
                headline=f"{zone} ({country}) lleva {streak} semanas de deterioro consecutivo en {metric} ({total_change:+.1%}).",
                zone={"country": country, "city": city, "zone": zone,
                      "zone_type": ztype, "zone_prioritization": zprior},
                evidence={"streak_weeks": streak, "l0w": float(l0w),
                          "ref_value": float(ref),
                          "total_change_pct": float(total_change)},
            ))
    return findings
```

- [ ] **Step 3: Run tests, verify pass**

- [ ] **Step 4: Commit**

```powershell
git add backend/app/insights/detector.py backend/tests/test_detector.py
git commit -m "feat(insights): anomaly and negative-trend detectors"
```

---

### Task 5.3: Benchmark + correlation + opportunity detectors

**Files:**
- Modify: `backend/app/insights/detector.py`
- Modify: `backend/tests/test_detector.py`

- [ ] **Step 1: Add failing tests**

```python
from app.insights.detector import (
    detect_benchmark_divergence, detect_correlations, detect_opportunities,
)

def test_benchmark_divergence_flags_outliers():
    rows = []
    # 10 Wealthy zones in CO, one (zone z9) is way below
    for zn in range(10):
        for w in range(9):
            val = 0.7 if zn != 9 else 0.2
            rows.append({"country": "CO", "city": "X", "zone": f"z{zn}",
                         "zone_type": "Wealthy", "zone_prioritization": "P",
                         "metric": "Lead Penetration",
                         "week_offset": w, "value": val})
    repo = _build_repo(rows)
    findings = detect_benchmark_divergence(repo, GLOSSARY)
    flagged = [f.zone["zone"] for f in findings]
    assert "z9" in flagged

def test_correlation_detected():
    rows = []
    # 40 zones, LP and PO strongly correlated
    for zn in range(40):
        lp = 0.1 + 0.02 * zn
        po = 0.2 + 0.018 * zn
        for w in range(9):
            for m, v in [("Lead Penetration", lp), ("Perfect Orders", po)]:
                rows.append({"country": "CO", "city": "X", "zone": f"z{zn}",
                             "zone_type": "Wealthy", "zone_prioritization": "P",
                             "metric": m, "week_offset": w, "value": v})
    repo = _build_repo(rows)
    findings = detect_correlations(repo, GLOSSARY)
    assert any(f.category == "correlation"
               and "Lead Penetration" in f.headline
               and "Perfect Orders" in f.headline
               for f in findings)
```

- [ ] **Step 2: Implement in `detector.py`**

```python
def detect_benchmark_divergence(repo: Repository, glossary: dict) -> list[Finding]:
    findings: list[Finding] = []
    df = repo.metrics
    df = df[df["week_offset"] == 0]
    for (country, ztype, metric), grp in df.groupby(
        ["country", "zone_type", "metric"]
    ):
        if len(grp) < 5:
            continue
        p_low = np.percentile(grp["value"], config.BENCHMARK_LOW_PCT)
        p_high = np.percentile(grp["value"], config.BENCHMARK_HIGH_PCT)
        median = grp["value"].median()
        higher_better = _direction(glossary, metric)
        for _, row in grp.iterrows():
            v = row["value"]
            distance = abs(v - median) / (abs(median) + 1e-9)
            if v <= p_low:
                # under-performer if higher_better, over-performer otherwise
                is_bad = higher_better
                label = "bajo p10" if higher_better else "alto p90 (mejor)"
                findings.append(Finding(
                    category="benchmark",
                    severity=float(min(1.0, distance)),
                    metric=metric,
                    headline=(f"{row['zone']} ({country}, {ztype}) está "
                              f"{'rezagada' if is_bad else 'sobresaliente'} "
                              f"en {metric}: {v:.3f} vs mediano {median:.3f} del grupo."),
                    zone={"country": country, "city": row["city"], "zone": row["zone"],
                          "zone_type": ztype,
                          "zone_prioritization": row["zone_prioritization"]},
                    evidence={"value": float(v), "p10": float(p_low),
                              "p90": float(p_high), "median": float(median),
                              "label": label},
                ))
            elif v >= p_high:
                is_bad = not higher_better
                label = "alto p90" if higher_better else "bajo p10 (mejor)"
                findings.append(Finding(
                    category="benchmark",
                    severity=float(min(1.0, distance)),
                    metric=metric,
                    headline=(f"{row['zone']} ({country}, {ztype}) destaca "
                              f"{'positivamente' if not is_bad else 'negativamente'} "
                              f"en {metric}: {v:.3f} vs mediano {median:.3f}."),
                    zone={"country": country, "city": row["city"], "zone": row["zone"],
                          "zone_type": ztype,
                          "zone_prioritization": row["zone_prioritization"]},
                    evidence={"value": float(v), "p10": float(p_low),
                              "p90": float(p_high), "median": float(median),
                              "label": label},
                ))
    return findings


def detect_correlations(repo: Repository, glossary: dict) -> list[Finding]:
    findings: list[Finding] = []
    df = repo.metrics
    df = df[df["week_offset"] == 0]
    pivot = df.pivot_table(index=["country", "zone"], columns="metric", values="value")
    metrics = list(pivot.columns)
    seen = set()
    for i, m_a in enumerate(metrics):
        for m_b in metrics[i+1:]:
            pair = pivot[[m_a, m_b]].dropna()
            if len(pair) < config.CORRELATION_MIN_N:
                continue
            r = pair[m_a].corr(pair[m_b])
            if pd.isna(r) or abs(r) < config.CORRELATION_MIN_ABS_R:
                continue
            key = tuple(sorted([m_a, m_b]))
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(
                category="correlation",
                severity=float(min(1.0, abs(r))),
                metric=f"{m_a} vs {m_b}",
                headline=(f"Correlación {'positiva' if r > 0 else 'negativa'} "
                          f"fuerte entre {m_a} y {m_b}: r={r:+.2f} "
                          f"(n={len(pair)} zonas)."),
                zone={},
                evidence={"metric_a": m_a, "metric_b": m_b,
                          "r": float(r), "n": int(len(pair))},
            ))
    return findings


def detect_opportunities(repo: Repository, glossary: dict) -> list[Finding]:
    """Combina señales: High Priority zones bajo p25 = under-performance estratégica."""
    findings: list[Finding] = []
    df = repo.metrics
    df = df[(df["week_offset"] == 0)
            & (df["zone_prioritization"] == "High Priority")]
    for (country, ztype, metric), grp in df.groupby(
        ["country", "zone_type", "metric"]
    ):
        if len(grp) < 5:
            continue
        p25 = np.percentile(grp["value"], 25)
        higher_better = _direction(glossary, metric)
        for _, row in grp.iterrows():
            v = row["value"]
            underperforming = (v <= p25) if higher_better else (v >= np.percentile(grp["value"], 75))
            if not underperforming:
                continue
            findings.append(Finding(
                category="opportunity",
                severity=0.7,
                metric=metric,
                headline=(f"{row['zone']} ({country}) es High Priority pero "
                          f"está en el cuartil bajo de su grupo en {metric}."),
                zone={"country": country, "city": row["city"], "zone": row["zone"],
                      "zone_type": ztype, "zone_prioritization": "High Priority"},
                evidence={"value": float(v), "p25": float(p25)},
            ))
    return findings
```

- [ ] **Step 3: Run tests, verify pass**

- [ ] **Step 4: Commit**

```powershell
git add backend/app/insights/detector.py backend/tests/test_detector.py
git commit -m "feat(insights): benchmark, correlation, opportunity detectors"
```

---

## Phase 6 — Ranker + Reporter + PDF

### Task 6.1: Ranker

**Files:**
- Create: `backend/app/insights/ranker.py`

- [ ] **Step 1: Implement**

```python
"""Rank, dedup, and limit findings."""
from collections import defaultdict
from app.insights.models import Finding
from app.insights import config


def rank_and_select(findings: list[Finding]) -> list[Finding]:
    # Sort by severity desc
    findings = sorted(findings, key=lambda f: f.severity, reverse=True)
    # Dedup: per (zone-key, metric), keep highest severity
    seen: dict[tuple, Finding] = {}
    for f in findings:
        zk = (f.zone.get("country", ""), f.zone.get("zone", ""), f.metric)
        if zk not in seen or seen[zk].severity < f.severity:
            seen[zk] = f
    deduped = sorted(seen.values(), key=lambda f: f.severity, reverse=True)
    # Cap per category
    counts: dict[str, int] = defaultdict(int)
    out: list[Finding] = []
    for f in deduped:
        if counts[f.category] >= config.PER_CATEGORY_CAP:
            continue
        out.append(f)
        counts[f.category] += 1
        if len(out) >= config.TOP_K_TOTAL:
            break
    return out
```

- [ ] **Step 2: Commit**

```powershell
git add backend/app/insights/ranker.py
git commit -m "feat(insights): ranker with dedup and per-category cap"
```

---

### Task 6.2: Reporter (LLM narrative)

**Files:**
- Create: `backend/app/insights/prompts.py`
- Create: `backend/app/insights/reporter.py`

- [ ] **Step 1: Implement `prompts.py`**

```python
REPORTER_SYSTEM = """Sos un analista de datos para los equipos de Operations y SP&A de Rappi.
Recibís una lista de findings (hallazgos cuantitativos ya detectados por un motor determinístico).
Tu tarea: redactar un reporte ejecutivo en Markdown.

**REGLAS CRÍTICAS:**
1. NUNCA inventes números. Solo usá los valores presentes en `evidence` de cada finding.
2. Citá los números exactos en la narrativa.
3. Para cada finding, generá una recomendación accionable concreta (acción específica + dueño sugerido si aplica).
4. Tono profesional, conciso, orientado a managers no técnicos.
5. Si una métrica está en el glosario, usá su descripción para contextualizar.

**Estructura obligatoria:**
# Reporte Ejecutivo — Operaciones Rappi
## Resumen Ejecutivo
(3-5 bullets con los hallazgos más críticos, citando zona y métrica)
## Anomalías
## Tendencias Preocupantes
## Benchmarking
## Correlaciones
## Oportunidades
## Metodología
(1 párrafo breve sobre cómo se generaron estos insights)

Cada hallazgo se presenta como:
### [headline]
- **Evidencia:** ...
- **Recomendación:** ...
"""
```

- [ ] **Step 2: Implement `reporter.py`**

```python
"""Build the executive report: detection → ranking → LLM narrative → markdown."""
from __future__ import annotations
import json
import logging
from app.data.repository import Repository
from app.data.glossary import GLOSSARY, glossary_for_prompt
from app.insights.detector import (
    detect_anomalies, detect_negative_trends,
    detect_benchmark_divergence, detect_correlations, detect_opportunities,
)
from app.insights.ranker import rank_and_select
from app.insights.prompts import REPORTER_SYSTEM
from app.llm.client import get_llm

log = logging.getLogger(__name__)


def collect_findings(repo: Repository) -> list[dict]:
    findings = []
    findings += detect_anomalies(repo, GLOSSARY)
    findings += detect_negative_trends(repo, GLOSSARY)
    findings += detect_benchmark_divergence(repo, GLOSSARY)
    findings += detect_correlations(repo, GLOSSARY)
    findings += detect_opportunities(repo, GLOSSARY)
    log.info("Collected %d raw findings", len(findings))
    top = rank_and_select(findings)
    log.info("Selected %d findings after ranking", len(top))
    return [f.to_dict() for f in top]


async def generate_markdown_report(repo: Repository) -> str:
    findings = collect_findings(repo)
    llm = get_llm()
    user_payload = {
        "findings": findings,
        "glossary": glossary_for_prompt(),
    }
    resp = await llm._client.chat.completions.create(
        model=llm.model,
        messages=[
            {"role": "system", "content": REPORTER_SYSTEM},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )
    return resp.choices[0].message.content or ""
```

- [ ] **Step 3: Commit**

```powershell
git add backend/app/insights/
git commit -m "feat(insights): reporter generates markdown via LLM"
```

---

### Task 6.3: Markdown → PDF

**Files:**
- Create: `backend/app/insights/pdf.py`

- [ ] **Step 1: Implement**

```python
"""Markdown → HTML → PDF with Rappi branding."""
import markdown as md
from weasyprint import HTML

CSS = """
@page { size: A4; margin: 2cm 1.5cm; }
body { font-family: 'Helvetica', 'Arial', sans-serif; color: #1A1A1A; font-size: 11pt; line-height: 1.5; }
h1 { color: #FF441F; border-bottom: 3px solid #FF441F; padding-bottom: 6px; }
h2 { color: #FF441F; margin-top: 24px; }
h3 { color: #333; margin-top: 16px; }
strong { color: #1A1A1A; }
ul { padding-left: 20px; }
li { margin-bottom: 4px; }
hr { border: none; border-top: 1px solid #ccc; margin: 24px 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
th { background: #FFE9E0; }
"""


def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    html_body = md.markdown(markdown_text, extensions=["tables", "fenced_code"])
    full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{CSS}</style></head><body>{html_body}</body></html>"""
    return HTML(string=full_html).write_pdf()
```

- [ ] **Step 2: Commit**

```powershell
git add backend/app/insights/pdf.py
git commit -m "feat(insights): markdown→PDF with Rappi-branded CSS"
```

---

## Phase 7 — FastAPI report endpoint

### Task 7.1: `/report` endpoint

**Files:**
- Modify: `backend/app/api/main.py`

- [ ] **Step 1: Add endpoint**

In `main.py`, add:
```python
from fastapi import Query
from fastapi.responses import Response, PlainTextResponse
from app.insights.reporter import generate_markdown_report
from app.insights.pdf import markdown_to_pdf_bytes


@app.post("/report")
async def report(request: Request, format: str = Query("pdf")):
    repo: Repository = request.app.state.repo
    md_text = await generate_markdown_report(repo)
    if format == "markdown":
        return PlainTextResponse(md_text, media_type="text/markdown; charset=utf-8")
    pdf = markdown_to_pdf_bytes(md_text)
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="rappi-insights.pdf"'},
    )
```

- [ ] **Step 2: Smoke test**

```powershell
curl -X POST "http://127.0.0.1:8000/report?format=markdown" -o report.md
curl -X POST "http://127.0.0.1:8000/report" -o report.pdf
```

Open `report.pdf`, verify it renders with Rappi colors.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/api/main.py
git commit -m "feat(api): /report endpoint returns markdown or pdf"
```

---

## Phase 8 — Frontend chat UI

### Task 8.1: API client + types

**Files:**
- Create: `frontend/lib/api-client.ts`
- Create: `frontend/lib/types.ts`

- [ ] **Step 1: Implement `lib/types.ts`**

```ts
export type ChatEvent =
  | { type: "token"; content: string }
  | { type: "tool"; name: string; args: Record<string, unknown> }
  | { type: "done"; sources: string[]; suggestions: string[] };

export type Message = {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  suggestions?: string[];
};
```

- [ ] **Step 2: Implement `lib/api-client.ts`**

```ts
import type { ChatEvent } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function* streamChat(
  sessionId: string,
  message: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = line.slice(6);
      try {
        yield JSON.parse(payload) as ChatEvent;
      } catch { /* ignore malformed */ }
    }
  }
}

export async function resetSession(sessionId: string): Promise<void> {
  await fetch(`${API}/chat/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function fetchReportMarkdown(): Promise<string> {
  const res = await fetch(`${API}/report?format=markdown`, { method: "POST" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

export function reportPdfUrl(): string {
  return `${API}/report`;
}
```

- [ ] **Step 3: Commit**

```powershell
git add frontend/lib/
git commit -m "feat(frontend): API client for chat SSE and report"
```

---

### Task 8.2: Chat components

**Files:**
- Create: `frontend/components/chat-window.tsx`
- Create: `frontend/components/message-bubble.tsx`
- Create: `frontend/components/message-input.tsx`

- [ ] **Step 1: Implement `components/message-bubble.tsx`**

```tsx
"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/lib/types";

export function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[80%] rounded-lg px-4 py-2 ${
        isUser
          ? "bg-rappi text-white"
          : "bg-gray-100 text-gray-900 border border-gray-200"
      }`}>
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
        {msg.toolsUsed && msg.toolsUsed.length > 0 && (
          <div className="text-xs text-gray-500 mt-2">
            Tools: {msg.toolsUsed.join(", ")}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Implement `components/message-input.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function MessageInput({ onSend, disabled, suggestions, onSuggest }: {
  onSend: (msg: string) => void;
  disabled: boolean;
  suggestions: string[];
  onSuggest: (s: string) => void;
}) {
  const [value, setValue] = useState("");
  const send = () => {
    const v = value.trim();
    if (!v) return;
    onSend(v);
    setValue("");
  };
  return (
    <div className="border-t border-gray-200 p-4 bg-white">
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggest(s)}
              className="text-xs px-3 py-1 rounded-full border border-rappi text-rappi hover:bg-rappi hover:text-white transition"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Hacé una pregunta sobre las métricas..."
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
          disabled={disabled}
        />
        <Button onClick={send} disabled={disabled} className="bg-rappi hover:bg-rappi/90">
          Enviar
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Implement `components/chat-window.tsx`**

```tsx
"use client";
import { useEffect, useRef, useState } from "react";
import { v4 as uuid } from "uuid";
import { MessageBubble } from "./message-bubble";
import { MessageInput } from "./message-input";
import { streamChat } from "@/lib/api-client";
import type { Message } from "@/lib/types";

export function ChatWindow() {
  const [sessionId] = useState(() => {
    if (typeof window === "undefined") return uuid();
    const stored = localStorage.getItem("session_id");
    if (stored) return stored;
    const fresh = uuid();
    localStorage.setItem("session_id", fresh);
    return fresh;
  });
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    setSuggestions([]);
    setMessages((m) => [...m, { role: "user", content: text }]);
    setMessages((m) => [...m, { role: "assistant", content: "" }]);
    setStreaming(true);
    const toolsUsed: string[] = [];
    try {
      for await (const ev of streamChat(sessionId, text)) {
        if (ev.type === "token") {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              content: copy[copy.length - 1].content + ev.content,
            };
            return copy;
          });
        } else if (ev.type === "tool") {
          toolsUsed.push(ev.name);
        } else if (ev.type === "done") {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              toolsUsed: ev.sources,
              suggestions: ev.suggestions,
            };
            return copy;
          });
          setSuggestions(ev.suggestions);
        }
      }
    } catch (e) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          role: "assistant",
          content: `Error: ${e instanceof Error ? e.message : String(e)}`,
        };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-12">
            <p className="text-lg">Preguntame sobre las métricas operacionales.</p>
            <p className="text-sm mt-2">Ej: "¿Cuáles son las 5 zonas con mayor Lead Penetration esta semana?"</p>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} />
        ))}
        <div ref={endRef} />
      </div>
      <MessageInput
        onSend={send}
        disabled={streaming}
        suggestions={suggestions}
        onSuggest={(s) => send(s)}
      />
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```powershell
git add frontend/components/
git commit -m "feat(frontend): chat components (window, bubble, input, suggestions)"
```

---

### Task 8.3: Wire chat into root page

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Update `app/layout.tsx`** (add Rappi favicon optionally, set title)

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Operations Analyzer — Rappi",
  description: "Bot de datos e insights automáticos para Operations",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-white text-gray-900 min-h-screen">{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Update `app/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import { ChatWindow } from "@/components/chat-window";
import { ReportPanel } from "@/components/report-panel"; // created next task
import { Button } from "@/components/ui/button";

export default function Home() {
  const [showReport, setShowReport] = useState(false);
  return (
    <main className="h-screen flex flex-col">
      <header className="bg-rappi text-white px-6 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">Operations Analyzer</h1>
        <Button
          variant="outline"
          className="bg-white text-rappi border-white hover:bg-gray-100"
          onClick={() => setShowReport((v) => !v)}
        >
          {showReport ? "Ocultar reporte" : "Generar reporte ejecutivo"}
        </Button>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <section className={`${showReport ? "w-1/2" : "w-full"} border-r border-gray-200 transition-all`}>
          <ChatWindow />
        </section>
        {showReport && (
          <section className="w-1/2 overflow-y-auto">
            <ReportPanel />
          </section>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```powershell
git add frontend/app/
git commit -m "feat(frontend): root layout with header and chat panel"
```

---

## Phase 9 — Frontend report panel

### Task 9.1: ReportPanel component

**Files:**
- Create: `frontend/components/report-panel.tsx`

- [ ] **Step 1: Implement**

```tsx
"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { fetchReportMarkdown, reportPdfUrl } from "@/lib/api-client";

export function ReportPanel() {
  const [md, setMd] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchReportMarkdown()
      .then((text) => { if (!cancelled) setMd(text); })
      .catch((e) => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const downloadPdf = async () => {
    const res = await fetch(reportPdfUrl(), { method: "POST" });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rappi-insights.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-rappi">Reporte Ejecutivo</h2>
        <Button onClick={downloadPdf} className="bg-rappi hover:bg-rappi/90" disabled={loading || !!error}>
          Descargar PDF
        </Button>
      </div>
      {loading && <p className="text-gray-500">Generando reporte... (esto puede tardar 20-40 segundos)</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && (
        <article className="prose prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
        </article>
      )}
    </div>
  );
}
```

- [ ] **Step 2: End-to-end manual test**

```powershell
# Terminal 1
cd backend; uv run uvicorn app.api.main:app --reload
# Terminal 2
cd frontend; pnpm dev
```

Open `http://localhost:3000`:
- Send "¿Cuáles son las 5 zonas con mayor Lead Penetration esta semana?" → expect tabular answer.
- Click "Generar reporte ejecutivo" → expect markdown report rendered after 20-40s.
- Click "Descargar PDF" → expect PDF download with Rappi orange styling.

- [ ] **Step 3: Commit**

```powershell
git add frontend/components/report-panel.tsx
git commit -m "feat(frontend): report panel with markdown preview and PDF download"
```

---

## Phase 10 — Smoke test + README + polish

### Task 10.1: Smoke-test script

**Files:**
- Create: `backend/scripts/eval_questions.py`

- [ ] **Step 1: Implement**

```python
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
```

- [ ] **Step 2: Run**

```powershell
cd backend
uv run python scripts/eval_questions.py 2>&1 | Tee-Object eval.log
```

Review answers. Fix any tool that misbehaves.

- [ ] **Step 3: Commit**

```powershell
git add backend/scripts/eval_questions.py
git commit -m "test: smoke-test script for the 6 brief questions"
```

---

### Task 10.2: README

**Files:**
- Create: `README.md` at repo root (or `operations-analyzer/README.md`)

- [ ] **Step 1: Write README**

```markdown
# Operations Analyzer — Rappi

Bot conversacional + sistema de insights automáticos sobre métricas operacionales por zona.

## Qué hace

- **Bot conversacional** (chat): responde preguntas en lenguaje natural sobre métricas operacionales (filtrado, comparación, tendencias, agregación, multivariable, inferencia) con memoria conversacional y sugerencias proactivas.
- **Reporte ejecutivo** (botón "Generar reporte"): genera un PDF con los hallazgos más relevantes (anomalías, tendencias preocupantes, benchmarking, correlaciones, oportunidades) y recomendaciones accionables.

## Stack

- Backend: Python 3.11, FastAPI, pandas, DuckDB, OpenAI gpt-4o, weasyprint, sqlglot.
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui.

## Cómo correrlo local

### Requisitos
- Python ≥ 3.11 + `uv` (`pipx install uv`)
- Node ≥ 20 + `pnpm` (`npm i -g pnpm`)
- API key OpenAI

### Backend
```powershell
cd backend
cp .env.example .env
# Editar .env: OPENAI_API_KEY=sk-...
uv sync
uv run uvicorn app.api.main:app --reload
```
Servidor en `http://127.0.0.1:8000`.

### Frontend
```powershell
cd frontend
pnpm install
pnpm dev
```
UI en `http://localhost:3000`.

## Arquitectura

Ver diagrama y detalles en [docs/superpowers/specs/2026-05-11-operations-analyzer-design.md](docs/superpowers/specs/2026-05-11-operations-analyzer-design.md).

Resumen:
- Datos pivotados de wide (L8W..L0W) a long en startup, cacheados a Parquet.
- Bot con tool-calling híbrido: 7 tools determinísticas + `run_sql` fallback con DuckDB y whitelist sqlglot.
- Insights con pipeline determinístico (5 detectores en pandas) → LLM redacta narrativa → Markdown → PDF.

## Decisiones técnicas y trade-offs

| Decisión | Razón |
|---|---|
| OpenAI gpt-4o vs open-source | Tool-calling estable + demo en vivo confiable. Costo bajo (~$0.20/sesión). Arquitectura LLM-agnostic vía wrapper. |
| pandas in-memory + DuckDB vs SQLite/Postgres | Dataset chico (~14k filas), zero-setup, DuckDB da SQL real sobre DataFrames sin DB externa. |
| Toolbox + SQL fallback vs text-to-pandas | Toolbox cubre los casos del brief con precisión + SQL fallback con whitelist sqlglot es más seguro y estándar que pandas arbitrario. |
| Determinístico para insights + LLM para narrativa | Cero alucinación de números, evidencia trazable, narrativa fluida. |

## Costo estimado

- Sesión de 10 preguntas en el chat: ~$0.10-0.20 (gpt-4o).
- Generación de un reporte: ~$0.05-0.10.
- Desarrollo + demo: <$5.

## Tests

```powershell
cd backend
uv run pytest -v
```

## Smoke test (pre-demo)

```powershell
cd backend
uv run python scripts/eval_questions.py
```

Corre las 6 preguntas del brief contra el ChatService.

## Limitaciones

- Memoria conversacional en memoria del proceso (se pierde al reiniciar).
- Sin auth/multi-usuario.
- Sin visualizaciones inline en el chat (planeado como stretch).
- Sin envío por email del reporte (planeado como stretch).

## Próximos pasos

- Visualizaciones Plotly inline en el chat (gráficos cuando la pregunta lo amerite).
- Export CSV de cualquier respuesta tabular.
- Envío automático del reporte por SMTP.
- Deployment en Render (backend) + Vercel (frontend).
- Cache de respuestas frecuentes para reducir costo de API.
- Modo "evaluación" con golden set de preguntas + respuestas esperadas (regression testing del bot).
```

- [ ] **Step 2: Commit**

```powershell
git add README.md
git commit -m "docs: README with setup, architecture, decisions and limitations"
```

---

### Task 10.3: Final polish — error handling + .env validation

**Files:**
- Modify: `backend/app/api/main.py`

- [ ] **Step 1: Add global exception handler**

```python
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception")
    return JSONResponse(status_code=500,
                        content={"error": str(exc), "type": type(exc).__name__})
```

- [ ] **Step 2: Validate API key on startup if not mock**

In lifespan, after loading data:
```python
if not settings.use_mock_llm and not settings.openai_api_key:
    log.warning("OPENAI_API_KEY not set; chat will fail. "
                "Set USE_MOCK_LLM=true to use mock responses.")
```

- [ ] **Step 3: Commit**

```powershell
git add backend/app/api/main.py
git commit -m "chore(api): global exception handler and api key validation"
```

---

## Stretch goals (post-MVP, opcionales)

- **S1: Visualización Plotly en chat** — agregar tool `generate_chart(spec)` que devuelve JSON Plotly; renderizar en el frontend con `react-plotly.js`. ~2-3h.
- **S2: Export CSV** — botón en cada respuesta tabular que descarga los datos del último `data` recibido. ~30min.
- **S3: Envío email del reporte** — endpoint `/report/email` con `aiosmtplib`, input de destinatario en UI. ~1h.
- **S4: Deployment** — Dockerfile backend → Render; frontend → Vercel; configurar CORS + env vars. ~1-2h.
