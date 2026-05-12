# Competitive Intelligence Scraper — Rappi vs Uber Eats vs DiDi Food (MX)

Sistema automatizado que recolecta precio unitario, delivery fee, ETA y promociones de SKUs estandarizados (3 fast food en **McDonald's** + 2 retail en **OXXO**) sobre 3 plataformas de delivery (**Rappi**, **Uber Eats**, **DiDi Food**) en 6 direcciones representativas de CDMX + EdoMex. Output: `data/scrapes.csv` y `data/scrapes.json` con una fila por (plataforma, marca, dirección, producto). Informe analítico en `notebooks/insights.ipynb`.

Caso técnico: AI Engineer @ Rappi. Spec original en [`competitive-intelligence/docs/specs/2026-05-11-mvp-4h-design.md`](competitive-intelligence/docs/specs/2026-05-11-mvp-4h-design.md); extensión retail en [`2026-05-12-retail-walmart-design.md`](competitive-intelligence/docs/specs/2026-05-12-retail-walmart-design.md).

---

## Setup

Requiere Python 3.11+.

```bash
cd competitive-intelligence
python -m venv .venv
# Linux/Mac:  source .venv/bin/activate
# Windows:    .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Correr el scraper

**Una corrida completa** (todas las combinaciones platform × brand sobre las 6 direcciones):

```bash
python -m scraper.run --platform all
```

**Subset** (útil para iterar sin re-scrapear todo):

```bash
python -m scraper.run --platform ubereats --brand oxxo
python -m scraper.run --platform rappi --brand mcdonalds
python -m scraper.run --platform rappi --brand oxxo
```

Flags:
- `--platform {rappi,ubereats,didi,all}` (default `all`).
- `--brand <brand_id>` (opcional) — filtra a una marca específica. Valores: `mcdonalds`, `oxxo`.
- `--out-dir <path>` (opcional) — directorio de salida (default `data/`).

**Salidas** (siempre escritas como par CSV + JSON):
- `data/scrapes.csv` — long-format con columnas: `scrape_id, timestamp_utc, platform, brand_id, address_id, address_label, store_id, store_name, product_sku, product_name_raw, unit_price_mxn, delivery_fee_mxn, service_fee_mxn, discount_mxn, total_final_mxn, eta_min, eta_min_low, eta_min_high, available, promo_text, collection_method, notes`.
- `data/scrapes.json` — mismo contenido, formato nested.

Cada corrida emite logs por línea: `<timestamp> scraper.<platform> INFO [<brand>/<address>] inicio` y `... menu items extraídos: N` para visibilidad de progreso.

## Ver el informe

```bash
jupyter notebook competitive-intelligence/notebooks/insights.ipynb
```

El notebook lee `data/scrapes.csv` y produce los gráficos del informe ejecutivo (posicionamiento de precios, ETA por zona, breakdown de fees).

## Catálogos editables

Sin cambiar código, podés modificar:

- [`data/addresses.csv`](competitive-intelligence/data/addresses.csv) — agregar/quitar direcciones (campos: `address_id, label, street, lat, lng, zone_type`).
- [`data/products.csv`](competitive-intelligence/data/products.csv) — SKUs comparables (campos: `sku, canonical_name, vertical, search_keywords, price_min_mxn, price_max_mxn, exclude_keywords`). El `vertical` determina en qué tienda se busca (`fast_food` → McDonald's, `retail` → OXXO).
- [`data/brands.csv`](competitive-intelligence/data/brands.csv) — qué tienda navegar por cada plataforma (`brand_id, platform, vertical, nav_strategy, nav_param`). `nav_strategy=brand_url` lleva a una URL fija; `search_query` usa la búsqueda interna.

## Estructura del repo

```
.
├── README.md                          # este archivo
└── competitive-intelligence/
    ├── scraper/                       # código
    │   ├── base.py                    # ABC PlatformScraper
    │   ├── rappi.py                   # Rappi (Playwright + JSON-LD)
    │   ├── ubereats.py                # Uber Eats (Playwright + JSON-LD/DOM)
    │   ├── didi.py                    # DiDi (stub documentado, app-only)
    │   ├── matching.py                # match keyword + rango de precio
    │   ├── catalog.py                 # carga addresses/products/brands
    │   ├── models.py                  # dataclasses
    │   ├── robots.py                  # respeto de robots.txt
    │   └── run.py                     # CLI orquestador
    ├── data/                          # catálogos + outputs
    ├── notebooks/insights.ipynb       # informe
    ├── scripts/                       # utilitarios (build_notebook, probes)
    └── docs/
        ├── specs/                     # specs de diseño
        ├── plans/                     # planes de implementación
        ├── blockers.md                # bitácora honesta de qué falló y por qué
        └── compliance.md              # robots.txt y ética
```

## Limitaciones conocidas (resumen — detalle completo en `docs/blockers.md`)

- **DiDi Food MX no tiene web pública.** Es 100% app-only. Las filas DiDi se emiten con `available=False` para preservar el shape de la matriz. Capturar precios DiDi exigiría reverseo de la app móvil (fuera del scope ético del brief).
- **Service fees imputados a 0.** Ni Rappi ni Uber Eats exponen el service fee fuera del checkout logueado. Documentado en `compliance.md`.
- **OXXO no vende pañales.** El SKU `panales_t4` fue removido del catálogo tras 0/6 matches en ambas plataformas (OXXO es conveniencia, no supermercado). Para incluir pañales habría que cambiar a Walmart Súper / Chedraui / Soriana, pero ninguno cubre uniformemente CDMX+EdoMex en ambas plataformas a la vez.
- **Walmart no está en Uber Eats MX.** Fue el primer target retail elegido; pivoteamos a OXXO durante implementación.
- **Catálogo McDonald's depende del horario.** A la hora del desayuno (~7–11 AM CST), 5 de 6 direcciones en Rappi devuelven solo el menú de desayuno sin Big Mac/McNuggets/combos. No es bug del scraper; es la realidad del menú activo. Un análisis robusto requiere scrapes en múltiples ventanas horarias.
- **6 direcciones, no 20–50.** Decisión consciente de scope para asegurar calidad por punto (consejo del brief: *"5 direcciones bien scrapeadas > 50 a medias"*).
- **Uber Eats puede bloquear intermitentemente.** Algunas direcciones devuelven 0 anchors en la búsqueda. Mitigaciones: rate-limit 1.5s entre direcciones, User-Agent realista, fallback documentado en `docs/blockers.md`.

## Ética y robots.txt

Ver [`docs/compliance.md`](competitive-intelligence/docs/compliance.md). Se respetan los `robots.txt` de Rappi y Uber Eats; **no** consumimos endpoints `/api*` (prohibidos por robots de Rappi) ni endpoints firmados de Uber Eats. Solo se lee:

- JSON-LD público (datos estructurados que las plataformas exponen deliberadamente para SEO).
- DOM visible al usuario anónimo.

Rate-limit defensivo: 1.5s entre direcciones por scraper. Sin login, sin proxies pagos.
