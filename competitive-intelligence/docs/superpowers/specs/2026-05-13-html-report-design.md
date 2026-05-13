# Diseño: Informe HTML Ejecutivo — Competitive Intelligence

**Fecha:** 2026-05-13  
**Autora:** Julieta Pages  
**Proyecto:** Rappi Technical Challenge — Competitive Intelligence

---

## Objetivo

Convertir el análisis del notebook `insights.ipynb` en un informe HTML ejecutivo de una sola página, portable, que se pueda imprimir a PDF desde el browser y que cumpla todos los requisitos del challenge.

---

## Archivos

| Archivo | Descripción |
|---|---|
| `competitive-intelligence/report/generate_report.py` | Script generador (único archivo a crear) |
| `competitive-intelligence/report/competitive_intelligence_2026.html` | Output generado (no commiteado) |
| `competitive-intelligence/scrapes.csv` | Fuente de datos (78 filas, Rappi + UberEats + DiDi) |

---

## Estructura del HTML (scroll vertical)

1. **Cover / Header** — Wordmark "Rappi", título del informe, fecha, autora, tagline
2. **Executive Summary** — Tabla 5×3 con semáforo por dimensión (Precios / ETA / Fees / Promos / Geo) y conclusión en 2-3 líneas
3. **Sección 1 — Posicionamiento de precios** — Bar chart agrupado (SKU × plataforma) + párrafo de lectura
4. **Sección 2 — Ventaja operacional (ETA)** — Heatmap zona × plataforma + párrafo
5. **Sección 3 — Estructura de fees** — Stacked bar (unit_price + delivery_fee + service_fee − discount) por plataforma + párrafo
6. **Sección 4 — Estrategia promocional** — Bar % promo_text + tabla de textos únicos por plataforma
7. **Sección 5 — Variabilidad geográfica** — Bar chart ticket final por zona × plataforma + párrafo
8. **Top 5 Insights Accionables** — 5 cards con Finding / Impacto / Recomendación, color-coded por urgencia
9. **Limitaciones y próximos pasos** — Lista bullets
10. **Footer** — Nota metodológica, fecha snapshot, disclaimer anónimo

---

## Estilo visual

- **Fuente:** Inter (Google Fonts CDN) + system-ui fallback
- **Fondo:** `#FFFFFF` / `#F8F9FA` (alternado por sección)
- **Texto:** `#1A1A2E`
- **Acento principal:** `#FF441F` (naranja Rappi) — headers, sidebar activo, borde cards urgentes
- **Sidebar fija:** tabla de contenidos con links ancla (#seccion-1 … #insights)
- **Ancho máximo contenido:** 900px, centrado
- **Cards insights:** sombra `box-shadow: 0 2px 8px rgba(0,0,0,0.08)`, borde izquierdo 4px por urgencia (rojo = alta, naranja = media, verde = baja)
- **Print-friendly:** `@media print` oculta la sidebar, ajusta márgenes

---

## Gráficos (Plotly, template `plotly_white`)

| # | Tipo | Datos | Variables |
|---|---|---|---|
| 1 | Bar chart agrupado | `av` (available=True), fast-food SKUs | x=SKU, color=platform, y=unit_price_mxn |
| 2 | Heatmap | `av`, pivot address_label × platform | valores=eta_min, cmap inverso |
| 3 | Stacked bar | `av`, groupby platform | componentes: unit_price, delivery_fee, service_fee, discount |
| 4 | Bar horizontal | `df`, groupby platform | y=% filas con promo_text |
| 5 | Bar chart agrupado | `av`, groupby address_label × platform | y=total_final_mxn |

**Colores por plataforma:** Rappi `#FF441F`, UberEats `#06C167`, DiDi `#FF7900`

Todos los gráficos embebidos como JSON en el HTML via `plotly.io.to_json()` + `plotly.js` via CDN (`https://cdn.plot.ly/plotly-latest.min.js`). HTML es un único archivo autosuficiente.

---

## Datos

- **Fuente:** `competitive-intelligence/scrapes.csv` (78 filas, 3 plataformas)
- **Filtro cuantitativo:** `available == True` para gráficos de precio/fees/ETA
- **Nota DiDi:** 0 observaciones disponibles — aparece en gráficos de presencia/promos pero no en precios/fees

---

## Ejecución

```bash
cd competitive-intelligence
python report/generate_report.py
# Output: report/competitive_intelligence_2026.html
```

---

## Criterios de éxito

- [ ] HTML abre en Chrome/Firefox sin errores de consola
- [ ] Todos los gráficos renderizan correctamente
- [ ] Impresión a PDF (Ctrl+P) produce un doc legible sin sidebar
- [ ] Los 5 insights tienen Finding / Impacto / Recomendación completos
- [ ] Al menos 3 gráficos soportan los insights
- [ ] El informe es autocontenido (sin dependencias externas de archivos locales)
