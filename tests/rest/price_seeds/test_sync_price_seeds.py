"""POST /api/syncpriceseeds: the simulator copies starting prices from an external price seed database.

Real-world idea: an end-of-day job writes closing prices into a central database, every simulator pulls them
with one REST call. Here the external database is the container external_price-seed-db (sim-run/db/
external_price_seed.sql) with one instrument per venue - VOW and EUR/USD; scripts/update_external_prices.sh
plays the daily job for demos.
The tests do not depend on that job: each one writes known prices into the external database itself,
runs the sync and checks the result.

Sync rules (simulator/project/http/src/data_bridge/price_seed_accessor.cpp): for every external row, by symbol -
an existing seed gets bid / mid / offer / last update, a missing symbol is inserted; nothing is deleted.
Teardown (fixture `undo`): the external rows are put back and synced again, so the simulator seeds return too;
an inserted symbol is deleted on both sides. SeedPricesLastUpdated cannot be restored (read-only, written by the
simulator) and is left out of the session isolation check (DatabaseState.EXCLUDED_SETTINGS).
"""
import time
from decimal import Decimal

import pytest
from allure import step

from framework.assertions.expect import check_fields, check_true
from framework.services.rest_api import to_price_seed
from test_data.instruments import EUR_USD, VOW
from tests.support.rest import check_response

SYNCED = "Price seeds successfully synchronized"
SYNC_FAILED = "Failed to synchronize price seeds because of unknown reason"
CONNECTION = "SeedPriceDatabaseConnection"
LAST_SYNC = "SeedPricesLastUpdated"
NEW_SYMBOL = "QASYNC"

# The instrument each venue has in the external price seed database.
EXTERNAL_INSTRUMENT = {"XETRA": VOW, "FASTMATCH": EUR_USD}

# Price seeds and settings are shared by both venues: one venue at a time (see `one_venue_at_a_time`).
pytestmark = pytest.mark.usefixtures("one_venue_at_a_time")


def _seed(api, symbol):
    seeds = [s for s in api.get_price_seeds().body["priceSeeds"] if s["symbol"] == symbol]
    return seeds[0] if seeds else None


def _setting(api, key):
    return {s["key"]: s.get("value") for s in api.get_settings().body["settings"]}[key]


def _sync(api):
    with step("POST /api/syncpriceseeds"):
        response = api.sync_price_seeds()
    check_response(response, "Sync price seeds", status_code=200, result=SYNCED)


@pytest.fixture
def external_instrument(market):
    return EXTERNAL_INSTRUMENT[market.venue_id]


@pytest.fixture
def restore_external(api, external_price_seed_table, undo):
    """restore_external("VOW") - after the test the external row gets its old prices back and is synced again,
    so the simulator seed returns to the same values as well."""
    def remember(symbol: str) -> dict:
        row = external_price_seed_table.get(symbol)
        assert row, f"{symbol} is missing in the external price seed database"

        def restore():
            external_price_seed_table.set_prices(symbol, row["bid_price"], row["mid_price"], row["offer_price"],
                                                 row["last_update"])
            check_response(api.sync_price_seeds(), "Re-sync after restore", status_code=200, result=SYNCED)

        undo.push(f"restore external {symbol} {row['bid_price']} / {row['mid_price']} / {row['offer_price']}"
                  " and sync", restore)
        return row
    return remember


@pytest.mark.smoke
def test_sync_copies_changed_prices(external_instrument, api, external_price_seed_table, restore_external):
    instrument = external_instrument
    restore_external(instrument.symbol)
    shift = instrument.tick_size * 10
    bid, mid, offer = instrument.bid + shift, instrument.mid + shift, instrument.offer + shift
    stamp = "2026-11-04 17:30:00"
    with step(f"External DB: {instrument} -> {bid} / {mid} / {offer} (10 ticks up), last update {stamp}"):
        external_price_seed_table.set_prices(instrument.symbol, bid, mid, offer, stamp)

    _sync(api)

    seed = _seed(api, instrument.symbol)
    check_fields(f"Simulator seed {instrument} after sync", to_price_seed(seed) if seed else None,
                 {"bid_price": bid, "mid_price": mid, "offer_price": offer})
    check_fields(f"Simulator seed {instrument}: last update", seed, {"lastUpdate": stamp})


def test_sync_updates_last_sync_time(api):
    before = _setting(api, LAST_SYNC)
    time.sleep(1.1)        # the setting has 1 s resolution: a previous test's sync may share the same second
    _sync(api)
    after = _setting(api, LAST_SYNC)
    # "YYYY-MM-DD HH:MM:SS": the text order is the time order
    check_true(f"{LAST_SYNC} moved forward", after > before, f"before {before}, after {after}")


def test_sync_inserts_symbol_missing_in_simulator(api, external_price_seed_table, undo):
    assert _seed(api, NEW_SYMBOL) is None, f"{NEW_SYMBOL} already exists in the simulator"
    bid, mid, offer = Decimal("9.98"), Decimal("10.00"), Decimal("10.02")
    undo.push(f"delete {NEW_SYMBOL} from the external DB", lambda: external_price_seed_table.delete(NEW_SYMBOL))
    with step(f"External DB: add {NEW_SYMBOL} {bid} / {mid} / {offer} (not in the simulator)"):
        external_price_seed_table.add(NEW_SYMBOL, "CS", "EUR", bid, mid, offer, "2026-11-04 17:30:00")

    _sync(api)

    seed = _seed(api, NEW_SYMBOL)
    if seed:
        undo.push(f"delete simulator seed {NEW_SYMBOL}", lambda: api.delete_price_seed(seed["id"]))
    check_fields(f"Simulator seed {NEW_SYMBOL} after sync", to_price_seed(seed) if seed else None,
                 {"symbol": NEW_SYMBOL, "security_type": "CS", "price_currency": "EUR",
                  "bid_price": bid, "mid_price": mid, "offer_price": offer})


@pytest.mark.negative
def test_sync_with_unreachable_database_changes_nothing(external_instrument, api, external_price_seed_table, restore_external,
                                                         undo):
    instrument = external_instrument
    restore_external(instrument.symbol)
    with step(f"External DB: {instrument} mid -> {instrument.mid + instrument.tick_size * 10}"):
        external_price_seed_table.set_prices(instrument.symbol, instrument.bid, instrument.mid + instrument.tick_size * 10,
                                             instrument.offer, "2026-11-04 17:30:00")
    connection = _setting(api, CONNECTION)
    undo.push(f"restore {CONNECTION}", lambda: api.update_settings([{"key": CONNECTION, "value": connection}]))
    wrong = connection.replace("priceseed:priceseed@", "priceseed:wrong-password@")
    with step(f"PUT /api/settings {CONNECTION}: wrong password"):
        api.update_settings([{"key": CONNECTION, "value": wrong}])
    seed_before, last_sync_before = _seed(api, instrument.symbol), _setting(api, LAST_SYNC)

    with step("POST /api/syncpriceseeds"):
        response = api.sync_price_seeds()

    check_response(response, "Sync with a wrong connection", status_code=500, result=SYNC_FAILED)
    check_true(f"Simulator seed {instrument} unchanged", _seed(api, instrument.symbol) == seed_before,
               str(_seed(api, instrument.symbol)))
    check_fields("Last sync time unchanged", {LAST_SYNC: _setting(api, LAST_SYNC)}, {LAST_SYNC: last_sync_before})
