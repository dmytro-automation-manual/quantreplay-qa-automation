"""NewOrderSingle rejects (Rules of Engagement, "New Order Single" rejection reasons).

Every reject is an ExecutionReport with ExecType=Rejected, OrdStatus=Rejected and the documented Text.
Precondition: empty order books. Teardown: nothing to undo - a rejected order never enters the book
(the fixture `trading` still cancels anything that was unexpectedly accepted).
"""
from dataclasses import replace

from allure import step

from framework.assertions.expect import ABSENT, PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus, OrdType, Side, TimeInForce
from framework.models.orders import NewOrderRequest
from test_data.instruments import UNKNOWN_SYMBOL, passive_buy_price
from test_data.orders import passive_buy


def test_unknown_symbol_is_rejected(market, trading):
    """An order for a symbol that is not listed on the venue is rejected: 'listing not found'."""
    instrument = market.main
    request = replace(passive_buy(instrument), symbol=UNKNOWN_SYMBOL)
    with step(f"Send NewOrderSingle for {UNKNOWN_SYMBOL}"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, 'listing not found'"):
        check_execution_report(report, "ExecutionReport for unknown symbol",
                               order_id=PRESENT, exec_type=ExecType.REJECTED, ord_status=OrdStatus.REJECTED,
                               symbol=UNKNOWN_SYMBOL, order_qty=request.order_qty, price=request.price,
                               text="listing not found")


def test_limit_order_without_price_is_rejected(market, trading):
    """A limit order must carry Price (44): 'order price missing'."""
    instrument = market.main
    request = NewOrderRequest(symbol=instrument.symbol, side=Side.BUY, order_qty=instrument.round_lot, price=None)
    with step(f"Send limit NewOrderSingle {instrument} without Price (44)"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, 'order price missing'"):
        check_execution_report(report, "ExecutionReport for limit order without price",
                               order_id=PRESENT, exec_type=ExecType.REJECTED, ord_status=OrdStatus.REJECTED,
                               symbol=instrument.symbol, order_qty=instrument.round_lot, price=ABSENT,
                               text="order price missing")


def test_market_order_with_price_is_rejected(market, trading):
    """A market order must not carry Price (44): 'order price is not allowed'."""
    instrument = market.main
    price = passive_buy_price(instrument)
    request = NewOrderRequest(symbol=instrument.symbol, side=Side.BUY, order_qty=instrument.round_lot, price=price,
                              ord_type=OrdType.MARKET, time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL)
    with step(f"Send market NewOrderSingle {instrument} with Price {price}"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, 'order price is not allowed'"):
        check_execution_report(report, "ExecutionReport for market order with price",
                               order_id=PRESENT, exec_type=ExecType.REJECTED, ord_status=OrdStatus.REJECTED,
                               symbol=instrument.symbol, order_qty=instrument.round_lot, price=price,
                               text="order price is not allowed")


def test_order_without_quantity_is_rejected(market, trading):
    """OrderQty (38) is mandatory: 'order quantity missing'."""
    instrument = market.main
    price = passive_buy_price(instrument)
    request = NewOrderRequest(symbol=instrument.symbol, side=Side.BUY, order_qty=None, price=price)
    with step(f"Send NewOrderSingle {instrument} @ {price} without OrderQty (38)"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, 'order quantity missing'"):
        check_execution_report(report, "ExecutionReport for order without quantity",
                               order_id=PRESENT, exec_type=ExecType.REJECTED, ord_status=OrdStatus.REJECTED,
                               symbol=instrument.symbol, order_qty=ABSENT, price=price,
                               text="order quantity missing")
