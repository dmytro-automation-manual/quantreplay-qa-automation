"""Market orders (OrdType=Market): executed against the book, never rest in it.

Precondition: an own passive order provides the liquidity (the venue matches own orders, includeOwnOrders=true).
Teardown (fixture `trading`): whatever is left of the resting order is cancelled and checked.
"""
import pytest
from allure import step

from framework.assertions.expect import ABSENT, PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus, OrdType, Side
from test_data.orders import market_order, passive_sell


@pytest.mark.smoke
def test_market_buy_fills_at_best_offer(trading, instrument):
    """A market buy smaller than the resting offer is filled completely at the offer price."""
    resting_request = passive_sell(instrument, qty=instrument.round_lot * 2)
    with step(f"Precondition: resting SELL {resting_request.order_qty} {instrument} @ {resting_request.price}"):
        resting, _ = trading.place(resting_request)

    request = market_order(instrument, Side.BUY, qty=instrument.round_lot)
    with step(f"Send market BUY {request.order_qty} {instrument}"):
        order, ack = trading.place(request)

    with step("Check ExecutionReport: New (no price on a market order)"):
        check_execution_report(ack, "ExecutionReport New for market order",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=ABSENT,
                               ord_type=OrdType.MARKET)

    with step("Check ExecutionReport: Trade, Filled at the resting offer price"):
        fill = trading.next_report(order, ExecType.TRADE)
        check_execution_report(fill, "ExecutionReport Trade for market order",
                               order_id=order.order_id, exec_type=ExecType.TRADE, ord_status=OrdStatus.FILLED,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=ABSENT,
                               last_px=resting_request.price, last_qty=request.order_qty,
                               cum_qty=request.order_qty, leaves_qty=0, avg_px=resting_request.price)

    with step("Check ExecutionReport of the resting sell: Trade, PartiallyFilled"):
        passive_fill = trading.next_report(resting, ExecType.TRADE)
        check_execution_report(passive_fill, "ExecutionReport Trade for resting order",
                               order_id=resting.order_id, exec_type=ExecType.TRADE,
                               ord_status=OrdStatus.PARTIALLY_FILLED, symbol=instrument.symbol,
                               order_qty=resting_request.order_qty, price=resting_request.price,
                               last_px=resting_request.price, last_qty=request.order_qty,
                               cum_qty=request.order_qty, leaves_qty=resting_request.order_qty - request.order_qty)


def test_market_order_without_liquidity_is_cancelled(market, trading):
    """With an empty book a market order cannot trade and is cancelled at once (it never rests)."""
    instrument = market.main
    request = market_order(instrument, Side.BUY)
    with step(f"Send market BUY {request.order_qty} {instrument} into an empty book"):
        order, report = trading.place(request)

    with step("Check ExecutionReport: Canceled, 'no facing orders found', nothing filled"):
        check_execution_report(report, "ExecutionReport for market order without liquidity",
                               order_id=PRESENT, exec_type=ExecType.CANCELED, ord_status=OrdStatus.CANCELED,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=ABSENT,
                               cum_qty=0, leaves_qty=0, text="no facing orders found")
