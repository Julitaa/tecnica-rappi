"""DiDi Food scraper. Stub en tramo 1; implementación real en tramo 3."""

from __future__ import annotations

from typing import Sequence

from .base import PlatformScraper
from .models import Address, Product, ScrapeRow


class DidiScraper(PlatformScraper):
    name = "didi"

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
                collection_method="api",
                available=False,
                notes="stub:tramo1",
            )
            for product in products
        ]
