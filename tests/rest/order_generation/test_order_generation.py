"""POST /api/genstart, /api/genstop and GET /api/genstatus (random order generator).

Precondition (session): the generator is stopped and the books are empty.
Teardown: the generator is stopped and the venue is reset - random orders left in the books are removed
(persistence is disabled on the test venue), so the next test starts with empty books again.
"""
import pytest
from allure import step

from framework.assertions.expect import check_true
from tests.support.isolation import wait_until
from tests.support.rest import check_response

VENUE = "XETRA"


@pytest.fixture
def generator_cleanup(api, venue, undo):
    undo.push("reset venue: remove random orders from the books", venue.reset)
    undo.push("stop the generator", lambda: api.stop_generator(VENUE))


def test_generator_is_stopped_before_tests(api):
    check_response(api.get_generator_status(VENUE), "GET genstatus", status_code=200, result="Stopped")


def test_start_and_stop_generator(api, market_data, generator_cleanup):
    with step(f"POST /api/genstart/{VENUE}"):
        response = api.start_generator(VENUE)
    check_response(response, "POST genstart", status_code=200)
    check_response(api.get_generator_status(VENUE), "GET genstatus after start", status_code=200, result="Running")

    with step("Check random orders appear in the books"):
        wait_until(lambda: market_data.snapshot("AMZ").entries, timeout=10, what="random AMZ orders")
        check_true("AMZ book is not empty", bool(market_data.snapshot("AMZ").entries))

    with step(f"POST /api/genstop/{VENUE}"):
        response = api.stop_generator(VENUE)
    check_response(response, "POST genstop", status_code=200)
    check_response(api.get_generator_status(VENUE), "GET genstatus after stop", status_code=200, result="Stopped")


@pytest.mark.known_issue("Documented status 'NotRunning'; the venue answers 'Stopped'")
def test_stopped_status_matches_documentation(api):
    check_response(api.get_generator_status(VENUE), "GET genstatus", status_code=200, result="NotRunning")


@pytest.mark.known_issue("Documented 'Random orders generator started/stopped successfully'; "
                         "the venue answers 'Generator was started' / 'Generator was stopped'")
def test_start_stop_messages_match_documentation(api, generator_cleanup):
    check_response(api.start_generator(VENUE), "POST genstart", status_code=200,
                   result="Random orders generator started successfully")
    check_response(api.stop_generator(VENUE), "POST genstop", status_code=200,
                   result="Random orders generator stopped successfully")
