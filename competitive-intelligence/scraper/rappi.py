"""Rappi scraper — Playwright anónimo (sin login).

Flujo:
  1. Lanzar contexto chromium con geolocation = (address.lat, address.lng)
     y permiso de geolocation otorgado.
  2. Navegar a /restaurantes/delivery/706-mcdonald-s (brand page McDonald's).
  3. Esperar el modal address_capture y cliquear "Usa tu ubicación actual";
     Rappi redirige a la tienda más cercana al punto.
  4. Interceptar la respuesta JSON de
     `services.mxgrability.rappi.com/api/web-gateway/web/restaurants-bus/store/id/<id>/`
     que trae: store name, ETA, delivery_price, percentage_service_fee,
     discount_tags y `corridors[].products[]` con precios.
  5. Emitir una fila por SKU del catálogo aplicando matching por keyword + rango.

Si algo falla (sin tiendas cercanas, timeout del modal, captcha), devolvemos
filas con `available=False` y `notes` describiendo el motivo, preservando la
forma de la matriz para los insights del notebook.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Sequence

from playwright.async_api import (
    BrowserContext,
    Response,
    TimeoutError as PWTimeout,
    async_playwright,
)

from .base import PlatformScraper
from .matching import MenuItem, match_product
from .models import Address, Product, ScrapeRow

log = logging.getLogger("scraper.rappi")

BRAND_MCDONALDS_URL = "https://www.rappi.com.mx/restaurantes/delivery/706-mcdonald-s"
STORE_API_PATTERN = re.compile(
    r"services\.mxgrability\.rappi\.com/api/web-gateway/web/restaurants-bus/store/id/(\d+)/?"
)
USE_LOCATION_TEXT = "Usa tu ubicación actual"
PAGE_TIMEOUT_MS = 45_000


class RappiScraper(PlatformScraper):
    name = "rappi"

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def scrape(
        self,
        address: Address,
        products: Sequence[Product],
    ) -> list[ScrapeRow]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                ctx = await browser.new_context(
                    locale="es-MX",
                    geolocation={"latitude": address.lat, "longitude": address.lng},
                    permissions=["geolocation"],
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                )
                try:
                    store_json, notes = await self._capture_store(ctx, address)
                finally:
                    await ctx.close()
            finally:
                await browser.close()

        if store_json is None:
            return [
                _empty_row(address, product, notes=notes or "rappi:no_store")
                for product in products
            ]

        return _rows_from_store(store_json, address, products)

    async def _capture_store(
        self,
        ctx: BrowserContext,
        address: Address,
    ) -> tuple[dict[str, Any] | None, str | None]:
        page = await ctx.new_page()
        store_payload: dict[str, Any] | None = None
        capture_event = asyncio.Event()

        async def on_response(resp: Response) -> None:
            nonlocal store_payload
            if store_payload is not None:
                return
            if not STORE_API_PATTERN.search(resp.url):
                return
            if resp.status != 200:
                return
            try:
                ctype = resp.headers.get("content-type", "")
                if "json" not in ctype:
                    return
                body = await resp.text()
                store_payload = json.loads(body)
                capture_event.set()
            except Exception as e:
                log.debug("response parse failed: %s", e)

        page.on("response", lambda r: asyncio.create_task(on_response(r)))

        try:
            await page.goto(BRAND_MCDONALDS_URL, timeout=PAGE_TIMEOUT_MS)
        except PWTimeout:
            return None, "rappi:brand_page_timeout"

        # esperar al modal address_capture
        try:
            await page.wait_for_selector(
                '[data-testid="address_capture"]', timeout=15_000
            )
        except PWTimeout:
            log.info("[%s] sin modal address_capture", address.label)

        # click "Usa tu ubicación actual"
        try:
            await page.get_by_text(USE_LOCATION_TEXT, exact=False).click(timeout=8_000)
        except PWTimeout:
            return None, "rappi:use_location_button_missing"

        # esperar el payload JSON
        try:
            await asyncio.wait_for(capture_event.wait(), timeout=25)
        except asyncio.TimeoutError:
            return None, "rappi:store_json_timeout"

        return store_payload, None


def _empty_row(
    address: Address,
    product: Product,
    notes: str,
) -> ScrapeRow:
    return ScrapeRow(
        platform="rappi",
        address_id=address.address_id,
        address_label=address.label,
        product_sku=product.sku,
        collection_method="playwright",
        available=False,
        notes=notes,
    )


def _iter_products(store: dict) -> list[MenuItem]:
    items: list[MenuItem] = []
    for corridor in store.get("corridors", []) or []:
        for p in corridor.get("products", []) or []:
            price = p.get("real_price") or p.get("price")
            name = p.get("name") or ""
            if price is None or not name:
                continue
            try:
                items.append(MenuItem(name_raw=name, unit_price_mxn=float(price)))
            except (TypeError, ValueError):
                continue
    return items


def _promo_text(store: dict) -> str | None:
    tags = store.get("discount_tags") or []
    titles = [t.get("title") or t.get("tag") or "" for t in tags]
    titles = [t for t in titles if t]
    return " | ".join(titles) if titles else None


def _discount_mxn() -> float:
    """Rappi no expone un monto fijo de descuento accionable sin checkout.

    Si hay `free_shipping` en discount_tags, el descuento se imputa al
    delivery_fee (manejado por el caller). En el resto de casos retornamos 0
    para no inventar valores.
    """
    return 0.0


def _rows_from_store(
    store: dict,
    address: Address,
    products: Sequence[Product],
) -> list[ScrapeRow]:
    menu = _iter_products(store)
    eta_value = _to_int(store.get("eta_value") or store.get("eta"))
    etas = (store.get("etas") or [{}])[0]
    eta_low = _to_int(etas.get("min")) or eta_value
    eta_high = _to_int(etas.get("max")) or eta_value
    delivery_fee = _to_float(store.get("delivery_price")) or 0.0
    pct_service = _to_float(store.get("percentage_service_fee")) or 0.0
    promo = _promo_text(store)
    has_free_shipping = any(
        (t.get("type") or "").lower() == "free_shipping"
        for t in (store.get("discount_tags") or [])
    )
    store_id = str(store.get("store_id") or "")
    store_name = store.get("name") or ""

    rows: list[ScrapeRow] = []
    for product in products:
        match = match_product(menu, product)
        if match is None:
            rows.append(
                ScrapeRow(
                    platform="rappi",
                    address_id=address.address_id,
                    address_label=address.label,
                    product_sku=product.sku,
                    collection_method="playwright",
                    available=False,
                    store_id=store_id or None,
                    store_name=store_name or None,
                    eta_min=eta_value,
                    eta_min_low=eta_low,
                    eta_min_high=eta_high,
                    delivery_fee_mxn=delivery_fee,
                    promo_text=promo,
                    notes="no_match_in_menu",
                )
            )
            continue

        unit = match.unit_price_mxn
        service_fee = round(unit * pct_service / 100.0, 2) if pct_service else 0.0
        # Si hay free_shipping vigente, descuento = -delivery_fee
        discount = round(-delivery_fee, 2) if has_free_shipping else _discount_mxn()
        total = round(unit + delivery_fee + service_fee + discount, 2)

        rows.append(
            ScrapeRow(
                platform="rappi",
                address_id=address.address_id,
                address_label=address.label,
                product_sku=product.sku,
                collection_method="playwright",
                available=True,
                store_id=store_id or None,
                store_name=store_name or None,
                product_name_raw=match.name_raw,
                unit_price_mxn=unit,
                delivery_fee_mxn=delivery_fee,
                service_fee_mxn=service_fee,
                discount_mxn=discount,
                total_final_mxn=total,
                eta_min=eta_value,
                eta_min_low=eta_low,
                eta_min_high=eta_high,
                promo_text=promo,
            )
        )
    return rows


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
