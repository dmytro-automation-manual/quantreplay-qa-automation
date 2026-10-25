"""PUT /api/listings/{symbol} and /api/listings/{id}.

The change is checked in REST and in the database. The venue applies listing changes to order validation only
after a reset (see the REST API document, "Reset"), so these tests do not send orders.
Teardown (fixture `remember_listing`): the original values are restored through REST.
"""
from decimal import Decimal

import pytest
from allure import step

from framework.assertions.expect import check_fields
from framework.services.rest_api import to_listing
from test_data.instruments import AMZ, NFC, UNKNOWN_SYMBOL
from tests.support.rest import check_response

VENUE = "XETRA"


def test_update_listing_by_symbol(api, listing_table, remember_listing):
    remember_listing(AMZ.symbol, ["qtyMaximum"])
    new_max = AMZ.qty_maximum * 2
    with step(f"PUT /api/listings/{AMZ} qtyMaximum {AMZ.qty_maximum} -> {new_max}"):
        response = api.update_listing(AMZ.symbol, {"qtyMaximum": new_max})
    check_response(response, "PUT listing by symbol", status_code=200)
    with step("Check REST and database show the new value"):
        check_fields("Listing in REST", to_listing(api.get_listing(AMZ.symbol).body), {"qty_maximum": new_max})
        check_fields("Listing in DB", listing_table.get(VENUE, AMZ.symbol), {"qty_maximum": new_max})


def test_update_listing_by_id(api, listing_table, remember_listing):
    remember_listing(NFC.symbol, ["priceTickSize"])
    listing_id = api.get_listing(NFC.symbol).body["id"]
    new_tick = Decimal("0.005")
    with step(f"PUT /api/listings/{listing_id} ({NFC}) priceTickSize {NFC.tick_size} -> {new_tick}"):
        response = api.update_listing(listing_id, {"priceTickSize": new_tick})
    check_response(response, "PUT listing by id", status_code=200)
    with step("Check REST and database show the new value"):
        check_fields("Listing in REST", to_listing(api.get_listing(listing_id).body), {"price_tick_size": new_tick})
        check_fields("Listing in DB", listing_table.get(VENUE, NFC.symbol), {"price_tick_size": new_tick})


def test_update_unknown_listing_returns_404(api):
    with step(f"PUT /api/listings/{UNKNOWN_SYMBOL}"):
        response = api.update_listing(UNKNOWN_SYMBOL, {"enabled": True})
    check_response(response, "PUT unknown listing", status_code=404)


@pytest.mark.known_issue("Documented answer 'Requested update of the listing - AMZ'; "
                         "the venue answers 'Successfully updated the AMZ listing'")
def test_update_listing_message_matches_documentation(api, remember_listing):
    remember_listing(AMZ.symbol, ["qtyMaximum"])
    check_response(api.update_listing(AMZ.symbol, {"qtyMaximum": AMZ.qty_maximum}), "PUT listing",
                   status_code=200, result=f"Requested update of the listing - {AMZ.symbol}")
