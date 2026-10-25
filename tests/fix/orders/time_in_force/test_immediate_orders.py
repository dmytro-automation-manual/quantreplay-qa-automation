"""ImmediateOrCancel and FillOrKill: execute at once against the book, never rest.

Liquidity comes from an own resting SELL (the venue matches own orders: includeOwnOrders=true),
at a price far from the market so nothing else can interfere.
Teardown (fixture `trading`): the remainder of the resting sell is cancelled and the cancel report is checked.
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus, Side, TimeInForce
from test_data.instruments import AMZ, INSTRUMENTS
from test_data.orders import limit_order, passive_sell
from tests.support.book import check_book_empty, check_order_rests

IOC, FOK = TimeInForce.IMMEDIATE_OR_CANCEL, TimeInForce.FILL_OR_KILL


def _resting_sell(trading, instrument, qty):
    request = passive_sell(instrument, qty=qty)
    with step(f"Precondition: resting SELL {qty} {instrument} @ {request.price}"):
        order, report = trading.place(request)
        check_execution_report(report, "ExecutionReport for resting sell",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=qty, price=request.price)
    return order, request


# --- no liquidity ----------------------------------------------------------------------------------
@pytest.mark.parametrize("tif", [IOC, FOK], ids=["IOC", "FOK"])
def test_immediate_order_without_liquidity_is_cancelled(trading, market_data, tif):
    """Nothing to trade against: cancelled immediately with 'no facing orders found', nothing rests."""
    request = limit_order(AMZ, Side.BUY, tif=tif)
    with step(f"Send {tif.name} BUY {request.order_qty} {AMZ} @ {request.price} into an empty book"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Canceled, nothing filled"):
        check_execution_report(report, f"ExecutionReport for {tif.name} without liquidity",
                               order_id=PRESENT, exec_type=ExecType.CANCELED, ord_status=OrdStatus.CANCELED,
                               symbol=AMZ.symbol, order_qty=request.order_qty, price=request.price,
                               time_in_force=tif, cum_qty=0, leaves_qty=0, text="no facing orders found")
    with step("Check the book stays empty"):
        check_book_empty(market_data.snapshot(AMZ.symbol), "Book after immediate order")


# --- full fill -------------------------------------------------------------------------------------
@pytest.mark.smoke
@pytest.mark.parametrize("instrument", INSTRUMENTS, ids=str)
@pytest.mark.parametrize("tif", [IOC, FOK], ids=["IOC", "FOK"])
def test_immediate_order_with_enough_liquidity_is_filled(trading, instrument, tif):
    """Enough liquidity at the limit price: New, then one Trade that fills the whole order at the resting price."""
    resting, resting_request = _resting_sell(trading, instrument, instrument.round_lot * 2)
    request = limit_order(instrument, Side.BUY, qty=instrument.round_lot, price=resting_request.price, tif=tif)

    with step(f"Send {tif.name} BUY {request.order_qty} @ {request.price}"):
        order, ack = trading.place(request)
    with step("Check ExecutionReport: New"):
        check_execution_report(ack, f"ExecutionReport New for {tif.name}",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price,
                               time_in_force=tif)
    with step("Check ExecutionReport: Trade, Filled"):
        fill = trading.next_report(order, ExecType.TRADE)
        check_execution_report(fill, f"ExecutionReport Trade for {tif.name}",
                               order_id=order.order_id, exec_type=ExecType.TRADE, ord_status=OrdStatus.FILLED,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price,
                               last_px=resting_request.price, last_qty=request.order_qty,
                               cum_qty=request.order_qty, leaves_qty=0, avg_px=resting_request.price)
    with step("Check ExecutionReport of the resting sell: Trade, PartiallyFilled"):
        passive_fill = trading.next_report(resting, ExecType.TRADE)
        check_execution_report(passive_fill, "ExecutionReport Trade for resting sell",
                               order_id=resting.order_id, exec_type=ExecType.TRADE,
                               ord_status=OrdStatus.PARTIALLY_FILLED, symbol=instrument.symbol,
                               order_qty=resting_request.order_qty, price=resting_request.price,
                               last_qty=request.order_qty, cum_qty=request.order_qty,
                               leaves_qty=resting_request.order_qty - request.order_qty)


# --- not enough liquidity --------------------------------------------------------------------------
@pytest.mark.smoke
def test_ioc_partially_filled_and_remainder_cancelled(trading):
    """IOC larger than the liquidity: trades what is available, the rest is cancelled at once."""
    available = AMZ.round_lot
    resting, resting_request = _resting_sell(trading, AMZ, available)
    request = limit_order(AMZ, Side.BUY, qty=available * 3, price=resting_request.price, tif=IOC)

    with step(f"Send IOC BUY {request.order_qty} @ {request.price} (only {available} available)"):
        order, _ = trading.place(request)
    with step(f"Check ExecutionReport: Trade {available}, PartiallyFilled"):
        fill = trading.next_report(order, ExecType.TRADE)
        check_execution_report(fill, "ExecutionReport Trade for IOC",
                               order_id=order.order_id, exec_type=ExecType.TRADE,
                               ord_status=OrdStatus.PARTIALLY_FILLED, symbol=AMZ.symbol,
                               order_qty=request.order_qty, price=request.price,
                               last_px=resting_request.price, last_qty=available, cum_qty=available,
                               leaves_qty=request.order_qty - available)
    with step("Check ExecutionReport: remainder Canceled, 'not enough liquidity to fully fill IoC order'"):
        cancel = trading.next_report(order, ExecType.CANCELED)
        check_execution_report(cancel, "ExecutionReport Canceled for IOC remainder",
                               order_id=order.order_id, exec_type=ExecType.CANCELED,
                               ord_status=OrdStatus.CANCELED, symbol=AMZ.symbol,
                               order_qty=request.order_qty, price=request.price, cum_qty=available,
                               leaves_qty=0, text="not enough liquidity to fully fill IoC order")
    with step("Check the resting sell is fully filled"):
        passive_fill = trading.next_report(resting, ExecType.TRADE)
        check_execution_report(passive_fill, "ExecutionReport Trade for resting sell",
                               order_id=resting.order_id, exec_type=ExecType.TRADE, ord_status=OrdStatus.FILLED,
                               symbol=AMZ.symbol, order_qty=available, price=resting_request.price,
                               cum_qty=available, leaves_qty=0)


@pytest.mark.smoke
def test_fok_without_enough_liquidity_is_killed_and_book_untouched(trading, market_data):
    """FOK larger than the liquidity: nothing trades at all, and the resting order keeps its full quantity."""
    available = AMZ.round_lot
    resting, resting_request = _resting_sell(trading, AMZ, available)
    request = limit_order(AMZ, Side.BUY, qty=available * 3, price=resting_request.price, tif=FOK)

    with step(f"Send FOK BUY {request.order_qty} @ {request.price} (only {available} available)"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Canceled, 'not enough liquidity to fill FoK order', nothing filled"):
        check_execution_report(report, "ExecutionReport for FOK without enough liquidity",
                               order_id=PRESENT, exec_type=ExecType.CANCELED, ord_status=OrdStatus.CANCELED,
                               symbol=AMZ.symbol, order_qty=request.order_qty, price=request.price,
                               time_in_force=FOK, cum_qty=0, leaves_qty=0,
                               text="not enough liquidity to fill FoK order")
    with step("Check the resting sell is untouched"):
        check_order_rests(market_data.snapshot(AMZ.symbol), Side.SELL, resting_request.price, available,
                          "Book after killed FOK")
