"""OrderCancelReplaceRequest (35=G) on an active order: price first, then quantity.

Precondition: a passive limit order is placed and acknowledged as New.
Teardown (fixture `trading`): the replaced order is cancelled and the cancel report is checked.
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus
from test_data.instruments import INSTRUMENTS, ticks_away
from test_data.orders import passive_buy


@pytest.mark.smoke
@pytest.mark.parametrize("instrument", INSTRUMENTS, ids=str)
def test_replace_price_then_quantity(trading, instrument):
    """Each replace is acknowledged as Replaced on the same OrderID and changes only the requested field."""
    request = passive_buy(instrument)
    with step(f"Precondition: place BUY {request.order_qty} {instrument} @ {request.price}"):
        order, report = trading.place(request)
        check_execution_report(report, "ExecutionReport for NewOrderSingle",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price)
    first_cl_ord_id = order.cl_ord_id

    new_price = ticks_away(request.price, instrument, 1)
    with step(f"Step 1: replace price {request.price} -> {new_price} (one tick up)"):
        report = trading.replace(order, price=new_price)
    with step("Check ExecutionReport: Replaced, same OrderID, new price, quantity unchanged"):
        check_execution_report(report, "ExecutionReport for price replace",
                               order_id=order.order_id, exec_type=ExecType.REPLACED,
                               ord_status=OrdStatus.REPLACED, symbol=instrument.symbol,
                               order_qty=request.order_qty, price=new_price,
                               orig_cl_ord_id=first_cl_ord_id, leaves_qty=request.order_qty, cum_qty=0)

    new_qty = request.order_qty * 2
    second_cl_ord_id = order.cl_ord_id
    with step(f"Step 2: replace quantity {request.order_qty} -> {new_qty}"):
        report = trading.replace(order, order_qty=new_qty)
    with step("Check ExecutionReport: Replaced, same OrderID, new quantity, price kept from step 1"):
        check_execution_report(report, "ExecutionReport for quantity replace",
                               order_id=order.order_id, exec_type=ExecType.REPLACED,
                               ord_status=OrdStatus.REPLACED, symbol=instrument.symbol,
                               order_qty=new_qty, price=new_price,
                               orig_cl_ord_id=second_cl_ord_id, leaves_qty=new_qty, cum_qty=0)
