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

## Pendientes para tramos 4-5

- Uber Eats no comenzado.
- Notebook de insights no generado.
- Para `cocacola_500ml` y `agua_1l`: evaluar si scrapeamos Rappi Turbo/Express como segundo store o si los excluimos del análisis de fast food puro.