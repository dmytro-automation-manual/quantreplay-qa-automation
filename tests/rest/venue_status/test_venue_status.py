"""GET /api/venuestatus, /api/venuestatus/{venueId}, /api/allvenuestatus."""
from allure import step

from framework.assertions.expect import PRESENT, check_fields
from tests.support.rest import check_response

VENUE = "XETRA"


def test_venue_status_of_test_venue(api):
    with step(f"GET /api/venuestatus/{VENUE}"):
        response = api.get_venue_status(VENUE)
    check_response(response, "GET venue status", status_code=200)
    check_fields("Venue status", response.body, {"id": VENUE, "name": VENUE, "startTime": PRESENT,
                                                 "version": PRESENT, "sessionSettings": PRESENT})


def test_venue_status_of_current_venue_equals_explicit_one(api):
    current, explicit = api.get_venue_status(), api.get_venue_status(VENUE)
    check_response(current, "GET /api/venuestatus", status_code=200)
    check_fields("Current venue = XETRA", current.body, {"id": explicit.body["id"],
                                                          "startTime": explicit.body["startTime"]})


def test_all_venue_status_contains_test_venue(api):
    with step("GET /api/allvenuestatus"):
        response = api.get_all_venue_status()
    check_response(response, "GET /api/allvenuestatus", status_code=200)
    check_fields("Venues in allvenuestatus", {"ids": [v["id"] for v in response.body["venuestatus"]]},
                 {"ids": [VENUE]})
