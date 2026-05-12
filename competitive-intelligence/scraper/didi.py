"""DiDi Food MX scraper — limitación documentada.

DiDi Food en México **no tiene superficie web de ordering**. Es 100% app-only.
Recon realizado el 2026-05-11 (ver `docs/blockers.md` y `docs/compliance.md`)
confirmó:

  - El único host de cliente es `www.didi-food.com`, que es una landing de
    marketing puro (descarga de app, info corporativa). No tiene búsqueda de
    restaurantes, selección de dirección, menú ni checkout.
  - Subdominios típicos de webapps (`web.`, `m.`, `h5.`, `api.didi-food.com`)
    no resuelven en DNS.
  - Mobile UA devuelve exactamente el mismo HTML (sin content-negotiation).
  - Los XHR de la home apuntan únicamente a telemetría y firma de sesión;
    cero llamadas a APIs de restaurantes o menús.
  - `robots.txt` y `sitemap.xml` devuelven 404 (no existen).

Conclusión: capturar precios/menús de DiDi MX exige reverseo de la app móvil
(mitmproxy, cert pinning bypass), lo cual queda **fuera del scope ético y
temporal** del MVP. Mantengo la columna DiDi en el dataset emitiendo filas
con `available=False` y `notes` específico — preserva el shape de la matriz
(plataforma × dirección × producto) y deja visible la limitación al evaluador,
en línea con la prioridad del brief sobre "documentar qué se logró y qué no".
"""

from __future__ import annotations

from typing import Sequence

from .base import PlatformScraper
from .models import Address, Product, ScrapeRow
from .robots import RobotsResult

UNAVAILABILITY_NOTE = "didi_mx_no_public_web_surface_app_only"


class DidiScraper(PlatformScraper):
    name = "didi"
    # URL marketing — la única superficie pública existente. La declaramos por
    # honestidad (sería el único punto en el que un crawler tocaría DiDi), pero
    # `scrape()` no abre Playwright porque no hay nada que extraer.
    nav_url = "https://www.didi-food.com/es-MX/food/"

    def check_robots(self) -> RobotsResult:
        # Short-circuit: no existe robots.txt en didi-food.com y la URL marketing
        # no es target de scraping de datos. Reportamos allowed=True sin hacer
        # request — evita ruido en stdout y un round-trip innecesario.
        return RobotsResult(
            url=self.nav_url,
            allowed=True,
            robots_url="https://www.didi-food.com/robots.txt",
            fetched=False,
        )

    async def scrape(
        self,
        address: Address,
        products: Sequence[Product],
    ) -> list[ScrapeRow]:
        return [
            ScrapeRow(
                platform="didi",
                address_id=address.address_id,
                address_label=address.label,
                product_sku=product.sku,
                collection_method="playwright",
                available=False,
                notes=UNAVAILABILITY_NOTE,
            )
            for product in products
        ]
