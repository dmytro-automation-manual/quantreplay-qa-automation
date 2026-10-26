"""MarketDataRequest (35=V) answered with MarketDataSnapshotFullRefresh (35=W).

Precondition: empty order books (generator stopped). Teardown (fixture `market_data`): subscriptions are closed.
How the book content changes with orders is covered in tests/fix/orders_and_market_data.
"""
import pytest
from allure import step

from framework.assertions.expect import check_fields
from framework.fix.tags import MDEntryType, MsgType
from tests.support.book import check_book_empty


@pytest.mark.smoke
def test_snapshot_returns_full_refresh_for_requested_symbol(market_data, instrument):
    with step(f"Send MarketDataRequest Snapshot for {instrument}"):
        snapshot = market_data.snapshot(instrument.symbol)
    with step("Check MarketDataSnapshotFullRefresh for the same symbol and request id, empty book"):
        check_fields("MarketDataSnapshotFullRefresh", snapshot,
                     {"msg_type": MsgType.MARKET_DATA_SNAPSHOT, "symbol": instrument.symbol})
        check_book_empty(snapshot, "No bids / offers in an empty book")


@pytest.mark.parametrize("entry_types", [(MDEntryType.BID,), (MDEntryType.OFFER,), (MDEntryType.TRADE,),
                                         (MDEntryType.BID, MDEntryType.OFFER, MDEntryType.TRADE)],
                         ids=["bid", "offer", "trade", "bid+offer+trade"])
def test_snapshot_accepts_each_supported_entry_type(market, market_data, entry_types):
    """Every documented MDEntryType can be requested (Market Data Entry Types section)."""
    instrument = market.main
    with step(f"Send Snapshot for {instrument} with MDEntryTypes {[t.name for t in entry_types]}"):
        snapshot = market_data.snapshot(instrument.symbol, entry_types=entry_types)
    with step("Check the answer is a full refresh, not a reject"):
        check_fields("MarketDataSnapshotFullRefresh", snapshot,
                     {"msg_type": MsgType.MARKET_DATA_SNAPSHOT, "symbol": instrument.symbol})


@pytest.mark.parametrize("incremental", [True, False], ids=["incremental", "full-refresh"])
def test_subscribe_starts_with_snapshot(market, market_data, incremental):
    """A subscription (Snapshot + Updates) is answered first with the current full book."""
    instrument = market.main
    with step(f"Subscribe to {instrument} (MDUpdateType {'incremental' if incremental else 'full refresh'})"):
        snapshot = market_data.subscribe(instrument.symbol, incremental=incremental)
    with step("Check the initial MarketDataSnapshotFullRefresh"):
        check_fields("Initial snapshot of the subscription", snapshot,
                     {"msg_type": MsgType.MARKET_DATA_SNAPSHOT, "symbol": instrument.symbol})
        check_book_empty(snapshot, "Initial snapshot of an empty book")
