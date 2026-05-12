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
from .catalog import DATA_DIR, load_addresses, load_brands, load_products
from .didi import DidiScraper
from .models import Address, Brand, Product, ScrapeRow
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
    "brand_id",
]


def _build_scrapers(
    platform: str, brand_filter: str | None
) -> list[PlatformScraper]:
    brands = load_brands()
    # DiDi no está en brands.csv (es app-only). Lo incluimos solo si
    # el target es fast_food y la plataforma lo pide.
    if platform != "all" and platform not in SCRAPERS:
        raise SystemExit(f"plataforma desconocida: {platform}")
    if platform != "all":
        brands = [b for b in brands if b.platform == platform]
    if brand_filter:
        brands = [b for b in brands if b.brand_id == brand_filter]

    out: list[PlatformScraper] = []
    for b in brands:
        cls = SCRAPERS.get(b.platform)
        if cls is None:
            continue
        out.append(cls(brand=b))

    # DiDi: una sola instancia con default brand si platform=all/didi y
    # no se filtró por una brand específica que no sea mcdonalds.
    if (platform in ("all", "didi")) and (brand_filter in (None, "mcdonalds")):
        out.append(DidiScraper())
    return out


async def _run_one(
    scraper: PlatformScraper,
    addresses: list[Address],
    products: list[Product],
) -> list[ScrapeRow]:
    brand_id = getattr(scraper, "brand", None)
    brand_label = brand_id.brand_id if brand_id else "?"
    robots = scraper.check_robots()
    fetched = "ok" if robots.fetched else "ausente/404"
    if not robots.allowed:
        print(
            f"SKIP {scraper.name}/{brand_label}: robots.txt ({fetched}) "
            f"prohibe {robots.url}. Ver {robots.robots_url}."
        )
        return []
    print(
        f"OK robots {scraper.name}/{brand_label}: {robots.url} "
        f"permitido ({fetched})."
    )

    vertical = scraper.brand.vertical
    products_for_brand = [p for p in products if p.vertical == vertical]
    rows: list[ScrapeRow] = []
    for address in addresses:
        rows.extend(await scraper.scrape(address, products_for_brand))
        await asyncio.sleep(1.5)  # rate-limit defensivo (ver spec §9)
    return rows


async def _run(platform: str, brand_filter: str | None) -> list[ScrapeRow]:
    addresses = load_addresses()
    products = load_products()
    scrapers = _build_scrapers(platform, brand_filter)
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
        "--brand",
        default=None,
        help="Filtrar a un brand_id (ej. mcdonalds, walmart_super)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DATA_DIR,
        help="Directorio de salida (default: ../data)",
    )
    args = parser.parse_args()

    rows = asyncio.run(_run(args.platform, args.brand))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, args.out_dir / "scrapes.csv")
    _write_json(rows, args.out_dir / "scrapes.json")

    print(f"OK · {len(rows)} filas · platform={args.platform}")


if __name__ == "__main__":
    main()
