"""GET /api/listings, /api/listings/{id}, /api/listings/{symbol}.

The trading parameters must equal the reference instruments (test_data/instruments.py):
a wrong tick size or quantity limit on a live venue means wrong prices or fat-finger orders getting through.
"""
import pytest
from allure import step

from framework.assertions.expect import check_fields, check_true
from framework.services.rest_api import to_listing
from test_data.instruments import UNKNOWN_SYMBOL
from tests.support.rest import check_response



def test_get_all_listings_returns_every_instrument_of_the_venue(market, api):
    with step("GET /api/listings"):
        response = api.get_listings()
    check_response(response, "GET /api/listings", status_code=200)
    with step("Check the venue lists exactly the reference instruments"):
        symbols = sorted(item["symbol"] for item in response.body["listings"]
                         if item["venueId"] == market.venue_id)
        check_fields("Listings of the venue", {"symbols": symbols},
                     {"symbols": sorted(i.symbol for i in market.instruments)})


@pytest.mark.smoke
def test_listing_trading_parameters_match_reference(market, api, instrument):
    with step(f"GET /api/listings/{instrument}"):
        response = api.get_listing(instrument.symbol)
    check_response(response, f"GET /api/listings/{instrument}", status_code=200)
    with step("Check tick size, quantity limits and identifiers"):
        check_fields(f"Listing {instrument}", to_listing(response.body), {
            "symbol": instrument.symbol, "venue_id": market.venue_id, "security_type": instrument.security_type,
            "price_currency": instrument.currency, "fx_base_currency": instrument.fx_base_currency,
            "security_exchange": instrument.security_exchange,
            "isin_id": instrument.isin, "price_tick_size": instrument.tick_size,
            "qty_minimum": instrument.qty_minimum, "qty_maximum": instrument.qty_maximum,
            "qty_multiple": instrument.qty_multiple, "enabled": True})


def test_listing_by_id_equals_listing_by_symbol(api, instrument):
    by_symbol = api.get_listing(instrument.symbol)
    with step(f"GET /api/listings/{by_symbol.body['id']} (id of {instrument})"):
        by_id = api.get_listing(by_symbol.body["id"])
    check_response(by_id, "GET listing by id", status_code=200)
    check_true("Same listing by id and by symbol", by_id.body == by_symbol.body,
               f"by id: {by_id.body} / by symbol: {by_symbol.body}")


def test_unknown_listing_returns_404(api):
    with step(f"GET /api/listings/{UNKNOWN_SYMBOL}"):
        response = api.get_listing(UNKNOWN_SYMBOL)
    check_response(response, "GET unknown listing", status_code=404)


@pytest.mark.known_issue("Documented 404 text 'No such listing'; the venue answers "
                         "'Can not resolve a single Listing by a given key'")
def test_unknown_listing_message_matches_documentation(api):
    check_response(api.get_listing(UNKNOWN_SYMBOL), "GET unknown listing", status_code=404,
                   result="No such listing")
