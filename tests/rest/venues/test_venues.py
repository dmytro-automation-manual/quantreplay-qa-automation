"""GET / PUT /api/venues. The test venue must support every TimeInForce the tests use and start clean.

Unknown venue: the venue's text is checked (the REST API document writes 'No such venue').
"""
import pytest
from allure import step

from framework.assertions.expect import check_fields
from framework.services.rest_api import to_venue
from test_data.markets import MARKETS
from tests.support.rest import check_response

UNKNOWN_VENUE = "NOSUCHVENUE"


def test_get_all_venues_contains_every_test_venue(api):
    with step("GET /api/venues"):
        response = api.get_venues()
    check_response(response, "GET /api/venues", status_code=200)
    check_fields("Venue ids", {"ids": sorted(v["id"] for v in response.body["venues"])},
                 {"ids": sorted(m.venue_id for m in MARKETS)})


@pytest.mark.smoke
def test_test_venue_configuration(market, api):
    """Matching engine, all TIFs supported, own orders match, no auto start of the generator, no persistence."""
    with step(f"GET /api/venues/{market.venue_id}"):
        response = api.get_venue(market.venue_id)
    check_response(response, f"GET /api/venues/{market.venue_id}", status_code=200)
    check_fields(f"Venue {market.venue_id}", to_venue(response.body), {
        "venue_id": market.venue_id, "name": market.venue_id, "engine_type": "Matching",
        "support_tif_ioc": True, "support_tif_fok": True, "support_tif_day": True,
        "include_own_orders": True, "rest_port": market.rest_port, "order_on_startup": False,
        "persistence_enabled": False, "cancel_on_disconnect": False, "timezone": market.timezone})


def test_update_venue(market, api, venue_table, undo):
    original = api.get_venue(market.venue_id).body["name"]
    undo.push(f"restore venue name '{original}'", lambda: api.update_venue(market.venue_id, {"name": original}))
    new_name = f"{market.venue_id} QA"
    with step(f"PUT /api/venues/{market.venue_id} name -> '{new_name}'"):
        response = api.update_venue(market.venue_id, {"name": new_name})
    check_response(response, "PUT venue", status_code=200)
    with step("Check REST and database show the new name"):
        check_fields("Venue in REST", to_venue(api.get_venue(market.venue_id).body), {"name": new_name})
        check_fields("Venue in DB", venue_table.get(market.venue_id), {"name": new_name})


def test_unknown_venue_returns_404(api):
    check_response(api.get_venue(UNKNOWN_VENUE), "GET unknown venue", status_code=404,
                   result="Can not resolve a single Venue by a given key")
    check_response(api.update_venue(UNKNOWN_VENUE, {"name": "x"}), "PUT unknown venue", status_code=404)
