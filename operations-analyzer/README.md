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

> **Nota Windows:** si `uv` no está en PATH, agregarlo primero:
> ```powershell
> $env:Path += ";$env:USERPROFILE\.local\bin"
> ```

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
