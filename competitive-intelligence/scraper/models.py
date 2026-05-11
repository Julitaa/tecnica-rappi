from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

Platform = Literal["rappi", "ubereats", "didi"]
CollectionMethod = Literal["api", "playwright"]
ProductSku = Literal[
    "big_mac",
    "mcombo_bigmac_med",
    "mcnuggets_10",
    "cocacola_500ml",
    "agua_1l",
]


@dataclass(frozen=True)
class Address:
    address_id: int
    label: str
    street: str
    lat: float
    lng: float
    zone_type: str


@dataclass(frozen=True)
class Product:
    sku: ProductSku
    canonical_name: str
    vertical: str
    search_keywords: tuple[str, ...]
    price_min_mxn: float
    price_max_mxn: float
    exclude_keywords: tuple[str, ...] = ()


@dataclass
class ScrapeRow:
    platform: Platform
    address_id: int
    address_label: str
    product_sku: ProductSku
    collection_method: CollectionMethod
    available: bool
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    product_name_raw: Optional[str] = None
    unit_price_mxn: Optional[float] = None
    delivery_fee_mxn: Optional[float] = None
    service_fee_mxn: Optional[float] = None
    discount_mxn: Optional[float] = None
    total_final_mxn: Optional[float] = None
    eta_min: Optional[int] = None
    eta_min_low: Optional[int] = None
    eta_min_high: Optional[int] = None
    promo_text: Optional[str] = None
    notes: Optional[str] = None
    scrape_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)
