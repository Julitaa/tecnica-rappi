# Blockers · bitácora

Formato: una entrada de 2 líneas por blocker. Fecha + qué falló + decisión.

## 2026-05-11 · Tramo 2 (Rappi)

- **Sin cuenta Rappi MX desde AR.** Intento de registro bloqueado por geo. Decisión: scraper anónimo (sin login).
- **Geolocation override por `cloudfront-location`.** Rappi detecta IP AR y devuelve coords default CDMX que no respetan la geolocation del contexto Playwright. Decisión: cliquear el botón "Usa tu ubicación actual" del modal `address_capture`, que sí usa la geolocation API del browser y respeta nuestra coord.
- **Menú no visible sin address seteada.** La URL directa de tienda `/restaurantes/delivery/706-mcdonald-s` muestra una landing SEO con modal de captura de dirección. Decisión: automatizar el modal vía Playwright + click "Usa tu ubicación actual"; Rappi redirige a la tienda real más cercana y dispara `GET /api/web-gateway/web/restaurants-bus/store/id/<id>/` con todos los datos.
- **`service_fee` no expuesto en endpoint de menú.** El JSON de tienda incluye `percentage_service_fee` (0.0 para McDonald's en todas las direcciones probadas). El valor accionable sólo aparece en el flujo de checkout. Decisión: imputar `unit_price * percentage_service_fee / 100`. Hoy queda 0 para McDonald's; aceptable para el MVP.
- **`discount_mxn` numérico no accionable sin checkout.** Las promos visibles (`discount_tags`) son free_shipping o "hasta X% off" condicionales. Decisión: si hay `free_shipping` activo, imputar `discount = -delivery_fee` (queda neto). El texto raw se preserva en `promo_text` para auditoría.
- **SKUs retail (`cocacola_500ml`, `agua_1l`) no presentes en McDonald's.** Esperado por diseño: estos SKUs apuntan a verticales de conveniencia (Rappi Turbo, OXXO). Quedan con `available=False, notes="no_match_in_menu"` en Rappi. Para tener data real en estos SKUs habría que cambiar la tienda objetivo en tramos 3-4.

## Pendientes para tramos 3-5

- DiDi Food y Uber Eats no comenzados.
- Notebook de insights no generado.
- Para `cocacola_500ml` y `agua_1l`: evaluar si scrapeamos Rappi Turbo/Express como segundo store o si los excluimos del análisis de fast food puro.