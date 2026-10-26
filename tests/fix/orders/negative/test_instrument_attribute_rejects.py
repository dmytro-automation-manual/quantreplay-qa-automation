"""NewOrderSingle whose instrument attributes do not match the listing (RoE "Instrument Resolution").

"If any listing attribute differs from the one specified in a request, the listing no longer participates
in the resolution process" - no listing is found and the order is rejected: 'listing not found'.
For FX the quote currency is a wrong Currency (15): Currency is the currency of the quantity.
"""
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus
from test_data.orders import passive_buy


def _check_listing_not_found(report, instrument, request, title):
    check_execution_report(report, title, order_id=PRESENT, exec_type=ExecType.REJECTED,
                           ord_status=OrdStatus.REJECTED, symbol=instrument.symbol,
                           order_qty=request.order_qty, price=request.price, text="listing not found")


def test_wrong_currency_is_rejected(trading, instrument):
    request = passive_buy(instrument, currency=instrument.other_currency)
    with step(f"Send BUY {instrument} with Currency={request.currency} (listing: {instrument.order_currency})"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, 'listing not found'"):
        _check_listing_not_found(report, instrument, request, "ExecutionReport for wrong Currency")


def test_wrong_security_type_is_rejected(trading, instrument):
    wrong_type = "CS" if instrument.security_type == "FXSPOT" else "FXSPOT"
    request = passive_buy(instrument, security_type=wrong_type)
    with step(f"Send BUY {instrument} with SecurityType={wrong_type} (listing: {instrument.security_type})"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: Rejected, 'listing not found'"):
        _check_listing_not_found(report, instrument, request, "ExecutionReport for wrong SecurityType")
