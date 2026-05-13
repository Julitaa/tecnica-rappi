# Solución Técnica: Inteligencia Competitiva + Análisis Operacional @ Rappi

Proyectos de análisis de datos y business intelligence para Rappi, demostrando capacidades full-stack en web scraping, datos, ML/LLM, y frontend moderno.

---

## Proyectos

### 1. 📊 [Competitive Intelligence Scraper](competitive-intelligence/)

**Qué es:** Sistema automatizado que recolecta datos de competencia (precios, delivery fees, ETAs, disponibilidad) de **McDonald's** y **OXXO** en **Rappi**, **Uber Eats** y **DiDi Food** sobre 20 direcciones representativas de CDMX + EdoMex.

**Output:**
- `data/scrapes.csv` — datos brutos (1 fila = 1 scrape de 1 SKU en 1 dirección en 1 plataforma)
- `data/scrapes.json` — mismo, formato nested
- `report/competitive_intelligence_2026.html` — reporte ejecutivo (print-to-PDF ready)
- `notebooks/insights.ipynb` — análisis exploratorio interactivo

**Cómo empezar:**
```bash
cd competitive-intelligence
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
python -m playwright install chromium
python -m scraper.run --platform all
```

👉 **Detalles completos:** [competitive-intelligence/README.md](competitive-intelligence/README.md)

---

### 2. 🤖 [Operations Analyzer — Bot + Insights](operations-analyzer/)

**Qué es:** Sistema conversacional + generador de reportes que responde preguntas en lenguaje natural sobre métricas operacionales por zona, detecta anomalías, tendencias y oportunidades, con recomendaciones accionables.

**Stack:** 
- **Backend:** FastAPI, DuckDB, pandas, OpenAI gpt-4o
- **Frontend:** Next.js 14, TypeScript, Tailwind, shadcn/ui

**Características:**
- 🗨️ Bot con memory conversacional + herramientas híbridas (7 tools determinísticas + fallback SQL)
- 📄 Reporte PDF ejecutivo generado automáticamente
- 🔍 Detectores de anomalías, tendencias, correlaciones
- 🎯 Recomendaciones accionables basadas en datos

**Cómo empezar:**
```powershell
# Backend
cd backend
cp .env.example .env
# Editar .env: agregar OPENAI_API_KEY=sk-...
uv sync
uv run uvicorn app.api.main:app --reload
# http://127.0.0.1:8000

# Frontend
cd frontend
pnpm install
pnpm dev
# http://localhost:3000
```

👉 **Detalles completos:** [operations-analyzer/README.md](operations-analyzer/README.md)

---

## Estructura general del repo

```
.
├── README.md (este archivo)
├── competitive-intelligence/
│   ├── scraper/              # web scraper
│   ├── data/                 # catálogos + outputs
│   ├── notebooks/            # análisis Jupyter
│   ├── report/               # generador HTML
│   ├── scripts/              # utilitarios
│   ├── docs/
│   │   ├── specs/            # especificaciones de diseño
│   │   ├── blockers.md       # limitaciones + mitigaciones
│   │   └── compliance.md     # ética, robots.txt
│   └── README.md
└── operations-analyzer/
    ├── backend/              # FastAPI + LLM orchestration
    ├── frontend/             # Next.js UI
    ├── docs/                 # arquitectura, specs
    └── README.md
```
