from abc import ABC, abstractmethod
from typing import Sequence

from .models import Address, Product, ScrapeRow


class PlatformScraper(ABC):
    """Interfaz común para cada plataforma (Rappi, UberEats, DiDi).

    Cada implementación decide internamente si usa API (httpx) o Playwright.
    El runner (`scraper.run`) es agnóstico al método de captura.
    """

    name: str

    @abstractmethod
    async def scrape(
        self,
        address: Address,
        products: Sequence[Product],
    ) -> list[ScrapeRow]:
        """Devuelve una fila por producto para la dirección dada.

        Si un producto no está disponible, devuelve una fila con
        `available=False` en lugar de omitirla — preserva el shape
        de la matriz para los insights.
        """
        ...
