# Blockers · bitácora

Formato: una entrada de 2 líneas por blocker. Fecha + qué falló + decisión.

## 2026-05-11 · Tramo 2 (Rappi)

- **Sin cuenta Rappi MX desde AR.** Intento de registro bloqueado por geo. Decisión: scraper anónimo (sin login).
- **Geolocation override por `cloudfront-location`.** Rappi detecta IP AR y devuelve coords default CDMX que no respetan la geolocation del contexto Playwright. Decisión: cliquear el botón "Usa tu ubicación actual" del modal `address_capture`, que sí usa la geolocation API del browser y respeta nuestra coord.
- **Menú no visible sin address seteada.** La URL directa de tienda `/restaurantes/delivery/706-mcdonald-s` muestra una landing SEO con modal de captura de dirección. Decisión: automatizar el modal vía Playwright + click "Usa tu ubicación actual"; Rappi redirige a la tienda real más cercana y dispara `GET /api/web-gateway/web/restaurants-bus/store/id/<id>/` con todos los datos.
- **`service_fee` no expuesto en endpoint de menú.** El JSON de tienda incluye `percentage_service_fee` (0.0 para McDonald's en todas las direcciones probadas). El valor accionable sólo aparece en el flujo de checkout. Decisión: imputar `unit_price * percentage_service_fee / 100`. Hoy queda 0 para McDonald's; aceptable para el MVP.
- **`discount_mxn` numérico no accionable sin checkout.** Las promos visibles (`discount_tags`) son free_shipping o "hasta X% off" condicionales. Decisión: si hay `free_shipping` activo, imputar `discount = -delivery_fee` (queda neto). El texto raw se preserva en `promo_text` para auditoría.
- **SKUs retail (`cocacola_500ml`, `agua_1l`) no presentes en McDonald's.** Esperado por diseño: estos SKUs apuntan a verticales de conveniencia (Rappi Turbo, OXXO). Quedan con `available=False, notes="no_match_in_menu"` en Rappi. Para tener data real en estos SKUs habría que cambiar la tienda objetivo en tramos 3-4.

## 2026-05-11 · Tramo 3 (DiDi Food MX)

**Hallazgo crítico: DiDi Food MX no tiene superficie web de ordering. Es 100% app-only.**

Recon completo realizado con Playwright MCP + httpx antes de implementar:

- `www.didi-food.com/es-MX/food/` es exclusivamente landing de marketing (CTA "Descarga la app"). Los elementos "Buscar comida" e "Iniciar sesión" son `<div>` decorativos sin onclick ni href reales.
- `/es-MX/restaurants`, `/es-MX/store-list`, y patrones similares → 404 server-rendered ("Esta página no se puede encontrar").
- Subdominios típicos de webapps (`web.didi-food.com`, `m.didi-food.com`, `h5.didi-food.com`, `api.didi-food.com`) no resuelven en DNS (`ERR_NAME_NOT_RESOLVED`).
- `robots.txt` y `sitemap.xml` devuelven 404 — DiDi no se molesta en publicarlos porque no hay nada que crawlear.
- Probe con User-Agent iPhone Safari: response idéntico al desktop (mismo HTML, mismo length). No hay content-negotiation ni redirect a un h5 mobile.
- Network requests del browser cargando la home: cero llamadas a APIs de restaurantes/menús/búsqueda. Solo `omgup.didiglobal.com/api/web/stat` (telemetría) y `api-sec.didiglobal.com/sign/...` (firma de sesión).
- Scan de los 4 bundles JS de la home (`soda_static/c/homepage/*.js`): única API funcional referenciada es `act-api.didi-food.com/act-api` (campañas de marketing, no menús).

**Decisión:** mantener DiDi como columna en el dataset emitiendo filas con `available=False` y `notes="didi_mx_no_public_web_surface_app_only"`. Razones:

1. Preserva el shape de la matriz (3 plataformas × 6 direcciones × 5 SKUs = 90 filas), permitiendo que el notebook compare lo que hay y muestre el hueco DiDi explícitamente.
2. La única vía técnica para capturar precios DiDi sería mitmproxy de la app móvil — fuera del scope ético del brief ("respetar robots.txt cuando sea posible" se generaliza a "no hackear app pinning").
3. La ausencia misma de DiDi en web es **un insight competitivo en sí mismo**: en el mercado mexicano post-2022, DiDi Food apostó a app-only mientras Rappi y Uber Eats invirtieron en web. El notebook lo refleja en el capítulo de cobertura.

Ver [`docs/compliance.md`](compliance.md) para el detalle del límite ético y [`scraper/didi.py`](../scraper/didi.py) para la implementación del stub documentado.

## 2026-05-11 · Tramo 4 (Uber Eats MX)

**Resultado: 17/30 filas reales** (5 SKUs × 6 direcciones; 13 misses son los SKUs retail `cocacola_500ml`/`agua_1l` que McDonald's no vende + 1 mcnuggets no listado en Santa Fe).

- **Address state vía `pl` base64.** Uber Eats no usa modal de "usa tu ubicación" como Rappi; el address vive en un query-param `?pl=<base64>` con JSON `{address, latitude, longitude}`. Hallazgo clave: si pasamos solo `lat/lng` (sin `reference` de Google Places), el server **resuelve la `reference` en su propio place-index** (`uber_places`) y redirige a una URL completa. Esto nos evita reverseo del typeahead/Google Places API. Decisión: construir `pl` desde `data/addresses.csv` puro.
- **Storefront page expone JSON-LD `Restaurant.hasMenu`** con shape schema.org idéntico al de Rappi (`hasMenuSection[].hasMenuItem[].offers.price`). Mismo helper de `_iter_menu_items` funciona en ambos. Esto es data estructurada deliberadamente publicada para SEO.
- **ETA no aparece en el storefront**, solo en la card del search results. Decisión: hop search→store. Navegamos a `/mx/search?q=mcdonalds&pl=...`, leemos ETA del card del primer resultado McDonald's (filtrando `mcdonalds-dummy-oaxaca`, que es un fixture interno de Uber Eats que aparece como placeholder), luego saltamos al storefront para el menú.
- **`wait_for_selector` no alcanza para el card de search.** Los anchors aparecen rápido pero el ETA (sibling) tarda ~6-8s en hidratar. Decisión: `wait_for_function` que requiere coexistencia de anchor McDonald's + texto `\d+\s*min` en el mismo subtree antes de extraer.
- **`load` event nunca dispara en headless.** Telemetría/analytics mantienen requests abiertos indefinidamente. Decisión: `wait_until="domcontentloaded"` en `page.goto`.
- **Anchors duplicados por card (imagen + nombre).** El primero tiene `innerText=""` (link de imagen, `rect.width=0`), el segundo tiene el nombre. Walk-up de hasta 15 niveles desde cualquiera encuentra el ETA en el subtree del card. Acepta el primer match único por `href`.
- **Service fee no expuesto.** Igual que Rappi: solo visible en checkout. Imputamos 0. Documentado en `compliance.md`.
- **Delivery fee visible solo como promo condicional.** El único texto de fee accesible en anónimo es `"Costo de envío: MXN0 (usuarios nuevos)"` (promo de onboarding) o variantes con Uber One. No hay tarifa base visible al usuario no logueado. Decisión: `delivery_fee_mxn=0` honestamente, y `promo_text` preserva el string raw para auditoría del evaluador.
- **Cobertura geográfica completa (6/6 direcciones).** Decisión positiva: no fue necesario degradar a 3 direcciones como el spec contemplaba para el "peor caso" — la captura anónima vía pl + JSON-LD funcionó para todas las zonas (Polanco, Roma, Del Valle, Iztapalapa, Santa Fe, Cuautitlán). Stores resueltas: Antara, Zona Rosa, Parque Hundido, Plaza Central, Santa Fe Zentrika, Cuautitlán Izcalli.

## Pendientes para tramo 5

- Notebook de insights no generado.
- Para `cocacola_500ml` y `agua_1l`: evaluar si scrapeamos Rappi Turbo/Express como segundo store o si los excluimos del análisis de fast food puro (siguen con `available=False, notes="no_match_in_menu"` en las 3 plataformas).

## 2026-05-12 · Tramo 6 (Retail OXXO)

**Pivot del spec.** El spec original (`2026-05-12-retail-walmart-design.md`) eligió Walmart Súper. Durante implementación descubrí que **Walmart no está en Uber Eats MX** (la búsqueda solo devuelve restaurantes con dirección "Walmart" como referencia). En Rappi sí existe Walmart, pero para paridad cross-plataforma pivoteamos a **OXXO** (la conveniencia más ubicua de México, ~22k tiendas).

**Implementación retail.** Rappi tiendas y UE tiendas exponen el menú con un schema **distinto** al de restaurantes:

- **Rappi tiendas**: en lugar de `<script id="seo-structured-schema">` con `hasMenu`, hay múltiples `<script type="application/ld+json">` con `@type=ItemList → itemListElement[].item (Product)` — uno por categoría visible en el storefront. Implementé `_iter_item_list_items` que aplana esos arrays.
- **UE tiendas**: NO exponen `hasMenu` en JSON-LD ni ItemList con productos. Además la CSP de las storefront pages bloquea `wait_for_function` (unsafe-eval). Solución: parseo del `innerText` del body buscando pares `$<precio>\n<nombre>` (heurística DOM, más frágil pero funciona).

**Modal address_capture en Rappi.** En brand pages de restaurantes Rappi muestra el modal "Usa tu ubicación actual"; en URLs de tienda concretas (ej. `/tiendas/<id>-oxxo-express-nc`) NO. Hice el click condicional al modal.

**Pañales (`panales_t4`): producto removido del catálogo.** OXXO Express en Rappi y en UE NO vende pañales (recorrí los ItemList y el innerText con keywords `huggies|pampers|kleenbebe` → 0 matches en las 6 direcciones). Es coherente con que OXXO es tienda de conveniencia (snacks/bebidas/alcohol), no supermercado. Decisión: remover `panales_t4` del catálogo (`data/products.csv`) y documentar el hallazgo aquí. Para incluir pañales habría que cambiar a un supermercado real (Soriana, Chedraui, La Comer), pero esos no están uniformemente presentes en CDMX + EdoMex en ambas plataformas.

**Horario del scrape sesga McDonald's.** Las corridas se hicieron a la hora de **desayuno mexicano** (~7–9 AM CST). En 5 de 6 direcciones, Rappi devolvió el menú parcial de desayuno (McMuffin, Hot Cakes, McBurrito) sin Big Mac/McNuggets/combos. Roma Norte fue la excepción (menú completo de 83 items, posiblemente cacheado). Es comportamiento real de la app, no bug del scraper. **Insight para la presentación**: el catálogo activo de un restaurante en una plataforma de delivery depende del horario; un análisis competitivo robusto requiere scrapes en múltiples ventanas horarias.

**UE: detección progresiva de bots.** Las búsquedas para `/store/mcdonalds` y `/store/oxxo` degradan a 0 anchors tras varias corridas seguidas desde la misma IP/contexto, aunque la primera corrida fresh da resultados (ej. UE OXXO: 8/18 en primer scrape, 0/12 después). Mitigaciones intentadas: wait_for_selector en lugar de wait_for_function (la CSP del storefront bloquea unsafe-eval), timeouts de 25s, User-Agent realista. **Sin proxies rotativos**, este blocker es estructural — UE detecta el patrón de Playwright headless. Para un sistema de producción habría que: (a) proxies residenciales, (b) browser stealth plugin, o (c) sesiones logueadas. Quedó fuera del scope ético y temporal del MVP.

**Corrida final fusionada (`scripts/merge_scrapes.py`):** 45/78 filas con `available=True`. Se combinó:

- **McDonald's**: snapshot del tramo 5 (commit `66573dd`, 2026-05-11 ~21:58 CST, hora local de almuerzo en MX — menú completo). Rappi 16/18, UE 17/18, DiDi 0/18.
- **OXXO**: corrida de tramo 6 (2026-05-12 ~14:00 CST). Rappi 12/12 ✅, UE 0/12 (bot detection — los 8/18 del primer probe se degradaron a 0 tras varias corridas seguidas).

La fusión es legítima: ambos snapshots están a menos de 24 h, los SKUs no se solapan (fast food vs retail) y el schema es idéntico (la columna `brand_id` se imputa `mcdonalds` en el snapshot viejo). El script `scripts/merge_scrapes.py` deja la decisión auditable y reproducible.

**Service fee** sigue siendo 0 (no expuesto pre-checkout, ver `compliance.md`).