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
import os
import random
import re
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

from playwright.async_api import (
    BrowserContext,
    TimeoutError as PWTimeout,
    async_playwright,
)

from .base import PlatformScraper
from .matching import MenuItem, match_product
from .models import Address, Brand, Product, ScrapeRow

log = logging.getLogger("scraper.ubereats")

PAGE_TIMEOUT_MS = 90_000  # Aumentado para resolver CAPTCHA
SEARCH_TIMEOUT_MS = 60_000  # Más tiempo en búsqueda
STORE_TIMEOUT_MS = 50_000  # Más tiempo en tienda
SEARCH_URL_TEMPLATE = "https://www.ubereats.com/mx/search?q={query}&pl={pl}"
MANUAL_UNLOCK_WAIT_MS = 180_000  # 3 minutos para resolver CAPTCHA manualmente

# Carpeta de evidencia (screenshots)
EVIDENCE_DIR = Path("evidencia")
EVIDENCE_DIR.mkdir(exist_ok=True)

# Thresholds para detectar problemas
MIN_HTML_SIZE_BYTES = 50_000  # Si HTML < esto, probablemente CAPTCHA o bloqueo


def _random_delay(min_ms: int = 1000, max_ms: int = 5000) -> int:
    """Genera delay aleatorio para simular comportamiento humano."""
    return random.randint(min_ms, max_ms)


async def _random_scroll(page, min_pixels: int = 200, max_pixels: int = 500) -> None:
    """Scroll aleatorio para simular comportamiento humano."""
    scroll_distance = random.randint(min_pixels, max_pixels)
    scroll_direction = random.choice([-1, 1])
    await page.evaluate(f"window.scrollBy(0, {scroll_distance * scroll_direction})")
    await page.wait_for_timeout(_random_delay())


def _is_likely_captcha_or_blocked(html_content: str) -> bool:
    """Detecta si la página probablemente tiene CAPTCHA o está bloqueada.
    
    Heurística: si el HTML es muy pequeño (< MIN_HTML_SIZE_BYTES), probablemente
    es una página de error, CAPTCHA o bloqueo.
    """
    return len(html_content) < MIN_HTML_SIZE_BYTES

_DEFAULT_BRAND = Brand(
    brand_id="mcdonalds",
    platform="ubereats",
    vertical="fast_food",
    nav_strategy="search_query",
    nav_param="mcdonalds",
)


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

    def __init__(self, brand: Brand | None = None, headless: bool = True, manual_captcha_unlock: bool = False):
        self.brand = brand or _DEFAULT_BRAND
        self.headless = headless
        self.manual_captcha_unlock = manual_captcha_unlock
        # Filtro de anchors: /store/<prefix>...
        self._anchor_prefix = self.brand.nav_param.lower()

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
                _empty_row(
                    address,
                    product,
                    notes=notes or "ubereats:no_store",
                    brand_id=self.brand.brand_id,
                )
                for product in products
            ]
        return _rows_from_capture(captured, address, products, self.brand.brand_id)

    async def _capture(
        self,
        ctx: BrowserContext,
        address: Address,
    ) -> tuple[dict[str, Any] | None, str | None]:
        pl = _build_pl(address)
        search_url = SEARCH_URL_TEMPLATE.format(
            query=quote(self.brand.nav_param, safe=""),
            pl=quote(pl, safe=""),
        )

        page = await ctx.new_page()
        try:
            await page.goto(
                search_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded"
            )
        except PWTimeout:
            return None, "ubereats:search_timeout"
        
        # Delay aleatorio después de navegar
        await page.wait_for_timeout(_random_delay(8000, 12000))
        
        # Scroll aleatorio para simular comportamiento humano
        try:
            await _random_scroll(page)
        except Exception as e:
            log.debug("[%s] Scroll falló (puede no haber contenido): %s", self.brand.brand_id, e)
        
        debug_html = await page.content()
        if _is_likely_captcha_or_blocked(debug_html):
            log.warning("[%s] Detectado posible CAPTCHA/bloqueo (HTML: %d bytes). Reintentando...", 
                       self.brand.brand_id, len(debug_html))
            
            # Si desbloqueo manual está habilitado, esperar a que se resuelva
            if self.manual_captcha_unlock:
                log.warning("[%s] Esperando resolución manual de CAPTCHA (3 minutos)...", self.brand.brand_id)
                await page.wait_for_timeout(MANUAL_UNLOCK_WAIT_MS)
                
                # Recargar después de que el usuario resuelva
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                    await page.wait_for_timeout(_random_delay(5000, 8000))
                    debug_html = await page.content()
                    
                    if _is_likely_captcha_or_blocked(debug_html):
                        log.error("[%s] CAPTCHA persiste incluso después de intervención manual", self.brand.brand_id)
                        screenshot_path = EVIDENCE_DIR / f"ubereats_{address.label}_{self.brand.brand_id}_CAPTCHA_MANUAL_FAILED.png"
                        await page.screenshot(path=str(screenshot_path))
                        return None, f"ubereats:captcha_or_blocked_{self.brand.brand_id}"
                except PWTimeout:
                    return None, "ubereats:search_timeout_after_manual_unlock"
            else:
                # Reintento automático sin intervención manual
                await page.wait_for_timeout(_random_delay(8000, 12000))
                
                try:
                    await page.goto(
                        search_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded"
                    )
                    await page.wait_for_timeout(_random_delay(8000, 12000))
                    debug_html = await page.content()
                    
                    if _is_likely_captcha_or_blocked(debug_html):
                        log.error("[%s] CAPTCHA/bloqueo persiste después de reintento (HTML: %d bytes)", 
                                 self.brand.brand_id, len(debug_html))
                        screenshot_path = EVIDENCE_DIR / f"ubereats_{address.label}_{self.brand.brand_id}_CAPTCHA.png"
                        await page.screenshot(path=str(screenshot_path))
                        log.warning("[%s] Screenshot CAPTCHA guardado en: %s", self.brand.brand_id, screenshot_path)
                        return None, f"ubereats:captcha_or_blocked_{self.brand.brand_id}"
                except PWTimeout:
                    return None, "ubereats:search_timeout_after_captcha"
        
        # Captura de pantalla del search
        screenshot_path = EVIDENCE_DIR / f"ubereats_{address.label}_{self.brand.brand_id}_search.png"
        await page.screenshot(path=str(screenshot_path))
        
        # Scroll aleatorio antes de buscar store
        try:
            await _random_scroll(page)
        except Exception:
            pass
        
        # En lugar de esperar selector (que puede fallar por remontaje del DOM),
        # intentamos evaluar directamente — el DOM ya está hidratado según el debug.
        prefix = self._anchor_prefix
        
        first = None
        for attempt in range(3):  # Hasta 3 intentos con delays aleatorios
            await page.wait_for_timeout(_random_delay(2000, 4000))
            first = await page.evaluate(
                f"""() => {{
                    const anchors = [...document.querySelectorAll('a[href*=\"/store/{prefix}\"]')];
                    const seen = new Set();
                    for (const a of anchors) {{
                        if (/\\/store\\/{prefix}-dummy/i.test(a.href)) continue;
                        const base = a.href.split('?')[0];
                        if (seen.has(base)) continue;
                        seen.add(base);
                        let node = a.parentElement;
                        let eta = null;
                        for (let i = 0; i < 15 && node; i++) {{
                            const t = node.innerText || '';
                            const m = t.match(/(\\d+)\\s*min/);
                            if (m) {{ eta = parseInt(m[1], 10); break; }}
                            node = node.parentElement;
                        }}
                        const name = (a.innerText || '').split('\\n')[0].trim();
                        return {{storeUrl: base, eta, name}};
                    }}
                    return null;
                }}"""
            )
            if first and first.get("storeUrl"):
                log.debug("[%s] Store encontrado en intento %d", self.brand.brand_id, attempt + 1)
                break
            log.debug("[%s] Reintentando búsqueda de store (intento %d)...", self.brand.brand_id, attempt + 1)
        
        if not first or not first.get("storeUrl"):
            return None, f"ubereats:no_results_for_{self._anchor_prefix}"

        store_url = f"{first['storeUrl']}?pl={quote(pl, safe='')}"
        await page.wait_for_timeout(_random_delay(1000, 3000))  # Pausa aleatoria antes de ir a tienda
        try:
            await page.goto(
                store_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded"
            )
        except PWTimeout:
            return None, "ubereats:store_timeout"
        
        await page.wait_for_timeout(_random_delay(5000, 10000))  # Pausa aleatoria después de cargar tienda
        
        # Scroll aleatorio en el storefront
        try:
            await _random_scroll(page)
        except Exception:
            pass
        
        # Captura de pantalla del storefront
        storefront_screenshot_path = EVIDENCE_DIR / f"ubereats_{address.label}_{self.brand.brand_id}_storefront.png"
        await page.screenshot(path=str(storefront_screenshot_path))

        # Restaurantes exponen hasMenu; tiendas (OXXO) NO. La CSP de las
        # storefront pages de tiendas bloquea wait_for_function (unsafe-eval),
        # así que para retail simplemente esperamos un tiempo fijo y validamos
        # después en _rows_from_capture si hay productos.
        is_retail = self.brand.vertical == "retail"
        if is_retail:
            await page.wait_for_timeout(_random_delay(3000, 7000))
        else:
            try:
                await page.wait_for_function(
                    """() => {
                        const ss = document.querySelectorAll('script[type=\"application/ld+json\"]');
                        for (const s of ss) {
                            try {
                                const j = JSON.parse(s.textContent);
                                const t = j && j['@type'];
                                if (t && /Restaurant|GroceryStore|Store/.test(t) && j.hasMenu) return true;
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
                        const t = j && j['@type'];
                        if (t && /Restaurant|GroceryStore|Store/.test(t)) { restaurant = j; break; }
                    } catch (e) {}
                }
                // Retail: tiendas tipo OXXO no exponen hasMenu. Parseamos
                // pares "$<precio>\\n<nombre>" del innerText como fallback.
                const innerProducts = [];
                {
                    const body = document.body.innerText || '';
                    const lines = body.split('\\n');
                    const seen = new Set();
                    for (let i = 0; i < lines.length - 1; i++) {
                        const m = lines[i].match(/^\\$\\s*([0-9]+(?:\\.[0-9]+)?)\\s*$/);
                        if (!m) continue;
                        const price = parseFloat(m[1]);
                        const name = (lines[i+1] || '').trim();
                        if (!name || name.length > 150 || /^\\$/.test(name)) continue;
                        const key = name.toLowerCase() + '|' + price;
                        if (seen.has(key)) continue;
                        seen.add(key);
                        innerProducts.push({name, price});
                        if (innerProducts.length >= 600) break;
                    }
                }

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
                    innerProducts,
                    deliveryFeeRaw,
                    deliveryFreeWithUberOne,
                    deliveryFreeUnconditional,
                    promoText: promoBits.join(' | ') || null,
                };
            }"""
        )
        if not payload:
            return None, "ubereats:dom_extract_failed"
        if not payload.get("restaurant") and not payload.get("innerProducts"):
            return None, "ubereats:no_menu_or_products"

        # ETA viene del search card; inyectamos
        payload["eta_min"] = first.get("eta")
        payload["store_name_hint"] = first.get("name")
        return payload, None


def _empty_row(
    address: Address, product: Product, notes: str, brand_id: str
) -> ScrapeRow:
    return ScrapeRow(
        platform="ubereats",
        address_id=address.address_id,
        address_label=address.label,
        product_sku=product.sku,
        collection_method="playwright",
        available=False,
        notes=notes,
        brand_id=brand_id,
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
    brand_id: str,
) -> list[ScrapeRow]:
    restaurant = captured.get("restaurant") or {}
    menu = _iter_menu_items(restaurant) if restaurant else []
    log.info("[%s] JSON-LD restaurant: %s", brand_id, bool(restaurant))
    log.info("[%s] Menú capturado: %d items", brand_id, len(menu))
    
    # Fallback retail: innerProducts del DOM (pares $precio\nname).
    if not menu:
        inner_products = captured.get("innerProducts") or []
        log.info("[%s] Intentando fallback retail: %d innerProducts", brand_id, len(inner_products))
        for p in inner_products:
            try:
                menu.append(
                    MenuItem(name_raw=p["name"], unit_price_mxn=float(p["price"]))
                )
            except (KeyError, TypeError, ValueError):
                continue

    eta_value = captured.get("eta_min")
    delivery_fee_raw = captured.get("deliveryFeeRaw")
    free_uber_one = bool(captured.get("deliveryFreeWithUberOne"))
    free_unconditional = bool(captured.get("deliveryFreeUnconditional"))
    promo = captured.get("promoText")
    store_name = (restaurant.get("name") if restaurant else None) or captured.get(
        "store_name_hint"
    )
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
    matches_count = 0
    no_matches_count = 0
    for product in products:
        match = match_product(menu, product)
        if match is None:
            no_matches_count += 1
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
                    brand_id=brand_id,
                )
            )
            continue

        matches_count += 1
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
