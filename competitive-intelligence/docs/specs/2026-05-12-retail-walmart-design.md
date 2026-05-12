# Retail vertical (Walmart Súper) — extensión del scraper

**Fecha:** 2026-05-12
**Autor:** Julieta Pages
**Contexto:** El MVP actual cubre 3 SKUs fast food en McDonald's (Rappi + Uber Eats). El brief pide además 3 SKUs retail (Coca-Cola 500ml, agua 1L, pañales marca reconocida). Este spec extiende el sistema para incluir retail vía Walmart Súper sin duplicar scrapers.

---

## 1. Objetivo

Agregar cobertura retail (Coca-Cola 500ml, agua 1L, pañales talla 4 ~24–40u) en Rappi y Uber Eats, scrapeada desde Walmart Súper, reutilizando la maquinaria existente (geolocation, JSON-LD, matching). Cierra el requisito del brief de scrapear "retail/pharmacy" como vertical bonus y completa la lista de 3 SKUs retail estandarizados.

**No-objetivos:**
- Múltiples supermercados (Walmart es suficiente para el contraste).
- Retail en DiDi Food (sigue siendo app-only).
- Cambios al notebook de insights (se regenera con la data nueva, sin nueva lógica).

---

## 2. Decisión de tienda

**Walmart Súper.** Razones:

- Cobertura nacional real (no solo CDMX como OXXO Spin).
- Presente en Rappi MX (vertical "Súper") y Uber Eats MX ("Tiendas").
- Lista las 3 categorías incluyendo pañales en presentaciones grandes (24u+).
- OXXO descartado: tienda de conveniencia, raramente lista pañales x24 con stock real.

---

## 3. SKU nuevo: pañales

| sku | canonical_name | vertical | search_keywords | price_min | price_max | exclude_keywords |
|---|---|---|---|---|---|---|
| `panales_t4` | Pañales talla 4 (24–40u) | retail | `huggies|pampers|kleenbebe` | 200 | 600 | `talla 1|talla 2|talla 3|talla 5|talla 6|recién nacido|premium care|toallitas|húmedas` |

**Rationale:** marca flexible (Huggies/Pampers/KleenBebé) + talla fija (4) + rango unidades amplio (24–40) maximiza hit-rate sin perder comparabilidad. Las exclusiones evitan ruido de SKUs cercanos (otras tallas, toallitas húmedas).

Las keywords/rangos de `cocacola_500ml` y `agua_1l` se mantienen; si en Walmart aparecen multipacks que rompen el rango, se ajustan en una iteración posterior y se documenta en `blockers.md`.

---

## 4. Catálogo de marcas (nuevo archivo `data/brands.csv`)

```
brand_id,platform,vertical,nav_strategy,nav_param
mcdonalds,rappi,fast_food,brand_url,https://www.rappi.com.mx/restaurantes/delivery/706-mcdonald-s
mcdonalds,ubereats,fast_food,search_query,mcdonalds
walmart_super,rappi,retail,brand_url,<URL Walmart Súper en Rappi — confirmar en runtime>
walmart_super,ubereats,retail,search_query,walmart
```

Cada fila define **qué scraper** (`platform`), **a qué tienda** (`brand_id`), **cómo navegar** (`nav_strategy` ∈ {`brand_url`, `search_query`}) y **con qué parámetro**. El `vertical` se usa para filtrar productos compatibles (no buscar Big Mac en Walmart ni pañales en McDonald's).

---

## 5. Cambios en código

### 5.1 `scraper/models.py`
Agregar dataclass `Brand`:
```python
@dataclass(frozen=True)
class Brand:
    brand_id: str          # "mcdonalds" | "walmart_super"
    platform: str          # "rappi" | "ubereats"
    vertical: str          # "fast_food" | "retail"
    nav_strategy: str      # "brand_url" | "search_query"
    nav_param: str
```
Agregar campo `brand_id: str | None = None` a `ScrapeRow`.

### 5.2 `scraper/catalog.py`
Función `load_brands() -> list[Brand]` que parsea `data/brands.csv`.

### 5.3 `scraper/rappi.py`
- Eliminar `BRAND_MCDONALDS_URL` como constante; el constructor recibe `brand: Brand` y usa `brand.nav_param` como URL.
- Para `nav_strategy="brand_url"`: flujo idéntico al actual (modal "Usa tu ubicación" → JSON-LD).
- Cada `ScrapeRow` emitida lleva `brand_id=brand.brand_id`.

### 5.4 `scraper/ubereats.py`
- Constructor recibe `brand: Brand`. `search_query` viene de `brand.nav_param`.
- `SEARCH_URL_TEMPLATE` parametriza `q={query}` en lugar de `q=mcdonalds`.
- El filtro de anchors pasa de `/store/mcdonalds` a `/store/{brand.nav_param}` (regex parametrizable). Filtra `*-dummy-*` igual que ahora.
- Cada `ScrapeRow` lleva `brand_id=brand.brand_id`.

### 5.5 `scraper/run.py`
- Carga `addresses`, `products`, `brands`.
- Itera `(brand, address)`. Para cada `brand`, filtra `products` donde `product.vertical == brand.vertical`.
- CLI: `--platform` sigue funcionando como filtro; agregar `--brand` opcional para correr solo una marca (útil para iterar Walmart sin re-scrapear McDonald's).
- Las filas se concatenan en un solo `scrapes.csv` / `scrapes.json` con la columna `brand_id` agregada al final.

### 5.6 `data/products.csv`
Agregar la fila `panales_t4`. No cambian las demás filas. Las keywords actuales de coca/agua se conservan.

---

## 6. Schema del CSV final

Agregar `brand_id` como última columna a `CSV_COLUMNS` en `run.py`. Filas existentes re-generadas tendrán `brand_id=mcdonalds`. Filas retail tendrán `brand_id=walmart_super`.

---

## 7. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Rappi: Walmart Súper no usa el mismo modal `address_capture` | Media | Si el `wait_for_selector` falla, documentar en `blockers.md` y probar nav directo con geolocation seteada |
| Rappi: JSON-LD de retail no expone menú completo (paginación) | Media | Probar primero. Si está paginado, intentar scroll-to-load o aceptar parcial documentado |
| Uber Eats: múltiples Walmart en search (Súper, Express, Bodega) | Alta | Filtro: primer match `/store/walmart-super` o equivalente; si no, primer Walmart no-dummy |
| Pañales no aparecen en ninguna dirección | Baja | `available=False, notes="no_match_in_menu"` — comportamiento igual que SKUs faltantes hoy |
| Walmart Súper no entrega a alguna dirección de la lista | Media | Fila con `available=False, notes="brand:walmart_super:no_coverage"` |

---

## 8. Pendientes posteriores (no parte de este spec)

Se identificarán al revisar el brief contra el estado del repo. Candidatos conocidos: README, evidencia de capturas de pantalla automáticas (bonus), análisis de variabilidad geográfica explícito en el notebook. Se atacan después de que retail esté ingestado.

---

## 9. Definición de "hecho"

- [ ] `data/brands.csv` y nueva fila `panales_t4` en `products.csv` commiteados.
- [ ] `python -m scraper.run --platform all` corre las 4 combinaciones (rappi×mcdonalds, rappi×walmart, ubereats×mcdonalds, ubereats×walmart) sin crashear.
- [ ] `data/scrapes.csv` incluye columna `brand_id` y tiene filas reales de Walmart en al menos 4 de las 6 direcciones para coca y agua.
- [ ] `docs/blockers.md` documenta cualquier limitación encontrada con Walmart.
- [ ] Brief comparado contra entregables; pendientes notificados al usuario.
- [ ] README en raíz del proyecto explica setup + cómo correr el scraper + cómo ver el notebook.
