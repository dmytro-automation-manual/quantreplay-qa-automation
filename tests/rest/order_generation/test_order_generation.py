"""POST /api/genstart, /api/genstop and GET /api/genstatus (random order generator).

Precondition (session): the generator is stopped and the books are empty.
Random orders are off for every test instrument by default (sim.listing.random_orders_enabled = false);
the test enables them for its instrument through REST and switches them off again in the teardown.
Teardown: the generator is stopped and the venue is reset - random orders left in the books are removed
(persistence is disabled on the test venue), so the next test starts with empty books again.
Texts are the venue's: status 'Stopped' (documented 'NotRunning'), 'Generator was started / stopped'
(documented 'Random orders generator started / stopped successfully').
"""
import pytest
from allure import step

from framework.assertions.expect import check_true
from tests.support.isolation import wait_until
from tests.support.rest import check_response



@pytest.fixture
def generator_cleanup(one_venue_at_a_time, market, api, venue, undo):
    """The venue reset reloads its configuration from the DB: no shared table may be half-changed meanwhile."""
    undo.push("reset venue: remove random orders from the books", venue.reset)
    undo.push("stop the generator", lambda: api.stop_generator(market.venue_id))


def test_generator_is_stopped_before_tests(market, api):
    check_response(api.get_generator_status(market.venue_id), "GET genstatus", status_code=200, result="Stopped")


def test_start_and_stop_generator(market, api, venue, market_data, undo, generator_cleanup):
    symbol = market.main.symbol
    with step(f"Precondition: enable random orders for {symbol} (off by default) and reload the venue"):
        undo.push(f"disable random orders for {symbol}",
                  lambda: api.update_listing(symbol, {"randomOrdersEnabled": False}))
        check_response(api.update_listing(symbol, {"randomOrdersEnabled": True}), f"PUT listing {symbol}",
                       status_code=200)
        venue.reset()

    with step(f"POST /api/genstart/{market.venue_id}"):
        response = api.start_generator(market.venue_id)
    check_response(response, "POST genstart", status_code=200, result="Generator was started")
    check_response(api.get_generator_status(market.venue_id), "GET genstatus after start", status_code=200,
                   result="Running")

    with step("Check random orders appear in the books"):
        wait_until(lambda: market_data.snapshot(symbol).entries, timeout=10, what=f"random {symbol} orders")
        check_true(f"{symbol} book is not empty", bool(market_data.snapshot(symbol).entries))

    with step(f"POST /api/genstop/{market.venue_id}"):
        response = api.stop_generator(market.venue_id)
    check_response(response, "POST genstop", status_code=200, result="Generator was stopped")
    check_response(api.get_generator_status(market.venue_id), "GET genstatus after stop", status_code=200,
                   result="Stopped")
