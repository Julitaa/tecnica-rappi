# Gap Analysis vs Brief Rappi

Comparación entre los requisitos del PDF del brief y el estado actual del repo.

## Sistema de Scraping (70%)

| Requisito brief | Estado | Notas |
|---|---|---|
| ≥ 2 competidores + Rappi | ✅ | Rappi + Uber Eats con data real; DiDi documentado como blocker (app-only) |
| ≥ 3 métricas | ✅ | `unit_price_mxn`, `delivery_fee_mxn`, `eta_min`, `promo_text`, `total_final_mxn`, `discount_mxn` (6/7 métricas listadas) |
| 20–50 direcciones | ⚠️ | 6 direcciones representativas (CDMX + EdoMex). Decisión consciente — el consejo del brief dice *"5 direcciones bien scrapeadas > 50 a medias"* |
| Productos Fast Food (3) | ✅ | `big_mac`, `mcombo_bigmac_med`, `mcnuggets_10` |
| Productos Retail (3) | ⚠️ | `cocacola_500ml`, `agua_1l` ✓ · `panales_t4` removido — OXXO no los vende, ver `blockers.md` |
| Comando único | ✅ | `python -m scraper.run --platform all` |
| CSV + JSON output | ✅ | `data/scrapes.{csv,json}` |
| robots.txt respetado | ✅ | Ver `docs/compliance.md` |
| User-Agents apropiados | ✅ | Chrome desktop reciente |
| Rate limiting | ✅ | 1.5s entre direcciones por scraper |

### Bonus

| Bonus brief | Estado |
|---|---|
| Múltiples verticales (restaurantes + retail) | ✅ Fast food (McDonald's) + Retail (OXXO) |
| Mismo producto en diferentes plataformas | ✅ Mismos SKUs en Rappi y Uber Eats |
| Capturas automáticas de pantalla | ❌ No implementado |

## Informe de Insights (30%)

| Requisito brief | Estado |
|---|---|
| Posicionamiento de precios | ⏳ Notebook existente; ajustar para incluir retail/OXXO |
| Ventaja/desventaja operacional (ETA) | ⏳ Idem |
| Estructura de fees | ⏳ Idem |
| Estrategia promocional (`promo_text`) | ⏳ Idem |
| Variabilidad geográfica | ⏳ Idem |
| Top 5 Insights con Finding/Impacto/Recomendación | ⏳ En notebook |
| ≥ 3 visualizaciones | ⏳ Notebook tiene 3 gráficos del tramo 5; regenerar con la data nueva |

### Bonus

| Bonus brief | Estado |
|---|---|
| Dashboard interactivo (Streamlit/Power BI) | ❌ No (notebook es suficiente para 30 min demo) |
| Análisis de tendencias temporales | ❌ Solo 1 snapshot. El hallazgo del horario del desayuno (ver `blockers.md`) es un argumento para hacer múltiples snapshots, pero queda como next-step |

## Reproducibilidad / Documentación (5%)

| Requisito brief | Estado |
|---|---|
| README setup | ✅ [`README.md`](../../README.md) raíz del repo |
| README cómo ejecutar | ✅ |
| README cómo generar informe | ✅ |
| README limitaciones conocidas | ✅ Sección dedicada |
| Output estructurado | ✅ |

## Pendientes después de la última corrida

1. Regenerar `notebooks/insights.ipynb` para incluir filas con `brand_id` (segmentación retail/fast_food).
2. Tabla pivote `platform × brand_id × product_sku → mean(unit_price_mxn)` para insight de retail.
3. Top 5 insights formalizados con Finding/Impacto/Recomendación.

## Riesgos para la demo

- **McDonald's en Rappi** muestra solo desayunos antes de las 11 AM CST → re-scrapear cerca del mediodía para tener Big Mac.
- **Uber Eats** detección de bots: re-scrape puede dar resultados distintos. Recomendado: tener data preexistente como backup.
- **DiDi** sigue al 0% (real-world finding, no bug).
