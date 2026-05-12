"""Rappi scraper — Playwright anónimo, extracción del DOM público.

Cumplimiento de robots.txt: el `robots.txt` de Rappi prohíbe `/api`, `/api-services`
y `/base-api` para User-agent: *. Por eso NO interceptamos ningún response de
esos endpoints. Trabajamos exclusivamente con:

  1. JSON-LD público (`<script id="seo-structured-schema" type="application/ld+json">`)
     que Rappi expone *deliberadamente* para SEO — es data estructurada
     destinada a clientes automatizados. Contiene store + menú con precios.
  2. Selectores DOM visibles para ETA y promociones.

Flujo:
  1. Lanzar contexto chromium con geolocation = (address.lat, address.lng).
  2. Navegar a /restaurantes/delivery/706-mcdonald-s (URL permitida por robots).
  3. Cliquear "Usa tu ubicación actual" → Rappi redirige a la tienda más cercana.
  4. Esperar que cargue el storefront y leer el JSON-LD + ETA del DOM.
  5. Emitir una fila por SKU del catálogo aplicando matching por keyword + rango.

Trade-off respecto a la versión que leía `/api`:
  - Perdemos el rango ETA (min/max). El DOM expone solo el punto medio →
    eta_min_low = eta_min_high = eta_min.
  - `percentage_service_fee` no está en JSON-LD; era 0 para McDonald's en todas
    las direcciones, así que mantenemos service_fee=0 imputado.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Sequence

from playwright.async_api import (
    BrowserContext,
    TimeoutError as PWTimeout,
    async_playwright,
)

from .base import PlatformScraper
from .matching import MenuItem, match_product
from .models import Address, Brand, Product, ScrapeRow

log = logging.getLogger("scraper.rappi")

BRAND_MCDONALDS_URL = "https://www.rappi.com.mx/restaurantes/delivery/706-mcdonald-s"
USE_LOCATION_TEXT = "Usa tu ubicación actual"
PAGE_TIMEOUT_MS = 45_000
# URL final tras redirect: /restaurantes/<store_id>-<slug>
STORE_URL_PATTERN = re.compile(r"/restaurantes/(\d+)-")


_DEFAULT_BRAND = Brand(
    brand_id="mcdonalds",
    platform="rappi",
    vertical="fast_food",
    nav_strategy="brand_url",
    nav_param=BRAND_MCDONALDS_URL,
)


class RappiScraper(PlatformScraper):
    name = "rappi"

    def __init__(self, brand: Brand | None = None, headless: bool = True):
        self.brand = brand or _DEFAULT_BRAND
        self.nav_url = self.brand.nav_param
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
                    storefront, notes = await self._capture_storefront(ctx, address)
                finally:
                    await ctx.close()
            finally:
                await browser.close()

        if storefront is None:
            return [
                _empty_row(
                    address,
                    product,
                    notes=notes or "rappi:no_store",
                    brand_id=self.brand.brand_id,
                )
                for product in products
            ]

        return _rows_from_storefront(storefront, address, products, self.brand.brand_id)

    async def _capture_storefront(
        self,
        ctx: BrowserContext,
        address: Address,
    ) -> tuple[dict[str, Any] | None, str | None]:
        page = await ctx.new_page()

        try:
            await page.goto(self.brand.nav_param, timeout=PAGE_TIMEOUT_MS)
        except PWTimeout:
            return None, "rappi:brand_page_timeout"

        try:
            await page.wait_for_selector(
                '[data-testid="address_capture"]', timeout=15_000
            )
        except PWTimeout:
            log.info("[%s] sin modal address_capture", address.label)

        try:
            await page.get_by_text(USE_LOCATION_TEXT, exact=False).click(timeout=8_000)
        except PWTimeout:
            return None, "rappi:use_location_button_missing"

        # Esperar a que el storefront cargue el JSON-LD del menú.
        try:
            await page.wait_for_function(
                """() => {
                    const el = document.getElementById('seo-structured-schema');
                    if (!el) return false;
                    try {
                        const j = JSON.parse(el.textContent);
                        return !!(j && j.hasMenu && j.hasMenu.hasMenuSection);
                    } catch { return false; }
                }""",
                timeout=25_000,
            )
        except PWTimeout:
            return None, "rappi:storefront_timeout"

        # Extracción del DOM público
        try:
            payload = await page.evaluate(
                """() => {
                    const ldEl = document.getElementById('seo-structured-schema');
                    const ld = ldEl ? JSON.parse(ldEl.textContent) : null;

                    // ETA: buscar primer span corto con "<n> min" (textContent porque
                    // innerText puede ser vacío hasta layout pintado)
                    let eta = null;
                    const re = /(\\d+)\\s*min/i;
                    for (const el of document.querySelectorAll('span, p')) {
                        const t = (el.textContent || '').trim();
                        if (!t || t.length > 20) continue;
                        const m = t.match(re);
                        if (m) { eta = parseInt(m[1], 10); break; }
                    }

                    // Free shipping: indicador "Envío Gratis" visible en el header
                    const bodyText = document.body.innerText || '';
                    const freeShipping = /Env[ií]o\\s*\\n*\\s*Gratis/i.test(bodyText)
                        || /env[ií]os?\\s+gratis/i.test(bodyText);

                    // Promo text raw: junta primeros banners promocionales visibles
                    const promoBits = [];
                    const banners = document.querySelectorAll(
                        '[data-testid*="banner"], [data-testid*="promo"], [class*="promo"]'
                    );
                    for (const b of banners) {
                        const t = (b.innerText || '').trim();
                        if (t && t.length < 200) promoBits.push(t);
                        if (promoBits.length >= 3) break;
                    }

                    return {
                        url: window.location.href,
                        jsonld: ld,
                        eta_min: eta,
                        free_shipping: freeShipping,
                        promo_text: promoBits.join(' | ') || null,
                    };
                }"""
            )
        except Exception as e:
            return None, f"rappi:dom_extract_failed:{e.__class__.__name__}"

        if not payload or not payload.get("jsonld"):
            return None, "rappi:jsonld_missing"

        return payload, None


def _empty_row(
    address: Address, product: Product, notes: str, brand_id: str
) -> ScrapeRow:
    return ScrapeRow(
        platform="rappi",
        address_id=address.address_id,
        address_label=address.label,
        product_sku=product.sku,
        collection_method="playwright",
        available=False,
        notes=notes,
        brand_id=brand_id,
    )


def _iter_menu_items(jsonld: dict) -> list[MenuItem]:
    """Aplana hasMenuSection → hasMenuItem → {name, offers.price}.

    Estructura observada:
      hasMenu.hasMenuSection: list[ list[ { name, offers, hasMenuItem } ] ]
      donde hasMenuItem: list[ list[ { name, offers: {price, priceCurrency} } ] ]
    """
    items: list[MenuItem] = []
    sections = (jsonld.get("hasMenu") or {}).get("hasMenuSection") or []

    def _walk(node: Any) -> None:
        if isinstance(node, list):
            for x in node:
                _walk(x)
            return
        if not isinstance(node, dict):
            return
        if node.get("@type") == "MenuItem":
            name = node.get("name") or ""
            offers = node.get("offers") or {}
            price = offers.get("price") if isinstance(offers, dict) else None
            if name and price is not None:
                try:
                    items.append(MenuItem(name_raw=name, unit_price_mxn=float(price)))
                except (TypeError, ValueError):
                    pass
            return
        # Recurse por estructura: sub-secciones o hasMenuItem
        for key in ("hasMenuItem", "hasMenuSection"):
            if key in node:
                _walk(node[key])

    _walk(sections)
    return items


def _store_id_from_url(url: str) -> str | None:
    m = STORE_URL_PATTERN.search(url or "")
    return m.group(1) if m else None


def _delivery_fee(jsonld: dict) -> float:
    spec = (jsonld.get("potentialAction") or {}).get("priceSpecification") or {}
    return _to_float(spec.get("price")) or 0.0


def _rows_from_storefront(
    storefront: dict,
    address: Address,
    products: Sequence[Product],
    brand_id: str,
) -> list[ScrapeRow]:
    jsonld = storefront["jsonld"]
    menu = _iter_menu_items(jsonld)
    eta_value = storefront.get("eta_min")
    delivery_fee = _delivery_fee(jsonld)
    has_free_shipping = bool(storefront.get("free_shipping"))
    # Si el banner muestra "Envío Gratis", el delivery_fee efectivo es 0.
    if has_free_shipping:
        delivery_fee_effective = delivery_fee
        discount = round(-delivery_fee, 2)
    else:
        delivery_fee_effective = delivery_fee
        discount = 0.0

    service_fee = 0.0  # no expuesto fuera del checkout (ver compliance.md)
    promo = storefront.get("promo_text")
    store_id = _store_id_from_url(storefront.get("url") or "")
    store_name_jsonld = jsonld.get("name") or ""
    address_node = jsonld.get("address") or {}
    street = address_node.get("streetAddress") if isinstance(address_node, dict) else ""
    store_name = (
        f"{store_name_jsonld} - {street.split(',')[0]}".strip(" -")
        if street
        else store_name_jsonld
    )

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
                    store_id=store_id,
                    store_name=store_name or None,
                    eta_min=eta_value,
                    eta_min_low=eta_value,
                    eta_min_high=eta_value,
                    delivery_fee_mxn=delivery_fee_effective,
                    promo_text=promo,
                    notes="no_match_in_menu",
                    brand_id=brand_id,
                )
            )
            continue

        unit = match.unit_price_mxn
        total = round(unit + delivery_fee_effective + service_fee + discount, 2)
        rows.append(
            ScrapeRow(
                platform="rappi",
                address_id=address.address_id,
                address_label=address.label,
                product_sku=product.sku,
                collection_method="playwright",
                available=True,
                store_id=store_id,
                store_name=store_name or None,
                product_name_raw=match.name_raw,
                unit_price_mxn=unit,
                delivery_fee_mxn=delivery_fee_effective,
                service_fee_mxn=service_fee,
                discount_mxn=discount,
                total_final_mxn=total,
                eta_min=eta_value,
                eta_min_low=eta_value,
                eta_min_high=eta_value,
                promo_text=promo,
                brand_id=brand_id,
            )
        )
    return rows


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
