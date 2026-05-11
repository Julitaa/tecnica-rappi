"""Uber Eats scraper. Stub en tramo 1; implementación real en tramo 4."""

from __future__ import annotations

from typing import Sequence

from .base import PlatformScraper
from .models import Address, Product, ScrapeRow


class UberEatsScraper(PlatformScraper):
    name = "ubereats"

    async def scrape(
        self,
        address: Address,
        products: Sequence[Product],
    ) -> list[ScrapeRow]:
        return [
            ScrapeRow(
                platform="ubereats",
                address_id=address.address_id,
                address_label=address.label,
                product_sku=product.sku,
                collection_method="playwright",
                available=False,
                notes="stub:tramo1",
            )
            for product in products
        ]
