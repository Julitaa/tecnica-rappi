"""Carga catálogos fijos (addresses, products) desde data/*.csv."""

from __future__ import annotations

import csv
from pathlib import Path

from .models import Address, Product

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_addresses(path: Path | None = None) -> list[Address]:
    path = path or (DATA_DIR / "addresses.csv")
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            Address(
                address_id=int(row["address_id"]),
                label=row["label"],
                street=row["street"],
                lat=float(row["lat"]),
                lng=float(row["lng"]),
                zone_type=row["zone_type"],
            )
            for row in reader
        ]


def load_products(path: Path | None = None) -> list[Product]:
    path = path or (DATA_DIR / "products.csv")
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            Product(
                sku=row["sku"],  # type: ignore[arg-type]
                canonical_name=row["canonical_name"],
                vertical=row["vertical"],
                search_keywords=tuple(
                    k.strip() for k in row["search_keywords"].split("|") if k.strip()
                ),
                price_min_mxn=float(row["price_min_mxn"]),
                price_max_mxn=float(row["price_max_mxn"]),
                exclude_keywords=tuple(
                    k.strip()
                    for k in (row.get("exclude_keywords") or "").split("|")
                    if k.strip()
                ),
            )
            for row in reader
        ]
