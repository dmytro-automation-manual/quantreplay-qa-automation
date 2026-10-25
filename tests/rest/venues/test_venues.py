"""GET / PUT /api/venues. The test venue must support every TimeInForce the tests use and start clean."""
import pytest
from allure import step

from framework.assertions.expect import check_fields
from framework.services.rest_api import to_venue
from tests.support.rest import check_response

VENUE = "XETRA"
UNKNOWN_VENUE = "NOSUCHVENUE"


def test_get_all_venues_contains_test_venue(api):
    with step("GET /api/venues"):
        response = api.get_venues()
    check_response(response, "GET /api/venues", status_code=200)
    check_fields("Venue ids", {"ids": [v["id"] for v in response.body["venues"]]}, {"ids": [VENUE]})


@pytest.mark.smoke
def test_test_venue_configuration(api):
    """Matching engine, all TIFs supported, own orders match, no auto start of the generator, no persistence."""
    with step(f"GET /api/venues/{VENUE}"):
        response = api.get_venue(VENUE)
    check_response(response, f"GET /api/venues/{VENUE}", status_code=200)
    check_fields(f"Venue {VENUE}", to_venue(response.body), {
        "venue_id": VENUE, "name": VENUE, "engine_type": "Matching",
        "support_tif_ioc": True, "support_tif_fok": True, "support_tif_day": True,
        "include_own_orders": True, "rest_port": 9050, "order_on_startup": False,
        "persistence_enabled": False, "cancel_on_disconnect": False, "timezone": "UTC"})


def test_update_venue(api, venue_table, undo):
    original = api.get_venue(VENUE).body["name"]
    undo.push(f"restore venue name '{original}'", lambda: api.update_venue(VENUE, {"name": original}))
    new_name = "XETRA QA"
    with step(f"PUT /api/venues/{VENUE} name -> '{new_name}'"):
        response = api.update_venue(VENUE, {"name": new_name})
    check_response(response, "PUT venue", status_code=200)
    with step("Check REST and database show the new name"):
        check_fields("Venue in REST", to_venue(api.get_venue(VENUE).body), {"name": new_name})
        check_fields("Venue in DB", venue_table.get(VENUE), {"name": new_name})


def test_unknown_venue_returns_404(api):
    check_response(api.get_venue(UNKNOWN_VENUE), "GET unknown venue", status_code=404)
    check_response(api.update_venue(UNKNOWN_VENUE, {"name": "x"}), "PUT unknown venue", status_code=404)


@pytest.mark.known_issue("Documented 404 text 'No such venue'; the venue answers "
                         "'Can not resolve a single Venue by a given key'")
def test_unknown_venue_message_matches_documentation(api):
    check_response(api.get_venue(UNKNOWN_VENUE), "GET unknown venue", status_code=404, result="No such venue")
