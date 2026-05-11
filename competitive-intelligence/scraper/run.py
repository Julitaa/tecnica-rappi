"""CLI orquestador: corre los scrapers seleccionados y escribe scrapes.{csv,json}.

Uso:
    python -m scraper.run --platform [rappi|ubereats|didi|all]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from .base import PlatformScraper
from .catalog import DATA_DIR, load_addresses, load_products
from .didi import DidiScraper
from .models import Address, Product, ScrapeRow
from .rappi import RappiScraper
from .ubereats import UberEatsScraper

SCRAPERS: dict[str, type[PlatformScraper]] = {
    "rappi": RappiScraper,
    "ubereats": UberEatsScraper,
    "didi": DidiScraper,
}

CSV_COLUMNS = [
    "scrape_id",
    "timestamp_utc",
    "platform",
    "address_id",
    "address_label",
    "store_id",
    "store_name",
    "product_sku",
    "product_name_raw",
    "unit_price_mxn",
    "delivery_fee_mxn",
    "service_fee_mxn",
    "discount_mxn",
    "total_final_mxn",
    "eta_min",
    "eta_min_low",
    "eta_min_high",
    "available",
    "promo_text",
    "collection_method",
    "notes",
]


def _select_scrapers(platform: str) -> list[PlatformScraper]:
    if platform == "all":
        return [cls() for cls in SCRAPERS.values()]
    if platform not in SCRAPERS:
        raise SystemExit(f"plataforma desconocida: {platform}")
    return [SCRAPERS[platform]()]


async def _run_one(
    scraper: PlatformScraper,
    addresses: list[Address],
    products: list[Product],
) -> list[ScrapeRow]:
    rows: list[ScrapeRow] = []
    for address in addresses:
        rows.extend(await scraper.scrape(address, products))
        await asyncio.sleep(1.5)  # rate-limit defensivo (ver spec §9)
    return rows


async def _run(platform: str) -> list[ScrapeRow]:
    addresses = load_addresses()
    products = load_products()
    scrapers = _select_scrapers(platform)
    results = await asyncio.gather(
        *(_run_one(s, addresses, products) for s in scrapers)
    )
    return [row for batch in results for row in batch]


def _write_csv(rows: list[ScrapeRow], path: Path) -> None:
    import csv

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _write_json(rows: list[ScrapeRow], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in rows], f, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Competitive intelligence scraper")
    parser.add_argument(
        "--platform",
        choices=["rappi", "ubereats", "didi", "all"],
        default="all",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DATA_DIR,
        help="Directorio de salida (default: ../data)",
    )
    args = parser.parse_args()

    rows = asyncio.run(_run(args.platform))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, args.out_dir / "scrapes.csv")
    _write_json(rows, args.out_dir / "scrapes.json")

    print(f"OK · {len(rows)} filas · platform={args.platform}")


if __name__ == "__main__":
    main()
