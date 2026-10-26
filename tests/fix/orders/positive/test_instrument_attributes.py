"""NewOrderSingle with the optional instrument attributes (RoE "Instrument Resolution", lookup by Symbol).

SecurityType (167), SecurityExchange (207) and Currency (15) must equal the listing's values.
Currency means the currency of the price for shares and the currency of the quantity for FX:
XETRA AMZ -> EUR (price), FASTMATCH EUR/USD -> EUR (base currency, not the quote currency USD).
Teardown (fixture `trading`): the order is cancelled and the cancel report is checked.
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus
from test_data.orders import passive_buy


@pytest.mark.smoke
def test_order_with_all_instrument_attributes_is_accepted(trading, instrument):
    request = passive_buy(instrument, security_type=instrument.security_type,
                          security_exchange=instrument.security_exchange, currency=instrument.order_currency)
    with step(f"Send BUY {request.order_qty} {instrument} @ {request.price} with SecurityType="
              f"{request.security_type}, SecurityExchange={request.security_exchange}, Currency={request.currency}"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: New"):
        check_execution_report(report, "ExecutionReport for order with instrument attributes",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price)
