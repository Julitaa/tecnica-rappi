"""Fuzzy product matching by keyword + price range.

Una sola regla pública: dado un menú raw (lista de items con nombre y precio)
y un Product, devuelve el primer match (item, score) o None.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .models import Product


@dataclass(frozen=True)
class MenuItem:
    name_raw: str
    unit_price_mxn: float


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _keywords(product: Product) -> list[str]:
    return [_normalize(k) for k in product.search_keywords if k.strip()]


def match_product(
    menu: Iterable[MenuItem],
    product: Product,
) -> Optional[MenuItem]:
    """Primer item con keyword + precio en rango y sin exclude_keywords."""
    kws = _keywords(product)
    excludes = [_normalize(k) for k in product.exclude_keywords if k.strip()]
    for item in menu:
        name = _normalize(item.name_raw)
        if not any(kw in name for kw in kws):
            continue
        if excludes and any(ex in name for ex in excludes):
            continue
        if not (product.price_min_mxn <= item.unit_price_mxn <= product.price_max_mxn):
            continue
        return item
    return None
