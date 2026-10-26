"""Read access to the simulator tables (schema `sim`, created by Liquibase), one class per table.

Layer rule: depends on an injected client with query(); returns models; makes no assertions.
`real` columns are cast to numeric in SQL, so 0.05 is read as Decimal('0.05'), not 0.0500000007.
"""
from typing import Protocol

from framework.models.reference_data import Listing, PriceSeed, Setting, Venue


class Db(Protocol):
    def query(self, sql: str, params: tuple = ()) -> list[dict]: ...


class VenueTable:
    def __init__(self, db: Db):
        self._db = db

    def get(self, venue_id: str) -> Venue | None:
        rows = self._db.query(
            """select venue_id, name, engine_type, support_tif_ioc, support_tif_fok, support_tif_day,
                      include_own_orders, rest_port, order_on_startup, cancel_on_disconnect,
                      persistence_enabled, timezone
               from sim.venue where venue_id = %s""", (venue_id,))
        return Venue(**rows[0]) if rows else None


class ListingTable:
    _COLUMNS = """listing_id, symbol, venue_id, security_type, price_currency, fx_base_currency, security_exchange,
                  isin_id,
                  qty_minimum::numeric as qty_minimum, qty_maximum::numeric as qty_maximum,
                  qty_multiple::numeric as qty_multiple, price_tick_size::numeric as price_tick_size,
                  enabled, random_orders_enabled"""

    def __init__(self, db: Db):
        self._db = db

    def all(self, venue_id: str) -> list[Listing]:
        rows = self._db.query(f"select {self._COLUMNS} from sim.listing where venue_id = %s order by listing_id",
                              (venue_id,))
        return [Listing(**r) for r in rows]

    def get(self, venue_id: str, symbol: str) -> Listing | None:
        rows = self._db.query(f"select {self._COLUMNS} from sim.listing where venue_id = %s and symbol = %s",
                              (venue_id, symbol))
        return Listing(**rows[0]) if rows else None


class PriceSeedTable:
    def __init__(self, db: Db):
        self._db = db

    def all(self) -> list[PriceSeed]:
        rows = self._db.query(
            """select price_seed_id, symbol, security_type, price_currency, security_id,
                      bid_price::numeric as bid_price, mid_price::numeric as mid_price,
                      offer_price::numeric as offer_price
               from sim.price_seed order by price_seed_id""")
        return [PriceSeed(**r) for r in rows]


class SettingTable:
    def __init__(self, db: Db):
        self._db = db

    def all(self) -> list[Setting]:
        return [Setting(**r) for r in self._db.query("select key, value from sim.setting order by key")]


class DatabaseState:
    """Whole-content fingerprint of the configuration tables, used to prove that tests leave no trace."""

    TABLES = ("venue", "listing", "price_seed", "setting", "data_source", "column_mapping",
              "data_source_listing", "listing_random_price_source", "market_phase")

    def __init__(self, db: Db):
        self._db = db

    def capture(self) -> dict[str, list[dict]]:
        return {t: sorted(self._db.query(f"select * from sim.{t}"), key=repr) for t in self.TABLES}
