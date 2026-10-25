"""Order quantity limits of each listing: qtyMinimum, qtyMaximum, qtyMultiple (values in test_data/instruments.py).

Exactly on the limit -> accepted (New); one step outside -> rejected with the documented Text.
qtyMaximum is the fat-finger limit: an order above it must never reach the book.
Teardown (fixture `trading`): accepted orders are cancelled and the cancel report is checked.
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus
from test_data.instruments import INSTRUMENTS
from test_data.orders import passive_buy

TEXT_WITHOUT_IS = ("Reject Text differs from RoE: the venue sends '... constraint violated', "
                   "RoE 'New Order Single' documents '... constraint is violated'")


def _check_accepted(report, instrument, request, title):
    check_execution_report(report, title, order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                           symbol=instrument.symbol, order_qty=request.order_qty, price=request.price,
                           leaves_qty=request.order_qty)


def _check_rejected(report, instrument, request, title, text):
    check_execution_report(report, title, order_id=PRESENT, exec_type=ExecType.REJECTED,
                           ord_status=OrdStatus.REJECTED, symbol=instrument.symbol,
                           order_qty=request.order_qty, price=request.price, text=text)


@pytest.mark.parametrize("instrument", INSTRUMENTS, ids=str)
def test_quantity_equal_to_minimum_is_accepted(trading, instrument):
    request = passive_buy(instrument, qty=instrument.qty_minimum)
    with step(f"Send BUY {instrument} with OrderQty = qtyMinimum = {request.order_qty}"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: New"):
        _check_accepted(report, instrument, request, "ExecutionReport for OrderQty = qtyMinimum")


@pytest.mark.known_issue(TEXT_WITHOUT_IS)
@pytest.mark.parametrize("instrument", INSTRUMENTS, ids=str)
def test_quantity_below_minimum_is_rejected(trading, instrument):
    request = passive_buy(instrument, qty=instrument.qty_minimum - instrument.qty_multiple)
    with step(f"Send BUY {instrument} with OrderQty = qtyMinimum - qtyMultiple = {request.order_qty}"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, minimal quantity constraint"):
        _check_rejected(report, instrument, request, "ExecutionReport for OrderQty below qtyMinimum",
                        "minimal order quantity constraint is violated")


@pytest.mark.smoke
@pytest.mark.parametrize("instrument", INSTRUMENTS, ids=str)
def test_quantity_equal_to_maximum_is_accepted(trading, instrument):
    request = passive_buy(instrument, qty=instrument.qty_maximum)
    with step(f"Send BUY {instrument} with OrderQty = qtyMaximum = {request.order_qty}"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: New"):
        _check_accepted(report, instrument, request, "ExecutionReport for OrderQty = qtyMaximum")


@pytest.mark.smoke
@pytest.mark.known_issue(TEXT_WITHOUT_IS)
@pytest.mark.parametrize("instrument", INSTRUMENTS, ids=str)
def test_quantity_above_maximum_is_rejected(trading, instrument):
    request = passive_buy(instrument, qty=instrument.qty_maximum + instrument.qty_multiple)
    with step(f"Send BUY {instrument} with OrderQty = qtyMaximum + qtyMultiple = {request.order_qty}"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, maximal quantity constraint"):
        _check_rejected(report, instrument, request, "ExecutionReport for OrderQty above qtyMaximum",
                        "maximal order quantity constraint is violated")


@pytest.mark.known_issue(TEXT_WITHOUT_IS)
@pytest.mark.parametrize("instrument", INSTRUMENTS, ids=str)
def test_quantity_not_multiple_of_lot_is_rejected(trading, instrument):
    request = passive_buy(instrument, qty=instrument.round_lot + instrument.qty_multiple / 2)
    with step(f"Send BUY {instrument} with OrderQty {request.order_qty} (not a multiple of {instrument.qty_multiple})"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, quantity multiple constraint"):
        _check_rejected(report, instrument, request, "ExecutionReport for OrderQty off the lot size",
                        "order quantity multiple constraint is violated")
