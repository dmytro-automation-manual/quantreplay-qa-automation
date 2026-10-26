"""Order book as seen through market data while own orders are placed, amended, traded and cancelled.

Precondition: empty book. Teardown: `trading` cancels and checks left orders, `market_data` unsubscribes.
"""
import pytest
from allure import step

from framework.assertions.expect import check_fields, check_true
from framework.fix.tags import ExecType, MDEntryType, MDUpdateAction, MsgType, Side, TimeInForce
from test_data.instruments import ticks_away
from test_data.orders import limit_order, passive_buy, passive_sell
from tests.support.book import check_book_empty, check_order_rests


@pytest.mark.smoke
def test_snapshot_shows_resting_bid_and_offer(trading, market_data, instrument):
    """Both own resting orders appear in the full book at their price and quantity."""
    bid, offer = passive_buy(instrument), passive_sell(instrument, qty=instrument.round_lot * 2)
    with step(f"Precondition: BUY {bid.order_qty} @ {bid.price} and SELL {offer.order_qty} @ {offer.price}"):
        trading.place(bid)
        trading.place(offer)
    with step(f"Send Snapshot for {instrument}"):
        snapshot = market_data.snapshot(instrument.symbol)
    with step("Check exactly one bid and one offer with the orders' price and size"):
        check_fields("Book size", {"bids": len(snapshot.side(MDEntryType.BID)),
                                   "offers": len(snapshot.side(MDEntryType.OFFER))}, {"bids": 1, "offers": 1})
        check_order_rests(snapshot, Side.BUY, bid.price, bid.order_qty, "Bid in the snapshot")
        check_order_rests(snapshot, Side.SELL, offer.price, offer.order_qty, "Offer in the snapshot")


def test_top_of_book_shows_only_best_bid(market, trading, market_data):
    """MarketDepth=1 returns only the best (highest) bid."""
    instrument = market.main
    worse = passive_buy(instrument)
    better = passive_buy(instrument, price=ticks_away(worse.price, instrument, 5))
    with step(f"Precondition: two bids {worse.price} and {better.price}"):
        trading.place(worse)
        trading.place(better)
    with step("Send Snapshot with MarketDepth=1"):
        snapshot = market_data.snapshot(instrument.symbol, market_depth=1, entry_types=(MDEntryType.BID,))
    with step("Check only the best bid is reported"):
        check_true("One bid level at depth 1", len(snapshot.side(MDEntryType.BID)) == 1,
                   f"found {snapshot.side(MDEntryType.BID)}")
        check_order_rests(snapshot, Side.BUY, better.price, better.order_qty, "Best bid")


@pytest.mark.smoke
def test_incremental_updates_follow_new_and_cancel(market, trading, market_data):
    """Incremental refresh: a new order adds a level (action New), its cancel removes it (action Delete)."""
    instrument = market.main
    with step(f"Precondition: subscribe to {instrument} with incremental updates"):
        initial = market_data.subscribe(instrument.symbol, incremental=True)
        check_book_empty(initial, "Initial snapshot")
    request = passive_buy(instrument)

    with step(f"Place BUY {request.order_qty} @ {request.price}"):
        order, _ = trading.place(request)
    with step("Check MarketDataIncrementalRefresh: New bid at the order's price and size"):
        update = market_data.next_update(initial.md_req_id)
        check_fields("Incremental refresh after NewOrderSingle", update,
                     {"msg_type": MsgType.MARKET_DATA_INCREMENTAL, "md_req_id": initial.md_req_id})
        check_fields("Entry", update.entries[0], {"update_action": MDUpdateAction.NEW, "entry_type": MDEntryType.BID,
                                                  "price": request.price, "size": request.order_qty})

    with step("Cancel the order"):
        trading.cancel(order)
    with step("Check MarketDataIncrementalRefresh: Delete of the same bid level"):
        update = market_data.next_update(initial.md_req_id)
        check_fields("Entry", update.entries[0], {"update_action": MDUpdateAction.DELETE,
                                                  "entry_type": MDEntryType.BID, "price": request.price})


@pytest.mark.smoke
def test_trade_reduces_resting_offer_in_book(market, trading, market_data):
    """After a partial execution the book shows only the open remainder of the resting order."""
    instrument = market.main
    offer = passive_sell(instrument, qty=instrument.round_lot * 3)
    with step(f"Precondition: resting SELL {offer.order_qty} {instrument} @ {offer.price}"):
        resting, _ = trading.place(offer)
    taken = instrument.round_lot
    with step(f"IOC BUY {taken} @ {offer.price} trades against it"):
        trading.place(limit_order(instrument, Side.BUY, qty=taken, price=offer.price,
                                  tif=TimeInForce.IMMEDIATE_OR_CANCEL))
        trading.next_report(resting, ExecType.TRADE)
    with step("Check the book: offer size = original - traded"):
        check_order_rests(market_data.snapshot(instrument.symbol), Side.SELL, offer.price, offer.order_qty - taken,
                          "Offer after partial execution")


def test_unsubscribe_stops_updates(market, trading, market_data):
    """After Unsubscribe the venue sends no more updates for that MDReqID."""
    instrument = market.main
    with step(f"Precondition: subscribe to {instrument}, then unsubscribe"):
        initial = market_data.subscribe(instrument.symbol, incremental=True)
        market_data.unsubscribe(initial.md_req_id, instrument.symbol)
    with step("Place an order that changes the book"):
        trading.place(passive_buy(instrument))
    with step("Check no update arrives for the closed subscription within 1 s"):
        check_true("No MarketDataIncrementalRefresh after Unsubscribe", market_data.no_update(initial.md_req_id))
