"""Price tick size of each listing (priceTickSize, values in test_data/instruments.py).

A price on the tick grid -> accepted; half a tick off the grid -> rejected, for new orders and for replaces.
Teardown (fixture `trading`): accepted orders are cancelled and the cancel report is checked.
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_cancel_reject, check_execution_report
from framework.fix.tags import CxlRejResponseTo, ExecType, OrdStatus, Side
from test_data.instruments import off_tick_price, passive_buy_price, ticks_away
from test_data.orders import passive_buy
from tests.support.book import check_order_rests

TEXT_WITHOUT_IS = ("Reject Text differs from RoE: the venue sends 'order price tick constraint violated', "
                   "RoE documents 'order price tick constraint is violated'")


def test_price_one_tick_from_valid_price_is_accepted(trading, instrument):
    """The smallest price step (one tick) is a valid price."""
    price = ticks_away(passive_buy_price(instrument), instrument, 1)
    request = passive_buy(instrument, price=price)
    with step(f"Send BUY {instrument} @ {price} (on the {instrument.tick_size} grid)"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: New"):
        check_execution_report(report, "ExecutionReport for price on tick",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=price)


@pytest.mark.smoke
@pytest.mark.known_issue(TEXT_WITHOUT_IS)
def test_new_order_price_off_tick_is_rejected(trading, instrument):
    """A price between two ticks is rejected and never reaches the book."""
    price = off_tick_price(instrument)
    request = passive_buy(instrument, price=price)
    with step(f"Send BUY {instrument} @ {price} (half a tick of {instrument.tick_size} off the grid)"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, price tick constraint"):
        check_execution_report(report, "ExecutionReport for price off tick",
                               order_id=PRESENT, exec_type=ExecType.REJECTED, ord_status=OrdStatus.REJECTED,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=price,
                               text="order price tick constraint is violated")


@pytest.mark.known_issue(TEXT_WITHOUT_IS + "; OrdStatus of the OrderCancelReject is the current one, not Rejected")
def test_replace_to_price_off_tick_is_rejected(trading, market_data, instrument):
    """A replace to an off-tick price is rejected and the order keeps its price."""
    request = passive_buy(instrument)
    with step(f"Precondition: place BUY {request.order_qty} {instrument} @ {request.price}"):
        order, report = trading.place(request)
        check_execution_report(report, "ExecutionReport for NewOrderSingle",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price)
    bad_price = off_tick_price(instrument)
    with step(f"Send OrderCancelReplaceRequest to {bad_price}"):
        reject = trading.replace(order, price=bad_price)
    with step("Check OrderCancelReject: price tick constraint"):
        check_cancel_reject(reject, "OrderCancelReject for replace off tick",
                            order_id=order.order_id, ord_status=OrdStatus.REJECTED,
                            cxl_rej_response_to=CxlRejResponseTo.ORDER_CANCEL_REPLACE_REQUEST,
                            text="order price tick constraint is violated")
    with step("Check the order keeps its original price in the book"):
        check_order_rests(market_data.snapshot(instrument.symbol), Side.BUY, request.price, request.order_qty,
                          "Book after rejected replace")
