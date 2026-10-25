"""Composition root: the only place where the framework layers are wired together.

Session level (once per run):
  * wait for the simulator, stop the random order generator, make sure every order book is empty;
  * capture the configuration tables and, after the last test, prove that nothing changed.
Test level (every test):
  * precondition fixtures give a fresh service object and an empty inbox;
  * teardown cancels the orders the test left active (and checks the cancel), unsubscribes market data,
    and undoes REST changes - so every test starts from the same state, in any order.
"""
import logging

import allure
import pytest

from framework.assertions.trading import check_execution_report
from framework.config import Settings
from framework.fix.tags import ExecType, OrdStatus
from framework.services.db_tables import DatabaseState, ListingTable, PriceSeedTable, SettingTable, VenueTable
from framework.services.market_data import MarketDataService
from framework.services.rest_api import SimulatorApi
from framework.services.trading import TradingService
from framework.transport.db_client import DbClient
from framework.transport.fix_session import FixSession
from framework.transport.http_client import HttpClient
from test_data.instruments import INSTRUMENTS
from tests.support.isolation import UndoStack, wait_until

log = logging.getLogger("setup")

# Folder names that become markers: `pytest -m negative`, `pytest -m "fix and boundary"` ...
FOLDER_MARKERS = {"fix", "rest", "db", "orders", "market_data", "orders_and_market_data",
                  "positive", "negative", "boundary", "time_in_force"}


def pytest_collection_modifyitems(items):
    for item in items:
        for part in item.path.relative_to(item.config.rootpath / "tests").parts[:-1]:
            if part in FOLDER_MARKERS:
                item.add_marker(getattr(pytest.mark, part))
        known = item.get_closest_marker("known_issue")
        if known:
            item.add_marker(pytest.mark.xfail(reason=f"KNOWN ISSUE: {known.args[0]}", strict=True))


# --- clients (session) -----------------------------------------------------------------------------
@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def api(settings):
    http = HttpClient(settings.rest.base_url, settings.rest.timeout)
    yield SimulatorApi(http)
    http.close()


@pytest.fixture(scope="session")
def db(settings):
    client = DbClient(settings.db.host, settings.db.port, settings.db.name, settings.db.user, settings.db.password)
    yield client
    client.close()


def _new_fix_session(settings: Settings) -> FixSession:
    s = settings.fix
    return FixSession(s.host, s.port, s.sender_comp_id, s.target_comp_id, timeout=s.timeout, heartbeat=s.heartbeat)


def _non_empty_books(session: FixSession) -> dict[str, int]:
    """Number of entries per non-empty book."""
    service = MarketDataService(session)
    non_empty = {}
    for instrument in INSTRUMENTS:
        snapshot = service.snapshot(instrument.symbol)
        if snapshot.entries:
            non_empty[instrument.symbol] = len(snapshot.entries)
    return non_empty


class Venue:
    """Venue-level control used by session setup and by the few tests that must reset the venue."""

    def __init__(self, settings: Settings, api: SimulatorApi, fix_session: FixSession):
        self.settings, self.api, self.fix_session = settings, api, fix_session

    def wait_ready(self) -> None:
        wait_until(lambda: self.api.get_venue(self.settings.venue_id).status_code == 200,
                   self.settings.startup_timeout, "Simulator REST API")

    def reset(self) -> None:
        """Reload configuration from the DB and clear the books (persistence is off on the test venue).
        The venue drops the FIX session when the reset really starts; then the session is logged on again."""
        with allure.step("Reset venue (config reload, empty order books)"):
            if not self.fix_session.connected:
                self.fix_session.logon()
            self.api.reset(self.settings.venue_id)
            self.fix_session.wait_disconnect(self.settings.startup_timeout)
            wait_until(self._logon_and_probe, self.settings.startup_timeout, "FIX order session after reset")

    def _logon_and_probe(self) -> bool:
        try:
            self.fix_session.logon()
            MarketDataService(self.fix_session).snapshot(INSTRUMENTS[0].symbol)
            return True
        except (OSError, TimeoutError):
            self.fix_session.close()
            return False


@pytest.fixture(scope="session")
def fix_session(settings):
    session = _new_fix_session(settings)
    yield session
    session.logout()


@pytest.fixture(scope="session")
def venue(settings, api, fix_session) -> Venue:
    return Venue(settings, api, fix_session)


@pytest.fixture(scope="session", autouse=True)
def clean_venue(settings, api, db, fix_session, venue):
    """Session precondition and final isolation proof."""
    venue_id = settings.venue_id
    with allure.step("Session setup: simulator is up, generator stopped, books empty"):
        venue.wait_ready()
        generator_was_running = api.get_generator_status(venue_id).result == "Running"
        if generator_was_running:
            api.stop_generator(venue_id)
        fix_session.logon()
        dirty = _non_empty_books(fix_session)
        if dirty:
            log.warning("Order books are not empty before the run (%s) - resetting the venue", dirty)
            venue.reset()
            dirty = _non_empty_books(fix_session)
            assert not dirty, f"Order books still not empty after reset: {dirty}"
        state_before = DatabaseState(db).capture()

    yield

    with allure.step("Session teardown: no order and no configuration change left behind"):
        problems = []
        if fix_session.connected:
            dirty = _non_empty_books(fix_session)
            if dirty:
                problems.append(f"orders left in the books: {dirty}")
        state_after = DatabaseState(db).capture()
        changed = [t for t in state_before if state_before[t] != state_after[t]]
        if changed:
            problems.append(f"configuration tables changed by the run: {changed}")
        if generator_was_running:
            api.start_generator(venue_id)
        assert not problems, "Test isolation broken: " + "; ".join(problems)


# --- services (per test) ---------------------------------------------------------------------------
@pytest.fixture
def trading(fix_session):
    """Order entry for one test. Teardown cancels every order the test left active and checks the cancel."""
    fix_session.clear_inbox()
    service = TradingService(fix_session)
    yield service
    for order in service.active_orders():
        with allure.step(f"Teardown: cancel {order.side.name} {order.order_qty} {order.symbol} @ {order.price}"):
            report = service.cancel(order)
            check_execution_report(report, "Teardown: ExecutionReport for OrderCancelRequest",
                                   order_id=order.order_id, exec_type=ExecType.CANCELED,
                                   ord_status=OrdStatus.CANCELED, symbol=order.symbol,
                                   order_qty=order.order_qty, price=order.price)


@pytest.fixture
def market_data(fix_session):
    """Market data for one test. Teardown unsubscribes every subscription the test opened."""
    service = MarketDataService(fix_session)
    yield service
    for md_req_id, request in list(service.subscriptions.items()):
        with allure.step(f"Teardown: unsubscribe {request.symbol} ({md_req_id})"):
            service.unsubscribe(md_req_id, request.symbol)


@pytest.fixture
def undo():
    """Register how to undo a change before making it: undo.push("restore AMZ", lambda: ...)."""
    stack = UndoStack()
    yield stack
    stack.run_all()


# --- database tables -------------------------------------------------------------------------------
@pytest.fixture(scope="session")
def venue_table(db):
    return VenueTable(db)


@pytest.fixture(scope="session")
def listing_table(db):
    return ListingTable(db)


@pytest.fixture(scope="session")
def price_seed_table(db):
    return PriceSeedTable(db)


@pytest.fixture(scope="session")
def setting_table(db):
    return SettingTable(db)
