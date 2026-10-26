"""NewOrderSingle (35=D) accepted by the venue.

Precondition (fixtures): empty order books, random order generator stopped.
Teardown (fixture `trading`): the order is cancelled and the cancel report is checked
(same OrderID, ExecType=Canceled, OrdStatus=Canceled, symbol / qty / price unchanged).
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus, OrdType, TimeInForce
from test_data.orders import passive_buy, passive_sell


@pytest.mark.smoke
@pytest.mark.parametrize("make_order", [passive_buy, passive_sell], ids=["buy", "sell"])
def test_new_limit_order_is_accepted(trading, instrument, make_order):
    """A limit order at a valid price is acknowledged as New, gets an OrderID and rests in the book unfilled."""
    request = make_order(instrument)

    with step(f"Send NewOrderSingle {request.side.name} {request.order_qty} {instrument} @ {request.price}"):
        order, report = trading.place(request)

    with step("Check ExecutionReport: New, OrderID assigned, nothing filled"):
        check_execution_report(
            report, "ExecutionReport for NewOrderSingle",
            order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
            symbol=instrument.symbol, order_qty=request.order_qty, price=request.price,
            cl_ord_id=order.cl_ord_id if order else PRESENT, side=request.side, ord_type=OrdType.LIMIT,
            time_in_force=TimeInForce.DAY, leaves_qty=request.order_qty, cum_qty=0, avg_px=0, exec_id=PRESENT)
