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
    """Item con keyword + precio en rango y sin exclude_keywords.

    Cuando hay múltiples candidatos válidos, prefiere el de nombre más corto:
    "Big Mac" gana sobre "Home Office con Big Mac" — la versión más corta
    suele ser el SKU canónico, no una promo/variante.
    """
    kws = _keywords(product)
    excludes = [_normalize(k) for k in product.exclude_keywords if k.strip()]
    candidates: list[tuple[int, MenuItem]] = []
    for item in menu:
        name = _normalize(item.name_raw)
        if not any(kw in name for kw in kws):
            continue
        if excludes and any(ex in name for ex in excludes):
            continue
        if not (product.price_min_mxn <= item.unit_price_mxn <= product.price_max_mxn):
            continue
        candidates.append((len(name), item))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1]
