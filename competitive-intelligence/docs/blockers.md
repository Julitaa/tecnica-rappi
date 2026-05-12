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