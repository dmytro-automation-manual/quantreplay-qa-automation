"""Reference data as configured on the venue (REST API and database). Plain data, no behaviour.

Numbers are Decimal: REST JSON is parsed with Decimal and the DB layer casts `real` columns to numeric,
so 0.05 from REST and 0.05 from the database compare equal (no float noise).
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Venue:
    venue_id: str
    name: str | None
    engine_type: str | None
    support_tif_ioc: bool | None
    support_tif_fok: bool | None
    support_tif_day: bool | None
    include_own_orders: bool | None
    rest_port: int | None
    order_on_startup: bool | None
    cancel_on_disconnect: bool | None
    persistence_enabled: bool | None
    timezone: str | None


@dataclass(frozen=True)
class Listing:
    listing_id: int
    symbol: str
    venue_id: str
    security_type: str | None
    price_currency: str | None
    security_exchange: str | None
    isin_id: str | None
    qty_minimum: Decimal | None
    qty_maximum: Decimal | None
    qty_multiple: Decimal | None
    price_tick_size: Decimal | None
    enabled: bool | None
    random_orders_enabled: bool | None


@dataclass(frozen=True)
class PriceSeed:
    price_seed_id: int
    symbol: str
    security_type: str | None
    price_currency: str | None
    security_id: str | None
    bid_price: Decimal | None
    mid_price: Decimal | None
    offer_price: Decimal | None


@dataclass(frozen=True)
class Setting:
    key: str
    value: str | None
