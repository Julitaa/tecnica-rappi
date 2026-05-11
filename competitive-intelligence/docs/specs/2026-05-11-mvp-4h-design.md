# MVP 4h — Competitive Intelligence Scraper (Rappi / Uber Eats / DiDi Food)

**Fecha:** 2026-05-11
**Autor:** Julieta Pages
**Contexto:** Reto técnico Rappi AI Engineer (48h). Este spec cubre el primer flujo funcional end-to-end. Post-MVP (robustez, escalado, README, deck) queda fuera.

---

## 1. Objetivo

Construir en 4 horas un pipeline ejecutable con un solo comando que:

1. Scrapea precio unitario, delivery fee, service fee, descuento y ETA de **5 productos estandarizados** en **3 plataformas** (Rappi, Uber Eats, DiDi Food) para **6 direcciones de CDMX/EdoMex**.
2. Exporta el resultado a `data/scrapes.csv` y `data/scrapes.json`.
3. Genera 3 gráficos demo-ready en un notebook que soportan los insights de la presentación.

**No-objetivos del MVP:**
- README completo, tests, retries elaborados, dashboard interactivo, múltiples verticales, capturas automáticas. Todo eso es post-MVP.

---

## 2. Stack

| Capa | Tecnología | Razón |
|---|---|---|
| Lenguaje | Python 3.11 | Ecosistema pandas/playwright maduro |
| HTTP/API | `httpx` (async) + `tenacity` | Async para paralelizar direcciones; retries triviales |
| Browser fallback | `playwright` (chromium, async) | Cuando la API resiste captura/firma |
| Captura tráfico | Chrome DevTools → "Copy as cURL" → conversión manual a httpx | 0 costo, suficiente para MVP |
| Storage | pandas → CSV + JSON | Sin BD; el evaluador valida en 1 vistazo |
| Insights | Jupyter + matplotlib/seaborn | Notebook curado supera a Streamlit en costo/beneficio para demo 30 min |
| CLI | `python -m scraper.run --platform [rappi\|ubereats\|didi\|all]` | Reproducibilidad |

**Estrategia "API-first time-boxed":** cada plataforma tiene 30 min de presupuesto para que la API sea viable; si no cede, cae a Playwright. Evita el bloqueo de "perdí 3h reverseando GraphQL".

**Orden de ataque (más a menos probable que la API ceda):**
1. **Rappi** — GraphQL web relativamente accesible. Además es baseline propio.
2. **DiDi Food** — REST histórica más simple.
3. **Uber Eats** — el más blindado (firma de requests, headers `x-uber-*`). Asumir Playwright desde el inicio si la captura inicial muestra signed requests.

---

## 3. Cobertura geográfica (6 direcciones)

CDMX + EdoMex únicamente. Razón: mismo catálogo McDonald's (controla la variable de inventario) y los insights atribuibles a estrategia de plataforma, no a SKU faltante.

| # | Zona | Dirección de referencia | Justificación |
|---|---|---|---|
| 1 | Polanco | Av. Presidente Masaryk 201 | Alto poder adquisitivo, alta densidad de oferta |
| 2 | Roma Norte | Av. Álvaro Obregón 100 | Zona "trendy", alta densidad de repartidores |
| 3 | Del Valle | Av. Coyoacán 1000 | Clase media residencial |
| 4 | Iztapalapa | Av. Ermita Iztapalapa 1000 | Periferia densa, price-sensitive |
| 5 | Santa Fe | Av. Vasco de Quiroga 3800 | Corporativo, lejos del centro histórico |
| 6 | Cuautitlán Izcalli (EdoMex) | Av. Jiménez Cantú | Zona de expansión metropolitana, testea fees fronterizos |

Catálogo persistido en `data/addresses.csv` con columnas: `address_id, label, street, lat, lng, zone_type`.

---

## 4. Productos de referencia (5 SKUs)

| sku | nombre canónico | vertical | rationale |
|---|---|---|---|
| `big_mac` | Big Mac (unidad, sin combo) | Fast food | SKU global, fácil de identificar |
| `mcombo_bigmac_med` | Combo Big Mac mediano (hamburguesa + papas + bebida) | Fast food | Combo medio, refleja ticket promedio |
| `mcnuggets_10` | McNuggets 10 piezas | Fast food | Producto de share alto, sensible a promociones |
| `cocacola_500ml` | Coca-Cola 500ml | Retail/Conveniencia | SKU universal, presente en restaurantes y tiendas |
| `agua_1l` | Agua embotellada 1L | Retail/Conveniencia | Commodity puro: el spread entre plataformas evidencia markup |

Persistido en `data/products.csv` con columnas: `sku, canonical_name, vertical, search_keywords, price_min_mxn, price_max_mxn` (keywords con sinónimos por plataforma para fuzzy matching del nombre raw).

**Regla de matching:** primer item del menú cuyo `product_name_raw` contenga al menos una `search_keyword` Y el precio esté dentro del rango `[price_min_mxn, price_max_mxn]`. Rangos actuales: Big Mac 80-150, Combo 150-250, Nuggets 10pz 60-150, Coca 500ml 20-50, Agua 1L 15-40. Si no hay match, `available=False`.

---

## 5. Schema de datos

### `data/scrapes.csv` (tabla long-format, una fila por (plataforma, dirección, producto))

| Campo | Tipo | Descripción |
|---|---|---|
| `scrape_id` | UUID | Identificador único de la corrida |
| `timestamp_utc` | ISO 8601 | Momento de captura |
| `platform` | enum | `rappi` \| `ubereats` \| `didi` |
| `address_id` | int | FK → addresses.csv |
| `address_label` | string | Denormalizado para conveniencia ("Polanco") |
| `store_id` | string | ID interno de la plataforma |
| `store_name` | string | Ej. "McDonald's Masaryk" |
| `product_sku` | enum | `big_mac` \| `mcombo_bigmac_med` \| `mcnuggets_10` \| `cocacola_500ml` \| `agua_1l` |
| `product_name_raw` | string | Nombre tal cual aparece (auditoría de matching) |
| `unit_price_mxn` | float | Precio del producto |
| `delivery_fee_mxn` | float | Antes de descuentos |
| `service_fee_mxn` | float | Comisión plataforma |
| `discount_mxn` | float | Negativo = descuento aplicado |
| `total_final_mxn` | float | Calculado: `unit_price + delivery_fee + service_fee + discount` |
| `eta_min` | int | Punto medio del rango ETA |
| `eta_min_low` | int | Extremo bajo del rango |
| `eta_min_high` | int | Extremo alto del rango |
| `available` | bool | Producto efectivamente disponible |
| `promo_text` | string | Texto raw de promoción visible (ej. "2x1 hamburguesas") |
| `collection_method` | enum | `api` \| `playwright` (auditoría de calidad) |
| `notes` | string | Errores parciales, observaciones |

### `data/scrapes.json`
Mismo contenido, formato nested (lista de objetos). Generado por `df.to_json(orient='records', indent=2)`.

### `data/addresses.csv`, `data/products.csv`
Catálogos fijos hardcodeados al inicio.

**Diseño rationale:**
- `unit_price` separado de fees permite cualquier insight (precio puro vs total).
- `eta_min_low/high` además del punto medio: el rango es el insight, no el promedio.
- `collection_method` es honestidad operativa — el brief premia visibilidad de qué se logró y qué no.
- `promo_text` raw + `discount_mxn` numérico: el numérico para gráficos, el texto para el insight cualitativo.

---

## 6. Arquitectura de código

```
competitive-intelligence/
├── scraper/
│   ├── __init__.py
│   ├── base.py           # ABC PlatformScraper: scrape(address, products) -> List[Row]
│   ├── rappi.py          # RappiScraper(PlatformScraper) — intenta API, fallback Playwright
│   ├── ubereats.py
│   ├── didi.py
│   ├── models.py         # dataclass ScrapeRow (espejo del schema)
│   ├── matching.py       # match_product(name_raw, sku, search_keywords) -> bool
│   └── run.py            # CLI: argparse, orquesta, escribe CSV/JSON
├── data/
│   ├── addresses.csv
│   ├── products.csv
│   ├── scrapes.csv       # generado
│   └── scrapes.json      # generado
├── notebooks/
│   └── insights.ipynb    # 3 gráficos demo
├── docs/
│   ├── specs/2026-05-11-mvp-4h-design.md
│   └── blockers.md       # bitácora de qué falló y por qué
└── requirements.txt
```

**Interfaz `PlatformScraper`:** un único método `scrape(address: Address, products: List[Product]) -> List[ScrapeRow]`. Cada implementación decide internamente API vs Playwright. Esto deja al `run.py` agnóstico.

---

## 7. Cronograma de 4 horas

| Tramo | Tarea | Entregable | Checkpoint |
|---|---|---|---|
| H0:00–H0:30 | Setup: repo, deps, estructura, `addresses.csv` + `products.csv` hardcodeados, esqueleto `base.py` + `run.py` | Pipeline corre con scraper dummy que devuelve filas vacías | CSV vacío bien formado |
| H0:30–H2:00 | **Rappi end-to-end**: 20 min captura DevTools, 30 min httpx, 20 min validar 6 direcciones, 20 min fallback Playwright si API falla | 30 filas reales (6 dirs × 5 productos) | `data/scrapes.csv` con 30 filas Rappi |
| H2:00–H3:00 | **DiDi**: 15 min captura, 30 min implementación reusando scaffolding, 15 min validación | 60 filas acumuladas | CSV con 2 plataformas |
| H3:00–H3:45 | **Uber Eats**: time-box estricto. Si API no cede a los 30 min → Playwright headless con solo 3 direcciones, documentar limitación en `blockers.md` | 90 filas (o 75 si Uber parcial) | CSV con 3 plataformas |
| H3:45–H4:00 | **Notebook**: 3 gráficos hardcodeados | `insights.ipynb` ejecutable | Demo-ready |

**Los 3 gráficos del notebook (fijos):**
1. Precio total promedio por plataforma — barras agrupadas por SKU.
2. ETA promedio por zona × plataforma — heatmap.
3. Desglose `unit_price + delivery_fee + service_fee + discount` por plataforma — barras apiladas.

**Reglas de oro:**
- No agregar plataformas/productos/direcciones durante las 4h.
- README, retries elaborados, deck → post-MVP.
- Commits en cada checkpoint, aunque sean WIP.
- Cada blocker → 2 líneas en `docs/blockers.md` y seguir.

---

## 8. Manejo de errores y casos edge

| Caso | Comportamiento |
|---|---|
| Plataforma bloquea API (403/429) | Caer a Playwright para esa plataforma; loguear en `blockers.md` |
| Producto no encontrado en la tienda | Fila con `available=False`, precios `null`, `notes` describe |
| Dirección sin McDonald's cercano | Fila con `store_id=null`, `available=False`, `notes="no_store_in_area"` |
| Playwright timeout (>30s) | Reintentar 1 vez; si falla, fila vacía con `notes="timeout"` |
| Captcha visible | Detectar por selector, abortar dirección, loguear blocker |

**No-objetivos de manejo de errores:** retries exponenciales sofisticados, rotación de proxies, persistencia de sesión entre corridas. Eso es post-MVP.

---

## 9. Consideraciones éticas y legales

- Rate limiting: `asyncio.sleep(1.5)` entre requests por plataforma.
- User-Agent realista (Chrome desktop reciente).
- Sin volumen masivo: el scraper hace 1 request de menú por (dirección × plataforma) = 18 requests; los 5 SKUs se extraen del mismo payload. Comparable a un usuario humano explorando opciones.
- Datos públicamente accesibles desde la web logueada del usuario; no se accede a información privada de otros usuarios.
- No se persisten credenciales en el repo (variables de entorno o `.env` gitignored).

---

## 10. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Uber Eats firma requests y rompe API | Alta | Playwright desde inicio para Uber; documentar |
| Captcha bloquea Playwright en corrida final | Media | Headless=False durante dev para detectar; tener dataset parcial pre-cacheado como backup demo |
| Captura DevTools toma más de 30 min | Media | Time-box estricto; saltar a Playwright sin culpa |
| Catálogo McDonald's varía entre zonas | Baja | Matching por keywords + rango de precio absorbe variaciones de nombre |
| Chatbot en paralelo consume tiempo | Alta | Las 4h son bloque dedicado; chatbot fuera de este bloque |

---

## 11. Definición de "MVP terminado"

Al cierre de H4:00 debe existir:

- [ ] `python -m scraper.run --platform all` ejecuta sin crashear.
- [ ] `data/scrapes.csv` con al menos 60 filas reales (2 plataformas completas, 5 SKUs × 6 dirs).
- [ ] `data/scrapes.json` regenerado.
- [ ] `notebooks/insights.ipynb` corre top-to-bottom y produce los 3 gráficos.
- [ ] `docs/blockers.md` documenta cualquier limitación.
- [ ] Repo commiteado en cada checkpoint.
