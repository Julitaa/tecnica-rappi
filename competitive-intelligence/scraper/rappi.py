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
from pathlib import Path
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
PAGE_TIMEOUT_MS = 30_000
STOREFRONT_TIMEOUT_MS = 25_000
# URL final tras redirect: /restaurantes/<store_id>-<slug>
STORE_URL_PATTERN = re.compile(r"/restaurantes/(\d+)-")

# Carpeta de evidencia (screenshots)
EVIDENCE_DIR = Path("evidencia")
EVIDENCE_DIR.mkdir(exist_ok=True)

# Thresholds para detectar problemas
MIN_HTML_SIZE_BYTES = 30_000  # Si HTML < esto, probablemente CAPTCHA o bloqueo


def _is_likely_captcha_or_blocked(html_content: str) -> bool:
    """Detecta si la página probablemente tiene CAPTCHA o está bloqueada.
    
    Heurística: si el HTML es muy pequeño (< MIN_HTML_SIZE_BYTES), probablemente
    es una página de error, CAPTCHA o bloqueo.
    """
    return len(html_content) < MIN_HTML_SIZE_BYTES


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
        log.info("[%s/%s] inicio", self.brand.brand_id, address.label)
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

        storefront["brand_id_for_log"] = self.brand.brand_id
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
        
        # Detectar CAPTCHA/bloqueos tempranamente
        await page.wait_for_timeout(2000)
        initial_html = await page.content()
        if _is_likely_captcha_or_blocked(initial_html):
            log.warning("[%s/%s] Detectado posible CAPTCHA/bloqueo (HTML: %d bytes). Reintentando...", 
                       self.brand.brand_id, address.label, len(initial_html))
            await page.wait_for_timeout(8000)
            
            # Reintento
            try:
                await page.goto(self.brand.nav_param, timeout=PAGE_TIMEOUT_MS)
                await page.wait_for_timeout(2000)
                initial_html = await page.content()
                
                if _is_likely_captcha_or_blocked(initial_html):
                    log.error("[%s/%s] CAPTCHA/bloqueo persiste (HTML: %d bytes)", 
                             self.brand.brand_id, address.label, len(initial_html))
                    screenshot_path = EVIDENCE_DIR / f"rappi_{address.label}_{self.brand.brand_id}_CAPTCHA.png"
                    await page.screenshot(path=str(screenshot_path))
                    log.warning("[%s] Screenshot CAPTCHA guardado en: %s", self.brand.brand_id, screenshot_path)
                    return None, f"rappi:captcha_or_blocked_{self.brand.brand_id}"
            except PWTimeout:
                return None, "rappi:brand_page_timeout_after_captcha"

        # Modal address_capture: aparece en brand pages de restaurantes
        # (McDonald's) pero NO en URLs de tiendas concretas (ej. OXXO Express),
        # donde la página ya carga directo el storefront usando geolocation.
        modal_present = False
        try:
            await page.wait_for_selector(
                '[data-testid="address_capture"]', timeout=8_000
            )
            modal_present = True
            # Captura del modal de dirección
            modal_screenshot_path = EVIDENCE_DIR / f"rappi_{address.label}_{self.brand.brand_id}_modal.png"
            await page.screenshot(path=str(modal_screenshot_path))
        except PWTimeout:
            log.debug("[%s] sin modal address_capture", address.label)

        if modal_present:
            try:
                await page.get_by_text(USE_LOCATION_TEXT, exact=False).click(
                    timeout=8_000
                )
            except PWTimeout:
                return None, "rappi:use_location_button_missing"

        # Esperar JSON-LD del menú. Restaurantes usan `seo-structured-schema`
        # con `hasMenu`; tiendas (retail) usan múltiples `<script type=ld+json>`
        # con `@type=ItemList → itemListElement[].item (Product)`.
        is_retail = self.brand.vertical == "retail"
        try:
            if is_retail:
                await page.wait_for_function(
                    """() => {
                        const lds = document.querySelectorAll('script[type=\"application/ld+json\"]');
                        for (const s of lds) {
                            try {
                                const j = JSON.parse(s.textContent);
                                if (j && j['@type'] === 'ItemList' && Array.isArray(j.itemListElement) && j.itemListElement.length) return true;
                            } catch {}
                        }
                        return false;
                    }""",
                    timeout=STOREFRONT_TIMEOUT_MS,
                )
            else:
                await page.wait_for_function(
                    """() => {
                        const el = document.getElementById('seo-structured-schema');
                        if (!el) return false;
                        try {
                            const j = JSON.parse(el.textContent);
                            return !!(j && j.hasMenu && j.hasMenu.hasMenuSection);
                        } catch { return false; }
                    }""",
                    timeout=STOREFRONT_TIMEOUT_MS,
                )
        except PWTimeout:
            return None, "rappi:storefront_timeout"

        # Extracción del DOM público
        try:
            payload = await page.evaluate(
                """() => {
                    const ldEl = document.getElementById('seo-structured-schema');
                    const ld = ldEl ? JSON.parse(ldEl.textContent) : null;

                    // Retail (tiendas): juntar todos los ItemList JSON-LD.
                    const itemLists = [];
                    let storeFromLd = null;
                    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
                        try {
                            const j = JSON.parse(s.textContent);
                            if (j && j['@type'] === 'ItemList' && Array.isArray(j.itemListElement)) {
                                itemLists.push(j);
                            } else if (j && j['@type'] === 'Store' && !storeFromLd) {
                                storeFromLd = j;
                            }
                        } catch {}
                    }

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
                        item_lists: itemLists,
                        store_ld: storeFromLd,
                        eta_min: eta,
                        free_shipping: freeShipping,
                        promo_text: promoBits.join(' | ') || null,
                    };
                }"""
            )
        except Exception as e:
            return None, f"rappi:dom_extract_failed:{e.__class__.__name__}"

        if not payload:
            return None, "rappi:dom_extract_empty"
        # Marcar de qué fuente sacar el menú.
        payload["is_retail"] = is_retail
        if is_retail:
            if not payload.get("item_lists"):
                return None, "rappi:item_list_missing"
        else:
            if not payload.get("jsonld"):
                return None, "rappi:jsonld_missing"
        
        # Captura de pantalla del storefront
        storefront_screenshot_path = EVIDENCE_DIR / f"rappi_{address.label}_{self.brand.brand_id}_storefront.png"
        await page.screenshot(path=str(storefront_screenshot_path))
        
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


def _iter_item_list_items(item_lists: list[dict]) -> list[MenuItem]:
    """Aplana ItemList[].itemListElement[].item (Product → offers.price).

    Estructura observada en Rappi tiendas (OXXO Express, etc.):
      ItemList { itemListElement: [ ListItem { item: Product { name, offers: { price } } } ] }
    Cada categoría visible en el storefront emite su propio ItemList script.
    """
    items: list[MenuItem] = []
    seen: set[tuple[str, float]] = set()
    for il in item_lists or []:
        for elem in il.get("itemListElement") or []:
            if not isinstance(elem, dict):
                continue
            prod = elem.get("item") or {}
            if not isinstance(prod, dict):
                continue
            name = prod.get("name") or ""
            offers = prod.get("offers") or {}
            price = offers.get("price") if isinstance(offers, dict) else None
            if not name or price is None:
                continue
            try:
                price_f = float(price)
            except (TypeError, ValueError):
                continue
            key = (name, price_f)
            if key in seen:
                continue
            seen.add(key)
            items.append(MenuItem(name_raw=name, unit_price_mxn=price_f))
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
    jsonld = storefront.get("jsonld") or {}
    item_lists = storefront.get("item_lists") or []
    store_ld = storefront.get("store_ld") or {}
    is_retail = bool(storefront.get("is_retail"))

    # Restaurantes: jsonld.hasMenu. Tiendas (retail): lista de ItemList.
    # No mezclar — los ItemList de SEO en páginas de restaurantes contienen
    # carruseles featured que ensucian el matching.
    if is_retail:
        menu = _iter_item_list_items(item_lists)
    else:
        menu = _iter_menu_items(jsonld) if jsonld else []
    log.info(
        "[%s/%s] menu items extraídos: %d",
        storefront.get("brand_id_for_log", "?"),
        address.label,
        len(menu),
    )

    eta_value = storefront.get("eta_min")
    delivery_fee = _delivery_fee(jsonld) if jsonld else 0.0
    has_free_shipping = bool(storefront.get("free_shipping"))
    if has_free_shipping:
        delivery_fee_effective = delivery_fee
        discount = round(-delivery_fee, 2)
    else:
        delivery_fee_effective = delivery_fee
        discount = 0.0

    service_fee = 0.0  # no expuesto fuera del checkout (ver compliance.md)
    promo = storefront.get("promo_text")
    store_id = _store_id_from_url(storefront.get("url") or "")
    name_source = jsonld if jsonld.get("name") else store_ld
    store_name_jsonld = (name_source.get("name") if isinstance(name_source, dict) else "") or ""
    address_node = (name_source.get("address") if isinstance(name_source, dict) else {}) or {}
    street = address_node.get("streetAddress") if isinstance(address_node, dict) else ""
    store_name = (
        f"{store_name_jsonld} - {street.split(',')[0]}".strip(" -")
        if street
        else store_name_jsonld
    )

    rows: list[ScrapeRow] = []
    matches_count = 0
    no_matches_count = 0
    for product in products:
        match = match_product(menu, product)
        if match is None:
            no_matches_count += 1
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

        matches_count += 1
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
    
    log.info(
        "[%s/%s] coincidencias: %d/%d (no encontrados: %d)",
        brand_id,
        address.label,
        matches_count,
        len(products),
        no_matches_count,
    )
    return rows


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
