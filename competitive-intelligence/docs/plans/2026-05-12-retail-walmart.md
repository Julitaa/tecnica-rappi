# Retail Walmart Súper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extender los scrapers de Rappi y Uber Eats para capturar 3 SKUs retail (coca, agua, pañales) desde Walmart Súper, reusando geolocation + JSON-LD existentes; cerrar con gap-analysis del brief y README.

**Architecture:** Introducir un catálogo `brands.csv` que define (platform × brand × vertical × nav_strategy). Los scrapers existentes se parametrizan por `Brand` en el constructor. El orquestador itera `(brand, address)` y filtra `products` por `brand.vertical`. McDonald's queda como `brand_id="mcdonalds"` sin cambios funcionales.

**Tech Stack:** Python 3.11, Playwright async, pandas (notebook). Sin nuevas deps.

**Eficiencia de tokens:** el repo no tiene suite de tests; en lugar de TDD formal usamos smoke-tests con corridas reales del CLI por marca, validando con `pandas` que las filas tengan precios. Cada task tiene un commit. Total estimado: ~7 tasks chicas.

---

## File Structure

| Archivo | Acción | Responsabilidad |
|---|---|---|
| [competitive-intelligence/data/brands.csv](competitive-intelligence/data/brands.csv) | Crear | Catálogo (platform × brand × vertical × nav) |
| [competitive-intelligence/data/products.csv](competitive-intelligence/data/products.csv) | Modificar | Agregar fila `panales_t4` |
| [competitive-intelligence/scraper/models.py](competitive-intelligence/scraper/models.py) | Modificar | `Brand` dataclass + `brand_id` en `ScrapeRow` + `ProductSku` literal extendido |
| [competitive-intelligence/scraper/catalog.py](competitive-intelligence/scraper/catalog.py) | Modificar | `load_brands()` |
| [competitive-intelligence/scraper/rappi.py](competitive-intelligence/scraper/rappi.py) | Modificar | Constructor `(brand: Brand)`, URL desde brand, `brand_id` en filas |
| [competitive-intelligence/scraper/ubereats.py](competitive-intelligence/scraper/ubereats.py) | Modificar | Constructor `(brand: Brand)`, query desde brand, regex de anchors parametrizado |
| [competitive-intelligence/scraper/didi.py](competitive-intelligence/scraper/didi.py) | Modificar | Aceptar `brand` para uniformidad (no cambia el stub) |
| [competitive-intelligence/scraper/run.py](competitive-intelligence/scraper/run.py) | Modificar | Itera `(brand, address)`, filtra por vertical, agrega columna `brand_id` |
| [competitive-intelligence/docs/blockers.md](competitive-intelligence/docs/blockers.md) | Modificar | Agregar entrada tramo 6 con hallazgos Walmart |
| [README.md](README.md) | Crear | Setup + cómo correr + cómo ver el informe |

---

## Task 1: Modelo `Brand` + `brand_id` en `ScrapeRow` + nuevo SKU literal

**Files:**
- Modify: `competitive-intelligence/scraper/models.py`

- [ ] **Step 1: Extender modelos**

Reemplazar el contenido del módulo dejando intactos los imports superiores y los dataclasses existentes; agregar `panales_t4` al literal, agregar dataclass `Brand`, y agregar `brand_id` opcional a `ScrapeRow`:

```python
ProductSku = Literal[
    "big_mac",
    "mcombo_bigmac_med",
    "mcnuggets_10",
    "cocacola_500ml",
    "agua_1l",
    "panales_t4",
]

NavStrategy = Literal["brand_url", "search_query"]


@dataclass(frozen=True)
class Brand:
    brand_id: str
    platform: Platform
    vertical: str
    nav_strategy: NavStrategy
    nav_param: str
```

Y en `ScrapeRow`, agregar (al final de los campos opcionales, antes de `scrape_id`):

```python
    brand_id: Optional[str] = None
```

- [ ] **Step 2: Verificar import**

Run: `cd competitive-intelligence && python -c "from scraper.models import Brand, ScrapeRow; print(Brand.__dataclass_fields__.keys(), ScrapeRow.__dataclass_fields__['brand_id'])"`
Expected: imprime los campos de `Brand` y muestra `brand_id` con default None.

- [ ] **Step 3: Commit**

```bash
cd competitive-intelligence
git add scraper/models.py
git commit -m "feat(models): Brand dataclass + brand_id field + panales_t4 sku"
```

---

## Task 2: `data/brands.csv` y `load_brands()`

**Files:**
- Create: `competitive-intelligence/data/brands.csv`
- Modify: `competitive-intelligence/scraper/catalog.py`

- [ ] **Step 1: Crear `brands.csv`**

Contenido exacto (la URL de Walmart en Rappi MX se confirma en runtime; se usa la del directorio público del partner):

```
brand_id,platform,vertical,nav_strategy,nav_param
mcdonalds,rappi,fast_food,brand_url,https://www.rappi.com.mx/restaurantes/delivery/706-mcdonald-s
mcdonalds,ubereats,fast_food,search_query,mcdonalds
walmart_super,rappi,retail,brand_url,https://www.rappi.com.mx/tiendas/900116707-walmart-super
walmart_super,ubereats,retail,search_query,walmart
```

Nota: el `nav_param` de Rappi/Walmart se ajustará en Task 6 si el path correcto difiere — el formato `/tiendas/<id>-<slug>` es el patrón observado en Rappi MX.

- [ ] **Step 2: Agregar `load_brands` a `catalog.py`**

Agregar al final del archivo:

```python
from .models import Brand


def load_brands(path: Path | None = None) -> list[Brand]:
    path = path or (DATA_DIR / "brands.csv")
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            Brand(
                brand_id=row["brand_id"],
                platform=row["platform"],  # type: ignore[arg-type]
                vertical=row["vertical"],
                nav_strategy=row["nav_strategy"],  # type: ignore[arg-type]
                nav_param=row["nav_param"],
            )
            for row in reader
        ]
```

(Mover `from .models import` al bloque superior si ya existe, evitando duplicar.)

- [ ] **Step 3: Verificar**

Run: `cd competitive-intelligence && python -c "from scraper.catalog import load_brands; bs = load_brands(); print(len(bs), [b.brand_id+':'+b.platform for b in bs])"`
Expected: `4 ['mcdonalds:rappi', 'mcdonalds:ubereats', 'walmart_super:rappi', 'walmart_super:ubereats']`

- [ ] **Step 4: Commit**

```bash
cd competitive-intelligence
git add data/brands.csv scraper/catalog.py
git commit -m "feat(catalog): brands.csv y load_brands"
```

---

## Task 3: Agregar `panales_t4` a `products.csv`

**Files:**
- Modify: `competitive-intelligence/data/products.csv`

- [ ] **Step 1: Agregar fila**

Append al final del archivo (preservando newline final):

```
panales_t4,Pañales talla 4 (24-40u),retail,"huggies|pampers|kleenbebe",200,600,"talla 1|talla 2|talla 3|talla 5|talla 6|recien nacido|recién nacido|premium care|toallitas|húmedas|humedas|wipes"
```

- [ ] **Step 2: Verificar**

Run: `cd competitive-intelligence && python -c "from scraper.catalog import load_products; ps = load_products(); print([p.sku for p in ps])"`
Expected: `['big_mac', 'mcombo_bigmac_med', 'mcnuggets_10', 'cocacola_500ml', 'agua_1l', 'panales_t4']`

- [ ] **Step 3: Commit**

```bash
cd competitive-intelligence
git add data/products.csv
git commit -m "feat(catalog): panales_t4 SKU"
```

---

## Task 4: Parametrizar `RappiScraper` por `Brand`

**Files:**
- Modify: `competitive-intelligence/scraper/rappi.py`

- [ ] **Step 1: Cambiar constructor y eliminar URL hardcodeada como default**

En [scraper/rappi.py](competitive-intelligence/scraper/rappi.py):

- Mantener la constante `BRAND_MCDONALDS_URL` (sirve de referencia/fallback), pero cambiar el constructor y `nav_url`:

```python
class RappiScraper(PlatformScraper):
    name = "rappi"

    def __init__(self, brand=None, headless: bool = True):
        from .models import Brand
        if brand is None:
            brand = Brand(
                brand_id="mcdonalds",
                platform="rappi",
                vertical="fast_food",
                nav_strategy="brand_url",
                nav_param=BRAND_MCDONALDS_URL,
            )
        self.brand = brand
        self.nav_url = brand.nav_param
        self.headless = headless
```

- En `_capture_storefront`, reemplazar `BRAND_MCDONALDS_URL` por `self.brand.nav_param`:

```python
        try:
            await page.goto(self.brand.nav_param, timeout=PAGE_TIMEOUT_MS)
        except PWTimeout:
            return None, "rappi:brand_page_timeout"
```

- En `_empty_row` y `_rows_from_storefront`, agregar `brand_id=<brand.brand_id>` a cada `ScrapeRow`. Como ambas funciones son módulo-level, pasar el `brand_id` por parámetro:

```python
def _empty_row(address: Address, product: Product, notes: str, brand_id: str) -> ScrapeRow:
    return ScrapeRow(
        platform="rappi",
        address_id=address.address_id,
        address_label=address.label,
        product_sku=product.sku,
        collection_method="playwright",
        available=False,
        notes=notes,
        brand_id=brand_id,
    )
```

```python
def _rows_from_storefront(
    storefront: dict,
    address: Address,
    products: Sequence[Product],
    brand_id: str,
) -> list[ScrapeRow]:
    ...
    # En cada ScrapeRow(...) agregar brand_id=brand_id como último kwarg.
```

- En `scrape()` actualizar las dos llamadas:

```python
        if storefront is None:
            return [
                _empty_row(address, product, notes=notes or "rappi:no_store", brand_id=self.brand.brand_id)
                for product in products
            ]

        return _rows_from_storefront(storefront, address, products, self.brand.brand_id)
```

- [ ] **Step 2: Smoke test mínimo (sin scraping real)**

Run:
```
cd competitive-intelligence && python -c "
from scraper.rappi import RappiScraper
from scraper.models import Brand
b = Brand('walmart_super', 'rappi', 'retail', 'brand_url', 'https://www.rappi.com.mx/tiendas/900116707-walmart-super')
s = RappiScraper(brand=b)
print(s.nav_url, s.brand.brand_id)
"
```
Expected: imprime la URL de Walmart y `walmart_super`.

- [ ] **Step 3: Commit**

```bash
cd competitive-intelligence
git add scraper/rappi.py
git commit -m "refactor(rappi): parametrizar por Brand, agregar brand_id a filas"
```

---

## Task 5: Parametrizar `UberEatsScraper` por `Brand`

**Files:**
- Modify: `competitive-intelligence/scraper/ubereats.py`

- [ ] **Step 1: Cambiar constructor + regex parametrizado**

En [scraper/ubereats.py](competitive-intelligence/scraper/ubereats.py):

- Agregar import: `from .models import Brand` (en el bloque de imports existente).

- Reescribir el constructor:

```python
class UberEatsScraper(PlatformScraper):
    name = "ubereats"
    nav_url = "https://www.ubereats.com/mx"

    def __init__(self, brand: Brand | None = None, headless: bool = True):
        if brand is None:
            brand = Brand(
                brand_id="mcdonalds",
                platform="ubereats",
                vertical="fast_food",
                nav_strategy="search_query",
                nav_param="mcdonalds",
            )
        self.brand = brand
        self.headless = headless
        # Para filtrar anchors del search: /store/{slug-prefix}*
        # mcdonalds → 'mcdonalds'; walmart → 'walmart'
        self._anchor_prefix = brand.nav_param.lower()
```

- En `_capture`, reemplazar la URL hardcodeada:

```python
        search_url = SEARCH_URL_TEMPLATE.format(pl=quote(pl, safe="")).replace(
            "q=mcdonalds", f"q={quote(self.brand.nav_param, safe='')}"
        )
```

Y los dos `evaluate()` JS que filtran `/store/mcdonalds` — cambiarlos para usar el prefijo dinámico. Como `page.evaluate` no acepta variables Python directamente sin interpolar, construir el JS con f-string:

Primer `wait_for_function`:
```python
        prefix = self._anchor_prefix
        await page.wait_for_function(
            f"""() => {{
                const anchors = [...document.querySelectorAll('a[href*=\"/store/{prefix}\"]')];
                for (const a of anchors) {{
                    if (/\\/store\\/{prefix}-dummy/i.test(a.href)) continue;
                    let node = a.parentElement;
                    for (let i = 0; i < 15 && node; i++) {{
                        const t = node.innerText || '';
                        if (/\\d+\\s*min/.test(t)) return true;
                        node = node.parentElement;
                    }}
                }}
                return false;
            }}""",
            timeout=SEARCH_TIMEOUT_MS,
        )
```

Nota: se quita `&& /McDonald/i.test(t)` (era específico de la marca); el filtro por `/store/{prefix}` ya es suficiente.

Segundo `evaluate` (extracción de primer anchor):
```python
        first = await page.evaluate(
            f"""() => {{
                const anchors = [...document.querySelectorAll('a[href*=\"/store/{prefix}\"]')];
                const seen = new Set();
                for (const a of anchors) {{
                    if (/\\/store\\/{prefix}-dummy/i.test(a.href)) continue;
                    const base = a.href.split('?')[0];
                    if (seen.has(base)) continue;
                    seen.add(base);
                    let node = a.parentElement;
                    let eta = null;
                    for (let i = 0; i < 15 && node; i++) {{
                        const t = node.innerText || '';
                        const m = t.match(/(\\d+)\\s*min/);
                        if (m) {{ eta = parseInt(m[1], 10); break; }}
                        node = node.parentElement;
                    }}
                    const name = (a.innerText || '').split('\\n')[0].trim();
                    return {{storeUrl: base, eta, name}};
                }}
                return null;
            }}"""
        )
```

También cambiar el regex JSON-LD `@type === 'Restaurant'` a aceptar `'Restaurant'` o `'Store'` (Walmart probablemente expone `Store`/`GroceryStore`):

```python
            for (const s of ss) {{
                try {{
                    const j = JSON.parse(s.textContent);
                    const t = j && j['@type'];
                    if (t && /Restaurant|Store|GroceryStore/.test(t) && j.hasMenu) return true;
                }} catch (e) {{}}
            }}
```

Y la extracción de JSON-LD (`restaurant`) — renombrar para que acepte cualquiera:

```python
                for (const s of ss) {
                    try {
                        const j = JSON.parse(s.textContent);
                        const t = j && j['@type'];
                        if (t && /Restaurant|Store|GroceryStore/.test(t)) { restaurant = j; break; }
                    } catch (e) {}
                }
```

- En `_empty_row` y `_rows_from_capture`, agregar parámetro `brand_id` y propagar a cada `ScrapeRow` (mismo patrón que Task 4).

- En `scrape()`:

```python
        if captured is None:
            return [
                _empty_row(address, product, notes=notes or "ubereats:no_store", brand_id=self.brand.brand_id)
                for product in products
            ]
        return _rows_from_capture(captured, address, products, self.brand.brand_id)
```

- [ ] **Step 2: Smoke test (sin scraping)**

Run:
```
cd competitive-intelligence && python -c "
from scraper.ubereats import UberEatsScraper
from scraper.models import Brand
b = Brand('walmart_super', 'ubereats', 'retail', 'search_query', 'walmart')
s = UberEatsScraper(brand=b)
print(s.brand.brand_id, s._anchor_prefix)
"
```
Expected: `walmart_super walmart`

- [ ] **Step 3: Commit**

```bash
cd competitive-intelligence
git add scraper/ubereats.py
git commit -m "refactor(ubereats): parametrizar por Brand, soportar Store/GroceryStore JSON-LD"
```

---

## Task 6: Orquestación en `run.py` y stub DiDi

**Files:**
- Modify: `competitive-intelligence/scraper/didi.py`
- Modify: `competitive-intelligence/scraper/run.py`

- [ ] **Step 1: DiDi acepta `brand` (sin cambio de comportamiento)**

En [scraper/didi.py](competitive-intelligence/scraper/didi.py) modificar el constructor para aceptar `brand` y propagar `brand_id` en las filas que emite. Si DiDi hoy emite filas con `available=False, notes="didi_mx_no_public_web_surface_app_only"`, agregar `brand_id=self.brand.brand_id` a cada `ScrapeRow`.

(Si DiDi solo aplica al vertical `fast_food`, en `run.py` se filtra para no instanciarlo con brand=walmart.)

- [ ] **Step 2: Actualizar `run.py` para iterar `(brand, address)`**

Reemplazar el cuerpo principal de `run.py`. Cambios clave:

a) Agregar `"brand_id"` al final de `CSV_COLUMNS`:

```python
CSV_COLUMNS = [
    "scrape_id",
    "timestamp_utc",
    "platform",
    "address_id",
    "address_label",
    "store_id",
    "store_name",
    "product_sku",
    "product_name_raw",
    "unit_price_mxn",
    "delivery_fee_mxn",
    "service_fee_mxn",
    "discount_mxn",
    "total_final_mxn",
    "eta_min",
    "eta_min_low",
    "eta_min_high",
    "available",
    "promo_text",
    "collection_method",
    "notes",
    "brand_id",
]
```

b) Reescribir selección de scrapers para que tome `brand`:

```python
from .catalog import DATA_DIR, load_addresses, load_brands, load_products
from .models import Address, Brand, Product, ScrapeRow

def _build_scrapers(platform: str, brand_filter: str | None) -> list[PlatformScraper]:
    brands = load_brands()
    if platform != "all":
        brands = [b for b in brands if b.platform == platform]
    if brand_filter:
        brands = [b for b in brands if b.brand_id == brand_filter]
    out: list[PlatformScraper] = []
    for b in brands:
        cls = SCRAPERS.get(b.platform)
        if cls is None:
            continue
        out.append(cls(brand=b))
    return out
```

c) Filtrar productos por vertical en `_run_one`:

```python
async def _run_one(
    scraper: PlatformScraper,
    addresses: list[Address],
    products: list[Product],
) -> list[ScrapeRow]:
    robots = scraper.check_robots()
    fetched = "ok" if robots.fetched else "ausente/404"
    if not robots.allowed:
        print(f"SKIP {scraper.name}/{scraper.brand.brand_id}: robots.txt ({fetched}) prohibe {robots.url}.")
        return []
    print(f"OK robots {scraper.name}/{scraper.brand.brand_id}: {robots.url} permitido ({fetched}).")

    vertical = scraper.brand.vertical
    products_for_brand = [p for p in products if p.vertical == vertical]
    rows: list[ScrapeRow] = []
    for address in addresses:
        rows.extend(await scraper.scrape(address, products_for_brand))
        await asyncio.sleep(1.5)
    return rows
```

d) Agregar flag CLI `--brand`:

```python
    parser.add_argument(
        "--brand",
        default=None,
        help="Filtrar a un brand_id (ej. mcdonalds, walmart_super)",
    )
```

Y en `_run`:

```python
async def _run(platform: str, brand_filter: str | None) -> list[ScrapeRow]:
    addresses = load_addresses()
    products = load_products()
    scrapers = _build_scrapers(platform, brand_filter)
    results = await asyncio.gather(
        *(_run_one(s, addresses, products) for s in scrapers)
    )
    return [row for batch in results for row in batch]
```

Llamada en `main`: `rows = asyncio.run(_run(args.platform, args.brand))`.

- [ ] **Step 3: Smoke test orquestación (lista las combinaciones que correría)**

Run:
```
cd competitive-intelligence && python -c "
from scraper.run import _build_scrapers
for s in _build_scrapers('all', None):
    print(s.name, s.brand.brand_id, s.brand.vertical)
"
```
Expected: 4 líneas (rappi/mcdonalds/fast_food, rappi/walmart_super/retail, ubereats/mcdonalds/fast_food, ubereats/walmart_super/retail) — más DiDi si aplica.

Si DiDi falla porque su `_build_scrapers` lo intenta instanciar con brand walmart, ajustar `SCRAPERS` o filtrar DiDi a fast_food en `_build_scrapers`.

- [ ] **Step 4: Commit**

```bash
cd competitive-intelligence
git add scraper/run.py scraper/didi.py
git commit -m "feat(run): orquestar por (brand, address) con filtro de vertical y --brand CLI"
```

---

## Task 7: Correr scraper Walmart y validar

**Files:**
- Modify (eventual): `competitive-intelligence/data/brands.csv` (si la URL Rappi de Walmart falla)
- Modify (eventual): `competitive-intelligence/scraper/rappi.py` (si el flujo Walmart difiere)
- Modify: `competitive-intelligence/data/scrapes.csv`, `scrapes.json` (regenerados)
- Modify: `competitive-intelligence/docs/blockers.md` (entrada Tramo 6)

- [ ] **Step 1: Correr Uber Eats / Walmart primero (menos riesgo)**

Run:
```
cd competitive-intelligence && python -m scraper.run --platform ubereats --brand walmart_super --out-dir /tmp/walmart-ue
```
Expected: ~18 filas (6 dirs × 3 SKUs retail). Verificar con:
```
python -c "
import json
rows = json.load(open('/tmp/walmart-ue/scrapes.json'))
print('total:', len(rows))
available = [r for r in rows if r['available']]
print('available:', len(available))
for r in available[:3]:
    print(r['product_sku'], r['product_name_raw'], r['unit_price_mxn'])
"
```
Expected: al menos algunas filas `available=True` con precios > 0.

- [ ] **Step 2: Correr Rappi / Walmart**

Run:
```
cd competitive-intelligence && python -m scraper.run --platform rappi --brand walmart_super --out-dir /tmp/walmart-rp
```

Si falla con `rappi:brand_page_timeout` o `rappi:storefront_timeout`: investigar la URL real de Walmart Súper en Rappi MX. Métodos en orden:

1. Abrir https://www.rappi.com.mx en headed (`headless=False`) para Walmart, copiar URL final.
2. Actualizar `brands.csv` con la URL correcta y reintentar.
3. Si el modal `address_capture` no aparece igual: documentar en blockers.md y bajar expectativa a 3-4 direcciones.

- [ ] **Step 3: Corrida completa (todas las marcas)**

Run:
```
cd competitive-intelligence && python -m scraper.run --platform all
```
Verificar el output:
```
python -c "
import pandas as pd
df = pd.read_csv('data/scrapes.csv')
print(df.groupby(['platform','brand_id','product_sku'])['available'].agg(['sum','count']))
"
```
Expected: matriz con filas por (platform, brand_id, product_sku); al menos algún `available > 0` en cada combinación esperada (rappi×mcdonalds×big_mac, ubereats×walmart_super×cocacola_500ml, etc.).

- [ ] **Step 4: Documentar hallazgos en blockers.md**

Append en [docs/blockers.md](competitive-intelligence/docs/blockers.md):

```markdown
## 2026-05-12 · Tramo 6 (Retail Walmart Súper)

- **Resultado:** <N>/<M> filas reales para Walmart Súper en (rappi, ubereats).
- **Pañales (`panales_t4`):** matches encontrados con marcas <Huggies/Pampers/...>; rango efectivo <X-Y> MXN. Las exclusiones por talla 1/2/3/5/6 funcionaron.
- **<Hallazgo específico Rappi-Walmart>** — ej.: la URL `tiendas/<id>-walmart-super` <funcionó | requirió redirect a `/super`>; modal address_capture <apareció igual | diferente>.
- **<Hallazgo específico UE-Walmart>** — ej.: el JSON-LD usa `@type=GroceryStore` (no Restaurant); regex actualizado.
```

Reemplazar `<…>` con números/strings reales observados durante la corrida.

- [ ] **Step 5: Commit**

```bash
cd competitive-intelligence
git add data/scrapes.csv data/scrapes.json docs/blockers.md data/brands.csv scraper/rappi.py
git commit -m "feat(retail): corrida Walmart Super en Rappi + Uber Eats"
```

---

## Task 8: Gap analysis del brief + README + notebook regen

**Files:**
- Modify: `competitive-intelligence/notebooks/insights.ipynb` (regenerar si lee la nueva data)
- Create: `README.md` (en raíz del repo)

- [ ] **Step 1: Gap analysis vs PDF del brief**

Leer mentalmente la rúbrica del brief y marcar en la sección "Pendientes" del README cualquier item no cubierto. Items del brief y su estado esperado:

| Requisito brief | Estado |
|---|---|
| ≥2 competidores + Rappi | ✅ Rappi + Uber Eats; DiDi documentado como blocker |
| ≥3 métricas | ✅ unit_price, delivery_fee, service_fee (imputado), discount, eta, promo, total |
| 20-50 direcciones | ⚠️ 6 direcciones (decisión consciente; documentar) |
| Productos fast food (3) | ✅ big_mac, mcombo_bigmac_med, mcnuggets_10 |
| Productos retail (3) | ✅ cocacola_500ml, agua_1l, panales_t4 |
| CSV/JSON output | ✅ data/scrapes.{csv,json} |
| Comando único | ✅ `python -m scraper.run` |
| README setup + run | ⬅️ se cubre en este task |
| Top 5 insights accionables | ⚠️ revisar notebook |
| ≥3 visualizaciones | ⚠️ revisar notebook |
| robots.txt respetado | ✅ ver compliance.md |
| Capturas pantalla (bonus) | ❌ no implementado |
| Múltiples verticales (bonus) | ✅ fast_food + retail |

- [ ] **Step 2: Regenerar notebook**

Run:
```
cd competitive-intelligence && python scripts/build_notebook.py && jupyter nbconvert --to notebook --execute notebooks/insights.ipynb --inplace
```
(Si `build_notebook.py` no regenera con datos retail, abrir y ajustar manualmente: agregar segmento por `brand_id`/`vertical` en los 3 gráficos.)

Si el notebook no tiene un gráfico que muestre retail vs fast food, agregar como mínimo: tabla pivote `platform × brand_id × product_sku → mean(unit_price_mxn)`.

- [ ] **Step 3: Escribir README.md en raíz**

Crear [README.md](README.md) con esta estructura (en español, conciso):

```markdown
# Competitive Intelligence Scraper — Rappi vs Uber Eats vs DiDi

Sistema automatizado que recolecta precio unitario, delivery fee, ETA y promociones de 6 SKUs (3 fast food en McDonald's + 3 retail en Walmart Súper) en Rappi MX, Uber Eats MX y DiDi Food MX, sobre 6 direcciones representativas de CDMX/EdoMex.

## Setup

Requiere Python 3.11+.

```bash
cd competitive-intelligence
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Correr el scraper

Una corrida completa (4 combinaciones platform × brand sobre 6 direcciones):

```bash
python -m scraper.run --platform all
```

Subset (útil para iterar):

```bash
python -m scraper.run --platform ubereats --brand walmart_super
python -m scraper.run --platform rappi --brand mcdonalds
```

Salidas: `data/scrapes.csv` y `data/scrapes.json`. Cada fila lleva `platform`, `brand_id`, `address_id`, `product_sku` y métricas (`unit_price_mxn`, `delivery_fee_mxn`, `service_fee_mxn`, `discount_mxn`, `total_final_mxn`, `eta_min`, `promo_text`, `available`).

## Ver el informe

```bash
jupyter notebook notebooks/insights.ipynb
```

El notebook ejecuta top-to-bottom y produce los gráficos del informe ejecutivo. La data fuente es `data/scrapes.csv`.

## Estructura

- `scraper/` — código del scraper (un módulo por plataforma + base + matching + run CLI).
- `data/addresses.csv` — 6 direcciones objetivo.
- `data/products.csv` — 6 SKUs estandarizados con keywords y rangos de precio.
- `data/brands.csv` — catálogo (platform × brand × vertical × nav).
- `data/scrapes.{csv,json}` — output del scraper.
- `notebooks/insights.ipynb` — informe ejecutivo.
- `docs/specs/` — specs de diseño.
- `docs/plans/` — planes de implementación.
- `docs/blockers.md` — bitácora de limitaciones y decisiones.
- `docs/compliance.md` — consideraciones éticas y de robots.txt.

## Limitaciones conocidas

- **DiDi Food MX es app-only.** No tiene superficie web pública. Las filas DiDi tienen `available=False`. Ver `docs/blockers.md` para el recon completo.
- **Service fees imputados a 0.** No están expuestos fuera del checkout (logueado). Ver `docs/compliance.md`.
- **Walmart Súper en Rappi:** la URL puede variar por zona. Si el modal de geolocation falla, ver `docs/blockers.md`.
- **6 direcciones (no 20-50):** decisión consciente de scope para el time-box; foco en calidad por punto.

## Ética y robots.txt

Ver `docs/compliance.md`. Se respetan los `robots.txt` de ambas plataformas; no se consumen endpoints `/api*` de Rappi ni endpoints firmados de Uber Eats. Solo se lee JSON-LD público (datos estructurados deliberadamente publicados para SEO) y DOM visible.
```

- [ ] **Step 4: Commit**

```bash
git add README.md competitive-intelligence/notebooks/insights.ipynb
git commit -m "docs: README de setup/uso + regen notebook con retail"
```

- [ ] **Step 5: Reporte final al usuario**

Imprimir un resumen con:
- Total de filas recolectadas y desglose por (platform, brand_id).
- Items pendientes del brief (la tabla del Step 1).
- Path al README y al notebook.

---

## Self-Review

**Spec coverage:**
- §3 SKU pañales → Task 3 ✅
- §4 brands.csv → Task 2 ✅
- §5.1 modelo Brand + brand_id → Task 1 ✅
- §5.2 load_brands → Task 2 ✅
- §5.3 RappiScraper parametrizado → Task 4 ✅
- §5.4 UberEatsScraper parametrizado + JSON-LD Store/GroceryStore → Task 5 ✅
- §5.5 run.py orquesta (brand, address) + --brand CLI → Task 6 ✅
- §5.6 products.csv + panales_t4 → Task 3 ✅
- §6 CSV con brand_id → Task 6 ✅
- §7 riesgos (URL Rappi, GroceryStore, múltiples Walmart) → Tasks 5, 7 ✅
- §8 pendientes brief → Task 8 ✅
- §9 done: scraper corre, csv con brand_id, blockers actualizado, README → Tasks 6, 7, 8 ✅

**Placeholder scan:** ningún TBD/TODO; todos los snippets de código completos.

**Type consistency:** `Brand` con los mismos 5 campos en models.py (Task 1), brands.csv (Task 2) y load_brands (Task 2). `brand_id` en ScrapeRow (Task 1) propagado en Rappi (Task 4), UberEats (Task 5), DiDi (Task 6). `--brand` CLI flag en Task 6 referenciado en Task 7. README referencia paths reales.

---

Plan complete and saved to `competitive-intelligence/docs/plans/2026-05-12-retail-walmart.md`.
