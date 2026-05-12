"""Chequeo de robots.txt por plataforma.

El brief técnico pide "respetar robots.txt cuando sea posible". Para cada
plataforma chequeamos antes de scrapear si la URL de navegación pública está
permitida para nuestro User-Agent. Si no, skipeamos la plataforma y lo
dejamos documentado.

No es un crawler agresivo: el browser real (Playwright) navega a URLs
públicas como lo haría un usuario. Esto verifica esa premisa formalmente.
"""

from __future__ import annotations

import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class RobotsResult:
    url: str
    allowed: bool
    robots_url: str
    fetched: bool  # True si pudimos descargar robots.txt; False si 404/timeout


def check_url(nav_url: str, user_agent: str = DEFAULT_UA) -> RobotsResult:
    """Descarga robots.txt del host de `nav_url` y verifica permiso.

    Si robots.txt no existe o falla la descarga, asume permitido
    (comportamiento estándar definido por RFC 9309 §2.3).
    """
    parsed = urlparse(nav_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()

    try:
        resp = httpx.get(
            robots_url,
            timeout=10.0,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )
        if resp.status_code == 200 and resp.text.strip():
            rp.parse(resp.text.splitlines())
            return RobotsResult(
                url=nav_url,
                allowed=rp.can_fetch(user_agent, nav_url),
                robots_url=robots_url,
                fetched=True,
            )
        # 404 / vacío → permitido por defecto
        return RobotsResult(url=nav_url, allowed=True, robots_url=robots_url, fetched=False)
    except (httpx.HTTPError, OSError):
        return RobotsResult(url=nav_url, allowed=True, robots_url=robots_url, fetched=False)
