"""POST /api/halt and /api/resume and their effect on order entry (FIX).

Teardown (fixture `undo`): the market is resumed; `trading` cancels and checks left orders.
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_cancel_reject, check_execution_report
from framework.fix.tags import CxlRejResponseTo, ExecType, OrdStatus
from test_data.instruments import AMZ
from test_data.orders import passive_buy
from tests.support.rest import check_response

VENUE = "XETRA"
HALTED = "request cannot be processed during halted trading status"


@pytest.fixture
def halted_market(api, undo):
    def halt(allow_cancels: bool):
        undo.push("resume the market", lambda: api.resume(VENUE))
        with step(f"POST /api/halt/{VENUE} allowCancels={allow_cancels}"):
            response = api.halt(VENUE, allow_cancels)
        check_response(response, "POST halt", status_code=200, result="The market was successfully halted.")
    return halt


@pytest.mark.smoke
def test_new_order_rejected_while_halted(trading, halted_market):
    halted_market(allow_cancels=True)
    request = passive_buy(AMZ)
    with step(f"Send BUY {request.order_qty} {AMZ} @ {request.price}"):
        _, report = trading.place(request)
    check_execution_report(report, "ExecutionReport during halt",
                           order_id=PRESENT, exec_type=ExecType.REJECTED, ord_status=OrdStatus.REJECTED,
                           symbol=AMZ.symbol, order_qty=request.order_qty, price=request.price, text=HALTED)


def test_cancel_allowed_while_halted_with_allow_cancels(trading, halted_market):
    request = passive_buy(AMZ)
    order, _ = trading.place(request)
    halted_market(allow_cancels=True)
    with step("Send OrderCancelRequest during the halt"):
        report = trading.cancel(order)
    check_execution_report(report, "ExecutionReport for cancel during halt",
                           order_id=order.order_id, exec_type=ExecType.CANCELED, ord_status=OrdStatus.CANCELED,
                           symbol=AMZ.symbol, order_qty=request.order_qty, price=request.price)


def test_cancel_rejected_while_halted_without_allow_cancels(trading, halted_market):
    request = passive_buy(AMZ)
    order, _ = trading.place(request)
    halted_market(allow_cancels=False)
    with step("Send OrderCancelRequest during the halt"):
        reject = trading.cancel(order)
    check_cancel_reject(reject, "OrderCancelReject during halt", order_id=order.order_id,
                        ord_status=OrdStatus.REJECTED, cxl_rej_response_to=CxlRejResponseTo.ORDER_CANCEL_REQUEST,
                        text=HALTED)


def test_resume_reopens_order_entry(trading, api, halted_market):
    halted_market(allow_cancels=True)
    with step(f"POST /api/resume/{VENUE}"):
        response = api.resume(VENUE)
    check_response(response, "POST resume", status_code=200, result="The market was successfully resumed.")
    request = passive_buy(AMZ)
    with step("Send NewOrderSingle after resume"):
        _, report = trading.place(request)
    check_execution_report(report, "ExecutionReport after resume",
                           order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                           symbol=AMZ.symbol, order_qty=request.order_qty, price=request.price)


def test_halt_twice_and_resume_without_halt_are_conflicts(api, halted_market):
    halted_market(allow_cancels=True)
    check_response(api.halt(VENUE, True), "Second halt", status_code=409, result="The market is already halted.")
    check_response(api.resume(VENUE), "Resume", status_code=200, result="The market was successfully resumed.")
    check_response(api.resume(VENUE), "Resume without halt", status_code=409,
                   result="There is no halt request to terminate.")
