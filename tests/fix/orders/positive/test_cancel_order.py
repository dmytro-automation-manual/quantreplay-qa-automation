"""OrderCancelRequest (35=F) on an active order.

Precondition: a passive limit order is placed and acknowledged as New.
Teardown: nothing left - the test itself cancels the order (fixture `trading` would cancel it otherwise).
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus
from test_data.instruments import INSTRUMENTS
from test_data.orders import passive_buy, passive_sell


@pytest.mark.smoke
@pytest.mark.parametrize("instrument", INSTRUMENTS, ids=str)
@pytest.mark.parametrize("make_order", [passive_buy, passive_sell], ids=["buy", "sell"])
def test_cancel_active_order(trading, instrument, make_order):
    """The cancel is acknowledged as Canceled on the same OrderID with nothing left open (LeavesQty=0)."""
    request = make_order(instrument)
    with step(f"Precondition: place {request.side.name} {request.order_qty} {instrument} @ {request.price}"):
        order, report = trading.place(request)
        check_execution_report(report, "ExecutionReport for NewOrderSingle",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price)
    original_cl_ord_id = order.cl_ord_id

    with step("Send OrderCancelRequest"):
        report = trading.cancel(order)

    with step("Check ExecutionReport: Canceled, same OrderID, LeavesQty=0"):
        check_execution_report(report, "ExecutionReport for OrderCancelRequest",
                               order_id=order.order_id, exec_type=ExecType.CANCELED,
                               ord_status=OrdStatus.CANCELED, symbol=instrument.symbol,
                               order_qty=request.order_qty, price=request.price,
                               side=request.side, orig_cl_ord_id=original_cl_ord_id,
                               leaves_qty=0, cum_qty=0)
