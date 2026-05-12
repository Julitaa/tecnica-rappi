"""Uber Eats MX scraper — Playwright anónimo, extracción del DOM público.

Cumplimiento de robots.txt: el `robots.txt` de ubereats.com permite `/mx` y
prohíbe `*/search?`, `*/delivery-details` y otros. **No** consumimos ningún
response de XHR `/api/...`. Trabajamos exclusivamente con:

  1. JSON-LD público en el storefront page
     (`<script type="application/ld+json">` con `@type=Restaurant`) que
     incluye `hasMenu.hasMenuSection[].hasMenuItem[]` con precios MXN.
     Es data estructurada que Uber Eats expone para SEO, destinada a
     clientes automatizados.
  2. DOM visible: la card del search results trae el ETA del store y el
     storefront muestra texto de delivery fee y promos.

Flujo por dirección:
  1. Construir `pl` (param de location) en base64 con solo lat/lng — Uber
     Eats resuelve la `reference` en su propio place-index server-side.
  2. Navegar al feed (`/mx/feed?pl=...`) sin búsqueda. Esto fija el state
     de address en la sesión y la URL final responde con la `reference`
     real en el redirect.
  3. Navegar al storefront de McDonald's más cercano. Usamos un URL de
     anchor pre-conocido (recon previo) y dejamos que Uber Eats sustituya
     a la sede correcta si la pl no la sirve — si la tienda específica
     "no entrega a esa dirección" devuelve 200 con un banner "no
     disponible", que detectamos y emitimos `available=False`.

Por simplicidad y robustez en el time-box: navegamos `/mx/search?q=mcdonalds
&pl=...` y tomamos el primer resultado `/store/mcdonalds-*`. Eso da el store
más cercano + ETA en la misma card.

Trade-offs declarados:
  - `eta_min_low/high` = `eta_min` (el DOM expone solo un valor "X min").
  - `service_fee_mxn` no expuesto fuera del checkout → imputamos 0
    (mismo trato que Rappi; ver `compliance.md`).
  - `delivery_fee_mxn`: leído del banner del storefront ("Costo de envío de
    $X"). Si solo aparece "Costo de envío de $0 con Uber One" (oferta
    condicional a membresía), imputamos 0 como tarifa base + `promo_text`
    preserva el contexto.
  - `discount_mxn`: si el banner muestra envío gratis incondicional,
    `discount = -delivery_fee`. Si la oferta es "con Uber One" (no
    aplicable a usuario anónimo), no descontamos.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from typing import Any, Sequence
from urllib.parse import quote

from playwright.async_api import (
    BrowserContext,
    TimeoutError as PWTimeout,
    async_playwright,
)

from .base import PlatformScraper
from .matching import MenuItem, match_product
from .models import Address, Product, ScrapeRow

log = logging.getLogger("scraper.ubereats")

PAGE_TIMEOUT_MS = 45_000
SEARCH_TIMEOUT_MS = 25_000
STORE_TIMEOUT_MS = 30_000
SEARCH_URL_TEMPLATE = "https://www.ubereats.com/mx/search?q=mcdonalds&pl={pl}"
MCD_STORE_HREF_RE = re.compile(r"/mx/store/mcdonalds[a-z0-9\-]*/[A-Za-z0-9_\-]+")
# Algunos resultados son "McDonald's Dummy ..." o postres-x-mcdonalds; queremos
# el storefront principal: nombre empieza con "mcdonalds-" + sufijo simple.
DUMMY_STORE_RE = re.compile(r"/store/mcdonalds-dummy", re.IGNORECASE)


def _build_pl(address: Address) -> str:
    """Construye el param `pl` de Uber Eats: base64(urlencode(JSON)).

    JSON shape: {"address": str, "latitude": float, "longitude": float}.
    Uber Eats resuelve `reference`/`referenceType` server-side cuando se
    omiten — el redirect rellena la URL con `uber_places` reference.
    """
    payload = {
        "address": address.street,
        "latitude": address.lat,
        "longitude": address.lng,
    }
    raw = json.dumps(payload, ensure_ascii=False)
    url_encoded = quote(raw, safe="")
    return base64.b64encode(url_encoded.encode("utf-8")).decode("ascii")


class UberEatsScraper(PlatformScraper):
    name = "ubereats"
    nav_url = "https://www.ubereats.com/mx"

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
                    viewport={"width": 1400, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                )
                try:
                    captured, notes = await self._capture(ctx, address)
                finally:
                    await ctx.close()
            finally:
                await browser.close()

        if captured is None:
            return [
                _empty_row(address, product, notes=notes or "ubereats:no_store")
                for product in products
            ]
        return _rows_from_capture(captured, address, products)

    async def _capture(
        self,
        ctx: BrowserContext,
        address: Address,
    ) -> tuple[dict[str, Any] | None, str | None]:
        pl = _build_pl(address)
        search_url = SEARCH_URL_TEMPLATE.format(pl=quote(pl, safe=""))

        page = await ctx.new_page()
        try:
            await page.goto(
                search_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded"
            )
        except PWTimeout:
            return None, "ubereats:search_timeout"

        # Esperar a que aparezca al menos un card de McDonald's no-dummy
        # cuyo subtree contenga también "<N> min" — eso garantiza que la
        # card terminó de hidratar con su ETA.
        try:
            await page.wait_for_function(
                """() => {
                    const anchors = [...document.querySelectorAll('a[href*=\"/store/mcdonalds\"]')];
                    for (const a of anchors) {
                        if (/\\/store\\/mcdonalds-dummy/i.test(a.href)) continue;
                        let node = a.parentElement;
                        for (let i = 0; i < 15 && node; i++) {
                            const t = node.innerText || '';
                            if (/\\d+\\s*min/.test(t) && /McDonald/i.test(t)) return true;
                            node = node.parentElement;
                        }
                    }
                    return false;
                }""",
                timeout=SEARCH_TIMEOUT_MS,
            )
        except PWTimeout:
            return None, "ubereats:no_search_results"

        first = await page.evaluate(
            """() => {
                const anchors = [...document.querySelectorAll('a[href*=\"/store/mcdonalds\"]')];
                const seen = new Set();
                for (const a of anchors) {
                    if (/\\/store\\/mcdonalds-dummy/i.test(a.href)) continue;
                    const base = a.href.split('?')[0];
                    if (seen.has(base)) continue;
                    seen.add(base);
                    // Caminar para arriba hasta encontrar un ancestro cuyo
                    // subtree contenga "<N> min" — ese es el card.
                    let node = a.parentElement;
                    let eta = null;
                    for (let i = 0; i < 15 && node; i++) {
                        const t = node.innerText || '';
                        const m = t.match(/(\\d+)\\s*min/);
                        if (m) { eta = parseInt(m[1], 10); break; }
                        node = node.parentElement;
                    }
                    const name = (a.innerText || '').split('\\n')[0].trim();
                    return {storeUrl: base, eta, name};
                }
                return null;
            }"""
        )
        if not first or not first.get("storeUrl"):
            return None, "ubereats:no_mcdonalds_in_search"

        store_url = f"{first['storeUrl']}?pl={quote(pl, safe='')}"
        try:
            await page.goto(
                store_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded"
            )
        except PWTimeout:
            return None, "ubereats:store_timeout"

        try:
            await page.wait_for_function(
                """() => {
                    const ss = document.querySelectorAll('script[type=\"application/ld+json\"]');
                    for (const s of ss) {
                        try {
                            const j = JSON.parse(s.textContent);
                            if (j && j['@type'] === 'Restaurant' && j.hasMenu) return true;
                        } catch (e) {}
                    }
                    return false;
                }""",
                timeout=STORE_TIMEOUT_MS,
            )
        except PWTimeout:
            return None, "ubereats:no_jsonld_menu"

        payload = await page.evaluate(
            """() => {
                const ss = [...document.querySelectorAll('script[type=\"application/ld+json\"]')];
                let restaurant = null;
                for (const s of ss) {
                    try {
                        const j = JSON.parse(s.textContent);
                        if (j && j['@type'] === 'Restaurant') { restaurant = j; break; }
                    } catch (e) {}
                }
                if (!restaurant) return null;

                // Delivery fee + promo del body
                const body = document.body.innerText || '';
                let deliveryFeeRaw = null;
                let deliveryFreeWithUberOne = false;
                let deliveryFreeUnconditional = false;
                // Patrones observados:
                //   "Costo de envío: MXN0 (usuarios nuevos)"  → promo, no base
                //   "Costo de envío de $0 (gasto de $100)"    → condicional ticket mínimo
                //   "Costo de envío de $0 con Uber One"       → condicional membresía
                //   "Costo de envío de $XX"                   → base
                const promoBits = [];
                for (const m of body.matchAll(/Costo de env[ií]o[^\\n]{0,80}/gi)) {
                    const line = m[0];
                    if (promoBits.indexOf(line) < 0) promoBits.push(line);
                    if (/uber\\s*one/i.test(line)) deliveryFreeWithUberOne = true;
                    const num = line.match(/\\$\\s*([0-9]+(?:\\.[0-9]+)?)|MXN\\s*([0-9]+(?:\\.[0-9]+)?)/i);
                    if (num) {
                        const val = parseFloat(num[1] || num[2]);
                        if (deliveryFeeRaw === null || val > deliveryFeeRaw) deliveryFeeRaw = val;
                    }
                    if (/env[ií]os?\\s+gratis|gratis\\s+sin\\s+condici/i.test(line)) deliveryFreeUnconditional = true;
                }
                // Banners promocionales adicionales (ofertas explícitas).
                for (const m of body.matchAll(/\\d+\\s*Ofertas\\s+disponibles/gi)) {
                    if (promoBits.indexOf(m[0]) < 0) promoBits.push(m[0]);
                    if (promoBits.length >= 5) break;
                }

                return {
                    url: location.href,
                    restaurant,
                    deliveryFeeRaw,
                    deliveryFreeWithUberOne,
                    deliveryFreeUnconditional,
                    promoText: promoBits.join(' | ') || null,
                };
            }"""
        )
        if not payload:
            return None, "ubereats:dom_extract_failed"

        # ETA viene del search card; inyectamos
        payload["eta_min"] = first.get("eta")
        payload["store_name_hint"] = first.get("name")
        return payload, None


def _empty_row(address: Address, product: Product, notes: str) -> ScrapeRow:
    return ScrapeRow(
        platform="ubereats",
        address_id=address.address_id,
        address_label=address.label,
        product_sku=product.sku,
        collection_method="playwright",
        available=False,
        notes=notes,
    )


def _iter_menu_items(restaurant: dict) -> list[MenuItem]:
    """Aplana Restaurant.hasMenu.hasMenuSection[].hasMenuItem[].

    Shape observada en Uber Eats: idéntica a schema.org canónico.
    Reusamos el mismo helper que Rappi (estructura paralela).
    """
    items: list[MenuItem] = []
    sections = (restaurant.get("hasMenu") or {}).get("hasMenuSection") or []

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
        for key in ("hasMenuItem", "hasMenuSection"):
            if key in node:
                _walk(node[key])

    _walk(sections)
    return items


def _store_id_from_url(url: str) -> str | None:
    m = re.search(r"/store/[^/]+/([A-Za-z0-9_\-]+)", url or "")
    return m.group(1) if m else None


def _rows_from_capture(
    captured: dict,
    address: Address,
    products: Sequence[Product],
) -> list[ScrapeRow]:
    restaurant = captured["restaurant"]
    menu = _iter_menu_items(restaurant)
    eta_value = captured.get("eta_min")
    delivery_fee_raw = captured.get("deliveryFeeRaw")
    free_uber_one = bool(captured.get("deliveryFreeWithUberOne"))
    free_unconditional = bool(captured.get("deliveryFreeUnconditional"))
    promo = captured.get("promoText")
    store_name = restaurant.get("name") or captured.get("store_name_hint")
    store_id = _store_id_from_url(captured.get("url") or "")

    # Tarifa efectiva:
    #   - Si hay envío gratis incondicional → fee=0, discount=0 (ya viene neto).
    #   - Si solo "con Uber One" → para usuario anónimo el fee base aplica.
    #   - Si no hay número visible, asumimos 0 (no penalizamos al store).
    if free_unconditional:
        delivery_fee_effective = 0.0
        discount = 0.0
    else:
        delivery_fee_effective = float(delivery_fee_raw) if delivery_fee_raw is not None else 0.0
        discount = 0.0

    service_fee = 0.0  # no expuesto fuera del checkout (ver compliance.md)

    rows: list[ScrapeRow] = []
    for product in products:
        match = match_product(menu, product)
        if match is None:
            rows.append(
                ScrapeRow(
                    platform="ubereats",
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
                )
            )
            continue

        unit = match.unit_price_mxn
        total = round(unit + delivery_fee_effective + service_fee + discount, 2)
        rows.append(
            ScrapeRow(
                platform="ubereats",
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
            )
        )
    return rows
