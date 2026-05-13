# Competitive Intelligence Scraper

Recolecta precio unitario, delivery fee, ETA y disponibilidad de SKUs estandarizados (McDonald's + OXXO) en **Rappi**, **Uber Eats** y **DiDi Food** sobre 10 direcciones de CDMX + EdoMex.

**Output:** `data/scrapes.csv` y `data/scrapes.json` | **Reportes:** `report/competitive_intelligence_2026.html` + `notebooks/insights.ipynb`

---

## Uso rápido

### 1. Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Correr scraper

**Completo** (todas plataformas × marcas):
```bash
python -m scraper.run --platform all
```

**Subset**:
```bash
python -m scraper.run --platform rappi --brand mcdonalds
python -m scraper.run --platform ubereats --brand oxxo
```

**Opciones:**
- `--platform {rappi,ubereats,didi,all}` (default: `all`)
- `--brand {mcdonalds,oxxo}` (opcional)
- `--out-dir <path>` (default: `data/`)

### 3. Generar reportes

**Reporte HTML ejecutivo** (print-to-PDF ready):
```bash
python report/generate_report.py
Output: report/competitive_intelligence_2026.html
```

**Notebook exploratorio**:
```bash
jupyter notebook notebooks/insights.ipynb
```

---

## Cobertura geográfica

20 direcciones seleccionadas para maximizar diversidad analítica en 3 dimensiones: **nivel socioeconómico**, **cuadrante geográfico** y **perfil de uso**.

### Primeras 10 direcciones (cobertura base)

| # | Zona | Zone type | NSE | Cuadrante | Perfil |
|---|------|-----------|-----|-----------|--------|
| 1 | Polanco | premium | A/B | NO | Residencial alto, marcas premium |
| 2 | Roma Norte | trendy | B/C+ | Centro-O | Hipster, alta densidad de restaurantes |
| 3 | Del Valle | residencial | C+ | Centro-S | Clase media consolidada |
| 4 | Iztapalapa | periferia | D | SE | Zona popular de mayor densidad de CDMX |
| 5 | Santa Fe | corporativo | A/B | SO | Oficinas, consumo en horario laboral |
| 6 | Cuautitlán Izcalli | edomex | C/D | Norte EdoMex | EdoMex suburbano, buena cobertura Rappi |
| 7 | Centro Histórico | historico | C | Centro | Alta densidad peatonal, turismo, mix NSE |
| 8 | Coyoacán | cultural | B/C+ | Sur-Centro | Universitario/cultural, diferente a Roma |
| 9 | Ecatepec | edomex_popular | D | Este EdoMex | Municipio más poblado del país, mercado masivo |
| 10 | Insurgentes Sur | residencial_sur | B/C+ | Sur | Corredor sur, contraste con Del Valle |

### Segundas 10 direcciones (expansión y complemento)

| # | Zona | Zone type | NSE | Cuadrante | Perfil | Justificación |
|---|------|-----------|-----|-----------|--------|---|
| 11 | Huixquilucan | premium_suburbano | A/B | Poniente | Residencial cerrado premium fuera CDMX | Contraste Polanco/Santa Fe: área de élite suburbana, mayor poder adquisitivo, distancia a delivery |
| 12 | Cuajimalpa | premium_bosque | A/B | Poniente Alto | Residencial ultra-premium, geografía montañosa | Extremo poniente: NSE más alto, zona boscosa, logística delivery desafiante |
| 13 | Gustavo A. Madero | popular_noreste | D | Noreste | Zona obrera norte, alta densidad | Llenar vacío noreste: GAM es 2da delegación más poblada, demanda masiva, bajo NSE |
| 14 | Azcapotzalco | industrial | C/D | Noroeste | Industrial/comercial, trabajadores | Cobertura noroeste: zona de fábricas y obreros, horarios de comida pico en mediodía |
| 15 | Álvaro Obregón | residencial_poniente | B/C+ | Poniente | Residencial consolidado poniente | Poniente medio: entre Polanco y zonas populares, residencial tradicional CDMX |
| 16 | Tlalpan | sur_residencial | B/C+ | Sur Profundo | Delegación sur, residencial tradicional | Sur profundo: residencial no corporativo, viejo sur de CDMX, menor densidad delivery |
| 17 | Xochimilco | sur_tradicional | C | Sur Profundo | Delegacional, turístico, tradicional | Sur cultural/turístico: baja penetración delivery, SKU locales, horarios atípicos |
| 18 | Naucalpan | edomex_corporativo | B/C | Centro-Oriente EdoMex | Polo corporativo EdoMex, tránsito laboral | EdoMex corporativo: paralelo a Santa Fe pero en Estado, traffic laboral diferente |
| 19 | Atizapán | edomex_poniente | C/D | Poniente EdoMex | Suburbano EdoMex poniente, clase media | Poniente EdoMex: zona de dormitorio, conexión con CDMX, cobertura WSW |
| 20 | Toluca | edomex_capital | C/D | Sur EdoMex (Capital estatal) | Capital estatal, mercado independiente | Capital EdoMex: mercado separado, logística interestatal, prueba de escalabilidad |

**Criterios de selección para las 20 direcciones:**

1. **Cobertura NSE:** 
   - A/B: Polanco, Santa Fe, Huixquilucan, Cuajimalpa (4 premium)
   - B/C+: Roma, Del Valle, Coyoacán, Insurgentes Sur, Álvaro Obregón, Tlalpan (6 medio-alto)
   - C/C+: Centro Histórico, Xochimilco, Naucalpan (3 medio)
   - C/D: Cuautitlán, Azcapotzalco, Atizapán, Toluca (4 medio-bajo)
   - D: Iztapalapa, Ecatepec, GAM (3 bajo)

2. **Cobertura cardinal completa:**
   - **Norte:** Cuautitlán Izcalli, Ecatepec, GAM, Naucalpan, Atizapán
   - **Sur:** Coyoacán, Insurgentes Sur, Tlalpan, Xochimilco
   - **Poniente:** Polanco, Santa Fe, Huixquilucan, Cuajimalpa, Álvaro Obregón, Atizapán
   - **Oriente:** Iztapalapa, Ecatepec, GAM
   - **Centro:** Roma, Del Valle, Centro Histórico, Naucalpan

3. **Casos analíticos únicos:**
   - **Geografía desafiante:** Cuajimalpa (montaña), Xochimilco (zona lacustre)
   - **Logística extrema:** Toluca (fuera CDMX, 60+ km), Huixquilucan (suburbano premium lejano)
   - **Alto volumen:** Ecatepec (5.2M habitantes), GAM (4M hab), Iztapalapa (1.8M hab)
   - **Horarios pico:** Santa Fe (12–14h laboral), Azcapotzalco (13h obrero), Xochimilco (turismo variable)
   - **Perfiles especiales:** Centro Histórico (turismo + peatonal), Naucalpan (tránsito laboral EdoMex)

---

## Datos & catálogos

**Editables sin cambiar código:**

- `data/addresses.csv` — direcciones test (campos: `address_id, label, street, lat, lng, zone_type`)
- `data/products.csv` — SKUs a buscar (campos: `sku, canonical_name, vertical, search_keywords, price_min_mxn, price_max_mxn, exclude_keywords`)
- `data/brands.csv` — tiendas por plataforma (campos: `brand_id, platform, vertical, nav_strategy, nav_param`)

**Output:**
- `scrapes.csv` — long format: `scrape_id, timestamp_utc, platform, brand_id, address_id, store_id, store_name, product_sku, product_name_raw, unit_price_mxn, delivery_fee_mxn, service_fee_mxn, discount_mxn, total_final_mxn, eta_min, eta_min_low, eta_min_high, available, promo_text, collection_method, notes`
- `scrapes.json` — mismo contenido, formato nested

---

## Limitaciones & detalles

Las limitaciones se informan en base a las primeras 6 direcciones probadas, más tarde se extendió la cobertura con cuatro direcciones extra.

| Limitación | Impacto |
|---|---|
| **DiDi Food** no tiene web pública | Es 100% app-only; filas emitidas con `available=False` |
| **Service fee** = 0 | Ni Rappi ni UE exponen fee fuera de checkout logueado |
| **McDonald's depende horario** | Desayuno (~7–11 AM CST): solo menú de desayuno en 5/6 direcciones |
| **OXXO no vende pañales** | SKU removido tras 0/6 matches; es conveniencia, no supermercado |
| **Uber Eats puede bloquear** | Algunas direcciones sin resultados; mitigado con rate-limit 1.5s |

**Scope deliberado:** 10 direcciones bien scrapeadas > 50 a medias.

---

## Ética & robots.txt

- Respetar `robots.txt` de Rappi y Uber Eats
- Solo JSON-LD público (SEO) + DOM visible
- **NO** consumir `/api*` (prohibido por Rappi robots)
- Rate-limit: 1.5s entre direcciones
- Sin login, sin proxies pagos

Detalles: [`docs/compliance.md`](docs/compliance.md)

---

## Estructura

```
.
├── scraper/              # código
│   ├── base.py          # ABC PlatformScraper
│   ├── rappi.py         # Rappi
│   ├── ubereats.py      # Uber Eats
│   ├── didi.py          # DiDi (stub)
│   ├── matching.py      # keyword + price range
│   ├── catalog.py       # load addresses/products/brands
│   ├── models.py        # dataclasses
│   ├── robots.py        # robots.txt check
│   └── run.py           # CLI
├── data/                # catálogos + outputs
├── notebooks/           # insights.ipynb
├── scripts/             # utilitarios
└── docs/                # specs, compliance, blockers
```

---

## Troubleshooting

- **Logs vacíos?** Verificar permisos en `data/`, asegurar Chromium instalado (`python -m playwright install chromium`)
- **0 items encontrados?** Revisar `data/products.csv` keywords; puede variar por zona/horario
- **UE sin resultados en dirección X?** Documentado en `docs/blockers.md`; es limitación de UE, no del scraper

---

## Referencias

- Spec MVP: [`docs/specs/2026-05-11-mvp-4h-design.md`](docs/specs/2026-05-11-mvp-4h-design.md)
- Spec retail: [`docs/specs/2026-05-12-retail-walmart-design.md`](docs/specs/2026-05-12-retail-walmart-design.md)
- Bitácora: [`docs/blockers.md`](docs/blockers.md)
