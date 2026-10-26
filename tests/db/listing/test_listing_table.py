"""Table sim.listing: the trading parameters stored for each instrument.

1. The database holds the reference values (test_data/instruments.py) - the test data itself is right.
2. The REST API exposes exactly what is stored - no transformation or rounding on the way.
"""
import pytest
from allure import step

from framework.assertions.expect import check_fields
from framework.services.rest_api import to_listing

TRADING_FIELDS = ("listing_id", "symbol", "venue_id", "security_type", "price_currency", "fx_base_currency",
                  "security_exchange",
                  "isin_id", "qty_minimum", "qty_maximum", "qty_multiple", "price_tick_size", "enabled",
                  "random_orders_enabled")


def test_table_holds_exactly_the_reference_instruments(market, listing_table):
    rows = listing_table.all(market.venue_id)
    check_fields("Symbols in sim.listing", {"symbols": sorted(r.symbol for r in rows)},
                 {"symbols": sorted(i.symbol for i in market.instruments)})


@pytest.mark.smoke
def test_row_matches_reference_instrument(market, listing_table, instrument):
    with step(f"Read sim.listing row of {instrument}"):
        row = listing_table.get(market.venue_id, instrument.symbol)
    check_fields(f"sim.listing {instrument}", row, {
        "security_type": instrument.security_type, "price_currency": instrument.currency,
        "fx_base_currency": instrument.fx_base_currency,
        "security_exchange": instrument.security_exchange, "isin_id": instrument.isin,
        "price_tick_size": instrument.tick_size, "qty_minimum": instrument.qty_minimum,
        "qty_maximum": instrument.qty_maximum, "qty_multiple": instrument.qty_multiple, "enabled": True})


@pytest.mark.smoke
def test_rest_listing_equals_database_row(market, api, listing_table, instrument):
    with step(f"Read {instrument} from REST and from sim.listing"):
        api_listing = to_listing(api.get_listing(instrument.symbol).body)
        row = listing_table.get(market.venue_id, instrument.symbol)
    check_fields(f"REST listing {instrument} vs sim.listing", api_listing,
                 {field: getattr(row, field) for field in TRADING_FIELDS})
