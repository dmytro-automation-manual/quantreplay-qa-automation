"""OrderCancelRequest rejects (Rules of Engagement, "Order Cancel Request" rejection reasons).

A rejected cancel is answered with OrderCancelReject (35=9), CxlRejResponseTo=OrderCancelRequest,
OrdStatus=Rejected and Text 'order not found'. "An order remains active if OrderCancelRequest is rejected" -
checked through the order book, because 35=9 carries no symbol / quantity / price.
Teardown (fixture `trading`): the still active order is cancelled and the cancel report is checked.
"""
from dataclasses import replace

from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_cancel_reject, check_execution_report
from framework.fix.tags import CxlRejResponseTo, ExecType, OrdStatus, Side
from test_data.orders import passive_buy
from tests.support.book import check_order_rests


def _place_resting_buy(trading, instrument):
    request = passive_buy(instrument)
    with step(f"Precondition: place BUY {request.order_qty} {instrument} @ {request.price}"):
        order, report = trading.place(request)
        check_execution_report(report, "ExecutionReport for NewOrderSingle",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price)
    return order, request


def test_cancel_of_cancelled_order_is_rejected(market, trading):
    """A terminated (cancelled) order cannot be cancelled again."""
    instrument = market.main
    order, request = _place_resting_buy(trading, instrument)
    with step("Precondition: cancel the order"):
        report = trading.cancel(order)
        check_execution_report(report, "ExecutionReport for first cancel",
                               order_id=order.order_id, exec_type=ExecType.CANCELED, ord_status=OrdStatus.CANCELED,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price)

    with step("Send OrderCancelRequest again"):
        reject = trading.cancel(order)
    with step("Check OrderCancelReject: 'order not found'"):
        check_cancel_reject(reject, "OrderCancelReject for second cancel",
                            order_id=order.order_id, ord_status=OrdStatus.REJECTED,
                            cxl_rej_response_to=CxlRejResponseTo.ORDER_CANCEL_REQUEST, text="order not found",
                            orig_cl_ord_id=order.cl_ord_id)


def test_cancel_with_unknown_order_id_is_rejected(market, trading, market_data):
    """Well-formed OrderID / OrigClOrdID that match no order: rejected, and the real order stays untouched."""
    instrument = market.main
    order, request = _place_resting_buy(trading, instrument)
    unknown_order_id, unknown_cl_ord_id = "999999999999999999", "ffffffffffffffff"   # venue's id formats
    with step(f"Send OrderCancelRequest with OrderID {unknown_order_id} that does not exist"):
        reject = trading.cancel_with_ids(order, order_id=unknown_order_id, orig_cl_ord_id=unknown_cl_ord_id)
    with step("Check OrderCancelReject: 'order not found'"):
        check_cancel_reject(reject, "OrderCancelReject for unknown order",
                            order_id=PRESENT, ord_status=OrdStatus.REJECTED,
                            cxl_rej_response_to=CxlRejResponseTo.ORDER_CANCEL_REQUEST, text="order not found",
                            orig_cl_ord_id=unknown_cl_ord_id)
    with step("Check the real order still rests in the book unchanged"):
        check_order_rests(market_data.snapshot(instrument.symbol), Side.BUY, request.price, request.order_qty,
                          "Book after rejected cancel")


def test_cancel_with_wrong_side_is_rejected(market, trading, market_data):
    """Side (54) must match the original order: a SELL cancel for a BUY order is rejected."""
    instrument = market.main
    order, request = _place_resting_buy(trading, instrument)
    wrong_side = replace(order, side=Side.SELL, history=[])
    with step("Send OrderCancelRequest with Side=SELL for the BUY order"):
        reject = trading.cancel(wrong_side)
    with step("Check OrderCancelReject: 'order not found'"):
        check_cancel_reject(reject, "OrderCancelReject for wrong side",
                            order_id=order.order_id, ord_status=OrdStatus.REJECTED,
                            cxl_rej_response_to=CxlRejResponseTo.ORDER_CANCEL_REQUEST, text="order not found")
    with step("Check the order still rests in the book unchanged"):
        check_order_rests(market_data.snapshot(instrument.symbol), Side.BUY, request.price, request.order_qty,
                          "Book after rejected cancel")
