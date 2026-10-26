"""OrderCancelReplaceRequest rejects (Rules of Engagement, "Order Cancel Replace Request" rejection reasons).

A rejected replace is answered with OrderCancelReject (35=9), CxlRejResponseTo=OrderCancelReplaceRequest,
OrdStatus=Rejected. "An order is not modified if OrderCancelReplaceRequest is rejected" - checked in the book.
Teardown (fixture `trading`): the still active order is cancelled and the cancel report is checked.
"""
from dataclasses import replace

import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_cancel_reject, check_execution_report
from framework.fix.tags import CxlRejResponseTo, ExecType, OrdStatus, Side, TimeInForce
from test_data.instruments import ticks_away
from test_data.orders import passive_buy
from tests.support.book import check_order_rests


REPLACE_REJECT_STATUS = ("OrderCancelReject for a replace of an ACTIVE order carries the order's current OrdStatus "
                         "(New / PartiallyFilled) instead of Rejected required by RoE 'Order Cancel Replace Request'")


def _place_resting_buy(trading, instrument):
    request = passive_buy(instrument)
    with step(f"Precondition: place BUY {request.order_qty} {instrument} @ {request.price} (Day)"):
        order, report = trading.place(request)
        check_execution_report(report, "ExecutionReport for NewOrderSingle",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price)
    return order, request


def test_replace_of_cancelled_order_is_rejected(market, trading):
    """A terminated (cancelled) order cannot be replaced: 'order not found'."""
    instrument = market.main
    order, request = _place_resting_buy(trading, instrument)
    with step("Precondition: cancel the order"):
        report = trading.cancel(order)
        check_execution_report(report, "ExecutionReport for cancel",
                               order_id=order.order_id, exec_type=ExecType.CANCELED, ord_status=OrdStatus.CANCELED,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price)

    with step("Send OrderCancelReplaceRequest (price one tick up)"):
        reject = trading.replace(order, price=ticks_away(request.price, instrument, 1))
    with step("Check OrderCancelReject: 'order not found'"):
        check_cancel_reject(reject, "OrderCancelReject for replace of cancelled order",
                            order_id=order.order_id, ord_status=OrdStatus.REJECTED,
                            cxl_rej_response_to=CxlRejResponseTo.ORDER_CANCEL_REPLACE_REQUEST,
                            text="order not found")


@pytest.mark.known_issue(REPLACE_REJECT_STATUS)
def test_replace_changing_time_in_force_is_rejected(market, trading, market_data):
    """TimeInForce cannot be amended: 'time in force can not be changed'; the order keeps its price and qty."""
    instrument = market.main
    order, request = _place_resting_buy(trading, instrument)
    with step("Send OrderCancelReplaceRequest Day -> GoodTillCancel"):
        reject = trading.replace(order, time_in_force=TimeInForce.GOOD_TILL_CANCEL)
    with step("Check OrderCancelReject: 'time in force can not be changed'"):
        check_cancel_reject(reject, "OrderCancelReject for TimeInForce change",
                            order_id=order.order_id, ord_status=OrdStatus.REJECTED,
                            cxl_rej_response_to=CxlRejResponseTo.ORDER_CANCEL_REPLACE_REQUEST,
                            text="time in force can not be changed")
    with step("Check the order is not modified"):
        check_order_rests(market_data.snapshot(instrument.symbol), Side.BUY, request.price, request.order_qty,
                          "Book after rejected replace")


@pytest.mark.known_issue(REPLACE_REJECT_STATUS)
def test_replace_quantity_not_above_executed_is_rejected(market, trading, market_data):
    """New OrderQty <= CumQty is rejected: 'invalid quantity' (partially filled resting order)."""
    instrument = market.main
    order, request = _place_resting_buy(trading, instrument)
    executed = request.order_qty / 2
    with step(f"Precondition: SELL {executed} @ {request.price} partially fills the resting buy"):
        sell = replace(request, side=Side.SELL, order_qty=executed, time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL)
        trading.place(sell)
        fill = trading.next_report(order, ExecType.TRADE)
        check_execution_report(fill, "ExecutionReport Trade for resting buy",
                               order_id=order.order_id, exec_type=ExecType.TRADE,
                               ord_status=OrdStatus.PARTIALLY_FILLED, symbol=instrument.symbol,
                               order_qty=request.order_qty, price=request.price, cum_qty=executed)

    with step(f"Send OrderCancelReplaceRequest with OrderQty = CumQty = {executed}"):
        reject = trading.replace(order, order_qty=executed)
    with step("Check OrderCancelReject: 'invalid quantity'"):
        check_cancel_reject(reject, "OrderCancelReject for quantity not above CumQty",
                            order_id=order.order_id, ord_status=OrdStatus.REJECTED,
                            cxl_rej_response_to=CxlRejResponseTo.ORDER_CANCEL_REPLACE_REQUEST,
                            text="invalid quantity")
    with step("Check the open remainder is not modified"):
        check_order_rests(market_data.snapshot(instrument.symbol), Side.BUY, request.price,
                          request.order_qty - executed, "Book after rejected replace")
