"""Simulator REST API (QuantReplay "REST API" document): one method per documented endpoint.

Layer rule: depends on an injected HTTP client with request(); maps JSON to models; makes no assertions.
JSON numbers are parsed as Decimal so prices and ticks compare exactly.
"""
import json
from urllib.parse import quote
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from framework.models.reference_data import Listing, PriceSeed, Setting, Venue


class Http(Protocol):
    def request(self, method: str, path: str, json: dict | None = None): ...


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    body: Any                 # parsed JSON (Decimal numbers) or None
    text: str

    @property
    def result(self) -> str | None:
        """The `result` message the simulator puts into every command / error answer."""
        return self.body.get("result") if isinstance(self.body, dict) else None


class SimulatorApi:
    def __init__(self, http: Http):
        self._http = http

    # --- settings --------------------------------------------------------------------------------
    def get_settings(self) -> ApiResponse:
        return self._call("GET", "/settings")

    def update_settings(self, settings: list[dict]) -> ApiResponse:
        return self._call("PUT", "/settings", {"settings": settings})

    # --- venues ----------------------------------------------------------------------------------
    def get_venues(self) -> ApiResponse:
        return self._call("GET", "/venues")

    def get_venue(self, venue_id: str) -> ApiResponse:
        return self._call("GET", f"/venues/{venue_id}")

    def update_venue(self, venue_id: str, changes: dict) -> ApiResponse:
        return self._call("PUT", f"/venues/{venue_id}", changes)

    # --- listings --------------------------------------------------------------------------------
    def get_listings(self) -> ApiResponse:
        return self._call("GET", "/listings")

    def get_listing(self, key: str | int) -> ApiResponse:
        """key = listing id or symbol (FX symbols contain '/', sent as %2F)."""
        return self._call("GET", f"/listings/{_path(key)}")

    def update_listing(self, key: str | int, changes: dict) -> ApiResponse:
        return self._call("PUT", f"/listings/{_path(key)}", changes)

    # --- price seeds -----------------------------------------------------------------------------
    def get_price_seeds(self) -> ApiResponse:
        return self._call("GET", "/priceseeds")

    def get_price_seed(self, seed_id: int) -> ApiResponse:
        return self._call("GET", f"/priceseeds/{seed_id}")

    def add_price_seed(self, seed: dict) -> ApiResponse:
        return self._call("POST", "/priceseeds", seed)

    def update_price_seed(self, seed_id: int, changes: dict) -> ApiResponse:
        return self._call("PUT", f"/priceseeds/{seed_id}", changes)

    def delete_price_seed(self, seed_id: int) -> ApiResponse:
        return self._call("DELETE", f"/priceseeds/{seed_id}")

    # --- datasources -----------------------------------------------------------------------------
    def get_datasources(self) -> ApiResponse:
        return self._call("GET", "/datasources")

    def get_datasource(self, datasource_id: int) -> ApiResponse:
        return self._call("GET", f"/datasources/{datasource_id}")

    # --- administrative commands -----------------------------------------------------------------
    def get_venue_status(self, venue_id: str | None = None) -> ApiResponse:
        return self._call("GET", f"/venuestatus/{venue_id}" if venue_id else "/venuestatus")

    def get_all_venue_status(self) -> ApiResponse:
        return self._call("GET", "/allvenuestatus")

    def get_generator_status(self, venue_id: str) -> ApiResponse:
        return self._call("GET", f"/genstatus/{venue_id}")

    def start_generator(self, venue_id: str) -> ApiResponse:
        return self._call("POST", f"/genstart/{venue_id}")

    def stop_generator(self, venue_id: str) -> ApiResponse:
        return self._call("POST", f"/genstop/{venue_id}")

    def halt(self, venue_id: str, allow_cancels: bool) -> ApiResponse:
        return self._call("POST", f"/halt/{venue_id}", {"allowCancels": allow_cancels})

    def resume(self, venue_id: str) -> ApiResponse:
        return self._call("POST", f"/resume/{venue_id}")

    def reset(self, venue_id: str) -> ApiResponse:
        """Reload the configuration from the database; drops FIX and REST connections for a few seconds."""
        return self._call("POST", f"/reset/{venue_id}")

    # --- internals -------------------------------------------------------------------------------
    def _call(self, method: str, path: str, body: dict | None = None) -> ApiResponse:
        response = self._http.request(method, path, json=body)
        try:
            parsed = json.loads(response.text, parse_float=Decimal) if response.text else None
        except json.JSONDecodeError:
            parsed = None
        return ApiResponse(status_code=response.status_code, body=parsed, text=response.text)


def _path(key: str | int) -> str:
    return quote(str(key), safe="")


# --- JSON -> models --------------------------------------------------------------------------------
def to_venue(body: dict) -> Venue:
    return Venue(venue_id=body["id"], name=body.get("name"), engine_type=body.get("engineType"),
                 support_tif_ioc=body.get("supportTifIoc"), support_tif_fok=body.get("supportTifFok"),
                 support_tif_day=body.get("supportTifDay"), include_own_orders=body.get("includeOwnOrders"),
                 rest_port=body.get("restPort"), order_on_startup=body.get("orderOnStartup"),
                 cancel_on_disconnect=body.get("cancelOnDisconnect"),
                 persistence_enabled=body.get("persistenceEnabled"), timezone=body.get("timezone"))


def _dec(value) -> Decimal | None:
    return Decimal(value) if value is not None else None


def to_listing(body: dict) -> Listing:
    return Listing(listing_id=body["id"], symbol=body["symbol"], venue_id=body["venueId"],
                   security_type=body.get("securityType"), price_currency=body.get("priceCurrency"),
                   fx_base_currency=body.get("fxBaseCurrency"), security_exchange=body.get("securityExchange"),
                   isin_id=body.get("isinId"),
                   qty_minimum=_dec(body.get("qtyMinimum")), qty_maximum=_dec(body.get("qtyMaximum")),
                   qty_multiple=_dec(body.get("qtyMultiple")), price_tick_size=_dec(body.get("priceTickSize")),
                   enabled=body.get("enabled"), random_orders_enabled=body.get("randomOrdersEnabled"))


def to_price_seed(body: dict) -> PriceSeed:
    return PriceSeed(price_seed_id=body["id"], symbol=body["symbol"], security_type=body.get("securityType"),
                     price_currency=body.get("priceCurrency"), security_id=body.get("securityId"),
                     bid_price=_dec(body.get("bidPrice")), mid_price=_dec(body.get("midPrice")),
                     offer_price=_dec(body.get("offerPrice")))


def to_setting(body: dict) -> Setting:
    return Setting(key=body["key"], value=body.get("value"))
