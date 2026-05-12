# Cumplimiento ético · scraping

El brief técnico pide "respetar robots.txt cuando sea posible". Este documento
registra el cumplimiento concreto.

## Mecanismo de chequeo

[`scraper/robots.py`](../scraper/robots.py) descarga el `robots.txt` de cada
plataforma al inicio de su corrida y verifica con `urllib.robotparser` que la
URL de navegación pública esté permitida para nuestro User-Agent. Si está
prohibida, la plataforma se **skipea** con log explícito en stdout. La lógica
está integrada en el runner ([run.py:71-78](../scraper/run.py#L71-L78)) y se
ejecuta antes de cualquier `page.goto()`.

## Resultado por plataforma (2026-05-11)

| Plataforma | nav_url chequeada | Resultado | Notas |
|---|---|---|---|
| Rappi | `/restaurantes/delivery/706-mcdonald-s` | ALLOWED | El storefront público no está en disallow. |
| Uber Eats | `/mx` | ALLOWED | Disallows `*/search?`, `*/delivery-details`; no aplica. |
| DiDi Food | `/es-MX/food/` | N/A — sin superficie scrapeable | `robots.txt` 404, pero la pregunta es moot: DiDi MX no tiene web ordering. Ver §DiDi abajo. |

## Rappi: qué consumimos del DOM público vs qué hace el browser

El `robots.txt` de Rappi prohíbe `/api`, `/api-services` y `/base-api` para
`User-agent: *`. Nuestra implementación respeta esa directiva en el sentido
relevante: **no leemos, parseamos ni persistimos ningún response de esos
endpoints**.

Fuentes de data del scraper:

1. **JSON-LD público** — `<script id="seo-structured-schema"
   type="application/ld+json">` server-rendered en el HTML de la URL pública.
   Es data estructurada que Rappi expone *deliberadamente* para motores de
   búsqueda (schema.org `Restaurant`); destino: clientes automatizados. De ahí
   sacamos: store name, dirección, geo, menú completo con precios y delivery
   fee.
2. **DOM visible** — selectores sobre elementos pintados (span/p con "X min"
   para ETA, banners de promo). Equivalente a lo que ve un usuario humano.

Lo que NO hacemos: registrar un `page.on("response", ...)` que intercepte y
parsee responses de `/api`. La versión previa del scraper sí lo hacía y fue
removida por este motivo (ver commit del refactor).

**Sobre los XHR del browser:** durante el render, el navegador igual emite
requests a `/api/web-gateway/...` (lo mismo que haría el browser de cualquier
usuario que abra la URL pública). Sin esos requests internos la página no se
puebla. Probamos bloquear `/api` con `page.route(...)` y el resultado fue que
JSON-LD y ETA no llegan a renderizarse, confirmando que esos requests son
parte del flujo normal de carga de la página pública, no un acto adicional de
scraping. Robots.txt regula el consumo activo por parte de un cliente
automatizado; nuestro cliente automatizado consume únicamente el DOM público.

## Trade-offs declarados

- `eta_min_low` / `eta_min_high`: el DOM solo expone el punto medio del ETA.
  Las tres columnas (low/mid/high) quedan iguales. Es una pérdida vs la
  versión `/api` que daba el rango.
- `service_fee_mxn`: no aparece en JSON-LD ni en el DOM público (se ve recién
  en checkout). Imputamos 0, como en la versión previa (era 0 para McDonald's
  en todas las direcciones).
- `discount_mxn`: si hay banner "Envío Gratis" visible en el header,
  imputamos `discount = -delivery_fee`. El texto raw de la promo va en
  `promo_text`.

## DiDi Food: límite ético declarado

DiDi Food MX no tiene **ninguna** superficie web de ordering (recon documentado
en [`blockers.md`](blockers.md)). La única forma técnica de obtener precios y
menús sería:

1. Levantar mitmproxy contra la app móvil oficial,
2. Bypass del certificate pinning (Frida / objection),
3. Reverseo del esquema de firma de requests propietario de DiDi,
4. Persistir y replicar tokens de sesión emitidos por la app.

Estas técnicas son **incompatibles con el espíritu del brief** ("respetar
robots.txt cuando sea posible") y con los ToS de la app DiDi Food, que
prohíben acceso automatizado. Por eso el [`DidiScraper`](../scraper/didi.py)
emite filas con `available=False` y `notes="didi_mx_no_public_web_surface_app_only"`
en lugar de intentar la captura por canales más invasivos.

La ausencia de DiDi en el dataset queda explícitamente visible en el CSV (no
oculta) — el notebook de insights lo señala como hallazgo competitivo:
**DiDi MX optó por app-only post-2022 mientras Rappi y Uber Eats mantienen
web ordering plena**.

## Otros controles

- **Rate limit:** `asyncio.sleep(1.5)` entre direcciones ([run.py:80](../scraper/run.py#L80)).
- **User-Agent:** Chrome 131 desktop real ([rappi.py:73-76](../scraper/rappi.py#L73-L76)).
- **Sin paralelismo por plataforma:** las 6 direcciones se procesan
  secuencialmente.
- **Datos públicamente accesibles sin login:** el scraper no autentica ni
  accede a información privada.
- **Sin credenciales en repo.**
