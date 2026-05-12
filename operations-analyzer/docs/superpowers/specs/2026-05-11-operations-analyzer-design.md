# Sistema de Análisis Inteligente para Operaciones Rappi — Diseño

**Fecha:** 2026-05-11
**Autor:** Julieta Pages
**Contexto:** Caso técnico Rappi (rol AI Engineer). Dos entregables: (1) bot conversacional de datos sobre métricas operacionales, (2) sistema de insights automáticos con reporte ejecutivo.

---

## 1. Objetivo y alcance

Construir un sistema local que permita a usuarios no técnicos (Strategy/Planning/Analytics y Operations) hacer preguntas en lenguaje natural sobre métricas operacionales por zona, y que genere automáticamente un reporte ejecutivo con los insights más relevantes.

**Alcance acordado (Plan A — tiempo ajustado, ~12-14h):**
- Bot conversacional cubriendo los 6 casos de uso del brief (filtrado, comparación, tendencia, agregación, multivariable, inferencia) con memoria conversacional y sugerencias proactivas.
- Sistema de insights con 5 categorías de detección (anomalías, tendencias, benchmarking, correlaciones, oportunidades) y reporte ejecutivo en PDF.
- Frontend funcional con paleta Rappi (naranja `#FF441F`).
- Tests unitarios para toolbox, detectores y sandbox.
- README con instrucciones, decisiones técnicas, trade-offs y limitaciones.

**Fuera de alcance (stretch goals si sobra tiempo):**
- Visualizaciones inline (Plotly) en el chat.
- Export CSV de resultados.
- Deployment cloud (Streamlit Cloud / Render / Railway).
- Envío del reporte por email.

---

## 2. Stack tecnológico

| Capa | Elección | Razón |
|---|---|---|
| LLM | OpenAI `gpt-4o` vía API | Tool-calling estable, demo confiable en vivo, costo bajo (~$0.20 / sesión completa de demo) |
| Backend | FastAPI (Python 3.11+) | Async, validación con Pydantic, OpenAPI gratis, stack familiar al usuario |
| Frontend | Next.js (App Router) + TypeScript + TailwindCSS + shadcn/ui | Stack del usuario, estética rápida, paleta Rappi customizable |
| Datos en memoria | pandas + DuckDB (in-process) | Dataset chico (~14k filas), pandas para detectores, DuckDB para sandbox SQL seguro |
| Caché | Parquet en disco | Arranques instantáneos tras primer load |
| PDF | `markdown` + `weasyprint` | Markdown → HTML → PDF sin dependencias pesadas |
| Package manager | `uv` (backend) + `pnpm` (frontend) | Velocidad |
| Tests | `pytest` | Estándar |

**Costo estimado:**
- Sesión de 10 preguntas: ~$0.10-0.20 (gpt-4o input/output).
- Generación de un reporte ejecutivo completo: ~$0.05-0.10.
- Desarrollo + demo total: <$5.

**Arquitectura LLM-agnostic:** el wrapper `llm/client.py` permite cambiar el provider a Groq (Llama 3.3 70B) o Anthropic con 3 líneas. Esto se menciona en la presentación como trade-off consciente.

---

## 3. Arquitectura general

```
┌─────────────────────────────────────────────────────────┐
│  Next.js Frontend                                       │
│  - Chat (left panel)                                    │
│  - Report panel (right panel, on-demand)                │
│  - Paleta Rappi: primary #FF441F, neutros grises        │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (REST + SSE streaming)
┌──────────────────────▼──────────────────────────────────┐
│  FastAPI Backend                                        │
│  ┌──────────────────┐    ┌────────────────────────────┐ │
│  │  /chat (SSE)     │    │  /report (POST → PDF)      │ │
│  │  ChatService     │    │  InsightsService           │ │
│  └────────┬─────────┘    └──────────┬─────────────────┘ │
│           │                         │                   │
│  ┌────────▼─────────────────────────▼────────────────┐  │
│  │  Core: Repository + Toolbox + LLM client          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                       │
              ┌────────▼──────────────────┐
              │  metrics_df, orders_df     │
              │  (pandas, in-memory,       │
              │   cache parquet en disco)  │
              └────────────────────────────┘
```

**Endpoints REST:**
- `POST /chat` — body `{session_id: str, message: str}`. Devuelve SSE con tokens streaming y, al final, un evento `{type: "done", sources: [...], suggestions: [...]}`.
- `POST /chat/reset` — borra el historial de un `session_id`.
- `POST /report` — devuelve `application/pdf` con el reporte ejecutivo. Acepta query param `?format=markdown` para previsualizar en pantalla antes de descargar.
- `GET /health` — readiness check.

---

## 4. Capa de datos

### 4.1 Loader (`data/loader.py`)

Al startup de FastAPI:
1. Si existe `data/cache.parquet`, lo carga. Si no, lee `data/source.xlsx`.
2. Pivota de formato wide (`L8W..L0W`) a long: una fila por (zona, métrica, week_offset).
3. Valida: nulls, negativos, porcentajes >1.0 → loggea warnings, no rompe.
4. Persiste a Parquet para próximos arranques.
5. Guarda `metrics_df` y `orders_df` en `app.state`.

### 4.2 Esquema interno (long format)

**`metrics_df`:**
| columna | tipo | descripción |
|---|---|---|
| country | str | código país (AR, BR, CL, CO, CR, EC, MX, PE, UY) |
| city | str | ciudad |
| zone | str | zona/barrio |
| zone_type | str | Wealthy / Non Wealthy |
| zone_prioritization | str | High Priority / Prioritized / Not Prioritized |
| metric | str | nombre de la métrica |
| week_offset | int | 0 = semana actual (L0W), 8 = hace 8 semanas (L8W) |
| value | float | valor de la métrica |

**`orders_df`:** mismo esquema sin `zone_type`/`zone_prioritization` (se joinean desde `metrics_df` cuando se necesitan).

### 4.3 Glosario (`data/glossary.py`)

Diccionario hardcodeado con metadata de negocio por métrica:
```python
{
  "Lead Penetration": {
    "description": "Tiendas habilitadas / (leads + habilitadas + salidas)",
    "higher_is_better": True,
    "format": "percentage",
    "category": "Supply",
  },
  ...
}
```

Se usa para: (1) inyectar contexto de dominio en el SYSTEM_PROMPT, (2) que el detector sepa si un cambio es "deterioro" o "mejora".

### 4.4 Repository (`data/repository.py`)

Fachada tipada sobre los DataFrames. Métodos: `get_metric_series(country, zone, metric, weeks)`, `list_zones(filters)`, `get_glossary_entry(metric)`, etc. Devuelve dataclasses, no DataFrames crudos. Aísla al resto del código de pandas.

---

## 5. ChatService (bot conversacional)

### 5.1 Flujo

```
user_msg → ChatService.handle(session_id, msg)
  1. Append a history[session_id] (sliding window últimos 10).
  2. Build messages = [SYSTEM_PROMPT, *history].
  3. Loop hasta no haya tool_calls (max 5 iter):
       - openai.chat.completions.create(model="gpt-4o", tools=TOOLBOX, messages, stream=True)
       - Ejecutar cada tool_call → resultado JSON
       - Append tool result a messages
  4. Stream tokens de la respuesta final al cliente.
  5. Append respuesta al history.
  6. Generar 1-2 sugerencias de follow-up (segunda llamada barata o derivadas de las tools usadas).
```

### 5.2 SYSTEM_PROMPT (resumen)

- Rol: asistente de datos para Operations/SP&A de Rappi.
- Glosario de métricas inyectado.
- Definiciones de negocio: "zona problemática" = métricas deterioradas vs L4W o vs benchmark del país; convenciones temporales (L0W..L8W).
- Convención de respuesta: citar zona+país+métrica+ventana temporal; pedir aclaración si la pregunta es ambigua; sugerir 1-2 análisis relacionados al final.
- Mandato: para responder números, **siempre** usar tools; nunca inventar.

### 5.3 Toolbox (`chat/toolbox.py`)

| Tool | Caso de uso del brief |
|---|---|
| `top_n_zones(metric, n, week_offset=0, filters, order)` | Filtrado: "top 5 con mayor X" |
| `compare_segments(metric, group_by, filters)` | Comparación: "Wealthy vs Non Wealthy en MX" |
| `metric_trend(metric, zone, weeks=8)` | Tendencia temporal |
| `aggregate(metric, group_by, agg=mean, filters)` | Agregación: "promedio por país" |
| `multivariable_filter(conditions)` | "alto X pero bajo Y" |
| `correlate_metrics(metric_a, metric_b, scope)` | Correlaciones |
| `growth_explainer(metric="Orders", weeks=5, top_n=10)` | Inferencia: zonas que más crecen + comparación con otras métricas para hipotetizar causa |
| `run_sql(query)` | Fallback DuckDB con whitelist de tablas |

Cada tool tiene schema JSON (OpenAI function-calling format) y devuelve `{data: [...], summary: str, metadata: {...}}`. `data` para citar números, `summary` para narrar.

### 5.4 Sandbox SQL (`chat/sandbox.py`)

- Parser `sqlglot` valida el query antes de ejecutarlo.
- Whitelist: solo `SELECT` / `WITH`; solo tablas `metrics_df` y `orders_df`; bloquea `INSERT`, `UPDATE`, `DELETE`, `ATTACH`, `PRAGMA`, `COPY`, `LOAD`.
- DuckDB ejecuta sobre los DataFrames vía `duckdb.sql(query)` con timeout 5s.
- Resultado capeado a 1000 filas para evitar respuestas gigantes.

### 5.5 Memoria conversacional

- `dict[session_id, list[Message]]` en memoria del proceso.
- Sliding window de últimos 10 mensajes (user + assistant + tool).
- `POST /chat/reset` limpia un session_id.
- Sin persistencia (se pierde al reiniciar el server — aceptable para alcance).

### 5.6 Sugerencias proactivas

Después de la respuesta principal, el LLM genera 1-2 follow-ups con un prompt corto que recibe la última pregunta + tools usados. Se devuelven al frontend como chips clickeables.

---

## 6. Sistema de Insights Automáticos

### 6.1 Pipeline

```
metrics_df + orders_df
    │
    ▼
detector.py (puro pandas)  →  lista de Finding objs
    │
    ▼
ranker.py  →  scoring + dedup + top-K (K≈15-20)
    │
    ▼
reporter.py (LLM gpt-4o)  →  Markdown
    │
    ▼
markdown → HTML → PDF (weasyprint)
```

### 6.2 Estructura `Finding` (dataclass)

```python
@dataclass
class Finding:
    category: Literal["anomaly", "trend", "benchmark", "correlation", "opportunity"]
    severity: float            # 0..1, para ranking
    zone: dict                 # country, city, zone, zone_type
    metric: str
    evidence: dict             # números crudos (delta, p-value, weeks, etc.)
    headline: str              # generado por el detector, no por LLM
```

### 6.3 Detectores

1. **`detect_anomalies`** — para cada (zona, métrica), `pct_change = (L0W - L1W) / L1W`. Flag si `|pct_change| > 10%`. Severity normalizada por z-score sobre la desviación histórica de la zona-métrica en las 8 semanas (evita falsos positivos en métricas naturalmente volátiles).

2. **`detect_negative_trends`** — rachas de ≥3 semanas consecutivas de deterioro (considerando `higher_is_better` del glosario). Severity = magnitud del deterioro acumulado.

3. **`detect_benchmark_divergence`** — agrupar por `(country, zone_type)`. Calcular percentil de cada zona en L0W para cada métrica. Flag zonas en p<10 (under) y p>90 (over). Severity = distancia al mediano del grupo.

4. **`detect_correlations`** — matriz de correlación entre métricas en L0W (panel de zonas). Flag pares con `|r| > 0.6` y `n ≥ 30`. Extra: zonas con residual alto en pares correlacionados (rompen el patrón).

5. **`detect_opportunities`** — combina señales: zonas High Priority bajo p25 del grupo (under-performance estratégica); zonas Non Wealthy con crecimiento Orders > media país; zonas Wealthy con Lead Penetration estancado y Orders creciendo (oportunidad de captar leads).

**Thresholds** (configurables vía `insights/config.py`):
- Anomalía: `pct_change > 10%`
- Tendencia: ≥3 semanas consecutivas
- Correlación: `|r| > 0.6`, `n ≥ 30`
- Top-K: 15-20 findings totales, distribuidos por categoría

### 6.4 Ranker (`insights/ranker.py`)

- Ordena por severity desc.
- Deduplica: si una zona aparece en >1 categoría por la misma raíz (ej: anomalía + tendencia en la misma métrica), se queda con la de mayor severity.
- Devuelve top-K balanceado entre categorías (cap por categoría para evitar reportes sesgados).

### 6.5 Reporter (`insights/reporter.py`)

- Un solo prompt al LLM con: lista de findings (JSON), glosario, instrucciones de formato.
- El LLM **nunca inventa números** — los recibe en `evidence` y se le instruye a citarlos literalmente.
- Output Markdown con estructura:

```markdown
# Reporte Ejecutivo — Operaciones Rappi
## Resumen Ejecutivo (top 3-5 hallazgos críticos)
## Anomalías
### [headline]
- Evidencia: ...
- Recomendación: ...
## Tendencias preocupantes
## Benchmarking
## Correlaciones
## Oportunidades
## Metodología (apéndice corto)
```

- Markdown → HTML (con CSS de marca Rappi) → PDF con `weasyprint`.
- Endpoint `/report?format=markdown` devuelve el Markdown crudo para previsualización en el frontend antes de descargar el PDF.

---

## 7. Frontend (Next.js)

### 7.1 Estructura

- 1 página (`app/page.tsx`) con layout split:
  - **Izquierda**: chat (input + lista de mensajes + chips de sugerencias).
  - **Derecha**: panel de reporte (oculto por default, se abre al clickear "Generar reporte ejecutivo"). Muestra el Markdown renderizado y un botón "Descargar PDF".

### 7.2 Componentes

- `<ChatWindow>` — contenedor con estado de mensajes y session_id.
- `<MessageList>` — renderiza mensajes con `react-markdown` (tablas, listas, code).
- `<MessageInput>` — textarea + botón enviar + chips de sugerencias.
- `<ReportPanel>` — fetch a `/report?format=markdown`, render con `react-markdown`, botón "Descargar PDF".

### 7.3 Estado y networking

- `useChat` hook con `session_id` en localStorage (uuid v4 generado client-side).
- Streaming desde `/chat` con `fetch` + `ReadableStream` (SSE).
- Sin auth, sin routing complejo, sin dark mode.

### 7.4 Estilos — paleta Rappi

- Primary: `#FF441F` (naranja Rappi) para botones, links activos, header.
- Neutros: blanco `#FFFFFF`, gris claro `#F5F5F5`, gris medio `#737373`, gris oscuro `#1A1A1A`.
- Tailwind config con `colors.rappi.primary = "#FF441F"`.
- shadcn/ui para componentes base (button, input, card).

---

## 8. Estructura de carpetas

```
operations-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── main.py           # FastAPI app + routes
│   │   │   └── schemas.py        # Pydantic models
│   │   ├── data/
│   │   │   ├── loader.py
│   │   │   ├── repository.py
│   │   │   └── glossary.py
│   │   ├── chat/
│   │   │   ├── service.py
│   │   │   ├── toolbox.py
│   │   │   ├── sandbox.py
│   │   │   └── prompts.py
│   │   ├── insights/
│   │   │   ├── detector.py
│   │   │   ├── ranker.py
│   │   │   ├── reporter.py
│   │   │   ├── config.py
│   │   │   └── prompts.py
│   │   └── llm/
│   │       └── client.py
│   ├── tests/
│   │   ├── test_toolbox.py
│   │   ├── test_detector.py
│   │   └── test_sandbox.py
│   ├── scripts/
│   │   └── eval_questions.py     # smoke-test pre-demo
│   ├── data/
│   │   ├── source.xlsx
│   │   └── cache.parquet         # generado
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── chat-window.tsx
│   │   ├── message.tsx
│   │   ├── message-input.tsx
│   │   └── report-panel.tsx
│   ├── lib/
│   │   └── api-client.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── README.md
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-11-operations-analyzer-design.md
```

---

## 9. Testing

**Unit tests (pytest):**
- `test_toolbox.py` — cada una de las 8 tools con 1-2 casos felices + 1 edge case (zona inexistente, métrica desconocida). ~15 tests.
- `test_detector.py` — cada detector con DataFrame sintético pequeño que dispara/no dispara. ~10 tests.
- `test_sandbox.py` — queries válidas pasan; `INSERT`/`ATTACH`/`PRAGMA`/tablas no permitidas rechazadas. ~6 tests.

**Sin tests de:**
- LLM (caro, frágil, fuera de alcance).
- Frontend (alcance).

**Smoke-test manual (`scripts/eval_questions.py`):**
Corre las 6 preguntas del brief contra el backend y printea respuestas. Sirve para validar antes de la demo.

---

## 10. README (estructura)

1. **Qué hace** — 1 párrafo + screenshot del chat.
2. **Cómo correrlo local:**
   - Backend: `uv sync && uv run uvicorn app.api.main:app --reload`
   - Frontend: `pnpm i && pnpm dev`
   - `.env`: `OPENAI_API_KEY=...`
3. **Arquitectura** — diagrama de Sección 3 + bullets.
4. **Decisiones técnicas y trade-offs:**
   - Por qué OpenAI gpt-4o (precisión + demo confiable).
   - Por qué híbrido toolbox + SQL sandbox.
   - Por qué pandas + DuckDB en lugar de SQLite/Postgres.
   - Costo estimado por uso.
5. **Limitaciones y próximos pasos** — sin persistencia, sin visualizaciones, sin auth, sin email; ideas: cache de respuestas, RAG sobre histórico, deployment cloud.

---

## 11. Mapeo a criterios de evaluación

| Criterio | Peso | Cómo lo cubrimos |
|---|---|---|
| Arquitectura y diseño técnico | 15% | Separación clara backend/frontend, repository pattern, toolbox + sandbox híbrido, decisiones documentadas en README |
| Calidad del bot | 35% | 8 tools cubriendo los 6 casos de uso del brief, memoria conversacional, sugerencias proactivas, glosario inyectado, sandbox SQL para queries no anticipadas |
| Calidad de insights | 30% | 5 detectores determinísticos (no alucinables) + LLM solo redacta narrativa, ranker con dedup, recomendaciones accionables |
| Código y documentación | 5% | Tipado con Pydantic, tests unitarios, README estructurado, spec en `/docs` |
| Presentación y comunicación | 20% | Demo en vivo con frontend funcional, paleta Rappi, reporte PDF descargable |

---

## 12. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Tiempo justo (12-14h) | Plan A acotado, stretch goals separados, smoke-test pre-demo |
| LLM falla tool-calling en demo en vivo | gpt-4o (no mini) + max 5 iter de tool loop + fallback a SQL sandbox |
| Query SQL maliciosa o cara | Whitelist sqlglot + timeout 5s + cap 1000 filas |
| PDF de reporte sale feo | CSS minimalista probado temprano; fallback HTML descargable |
| API key se queda sin crédito en demo | Mock mode (`USE_MOCK_LLM=true`) que devuelve respuestas pre-grabadas para las 6 preguntas del brief |

---

## 13. Stretch goals (si sobra tiempo)

1. **Visualizaciones inline** — Plotly en el chat (líneas para tendencias, barras para comparaciones). Tool extra `generate_chart(spec)` que devuelve JSON Plotly. ~2-3h.
2. **Export CSV** — botón en cada respuesta tabular que descarga los datos. ~30min.
3. **Email del reporte** — endpoint `/report/email` con SMTP. ~1h.
4. **Deployment** — Render para backend + Vercel para frontend. ~1-2h.
