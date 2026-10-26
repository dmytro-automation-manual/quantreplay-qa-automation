"""Day, GoodTillCancel and GoodTillDate: orders that rest in the book until cancelled or expired.

Precondition: empty book. Teardown (fixture `trading`): the order is cancelled and the cancel report is checked.
"""
import pytest
from allure import step

from framework.assertions.expect import PRESENT
from framework.assertions.trading import check_execution_report
from framework.fix.tags import ExecType, OrdStatus, Side, TimeInForce
from test_data.orders import expire_date, passive_buy
from tests.support.book import check_order_rests


@pytest.mark.parametrize("tif, extra", [
    (TimeInForce.DAY, {}),
    (TimeInForce.GOOD_TILL_CANCEL, {}),
    (TimeInForce.GOOD_TILL_DATE, {"expire_date": expire_date(days_from_today=2)}),
], ids=["Day", "GoodTillCancel", "GoodTillDate"])
def test_resting_time_in_force_is_accepted_and_rests(market, trading, market_data, tif, extra):
    """The order is acknowledged as New with the requested TimeInForce and is visible in the book."""
    instrument = market.main
    request = passive_buy(instrument, tif=tif, **extra)
    with step(f"Send BUY {request.order_qty} {instrument} @ {request.price} TimeInForce={tif} {extra or ''}"):
        _, report = trading.place(request)
    with step("Check ExecutionReport: New, TimeInForce echoed"):
        check_execution_report(report, f"ExecutionReport for {tif.name} order",
                               order_id=PRESENT, exec_type=ExecType.NEW, ord_status=OrdStatus.NEW,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price,
                               time_in_force=tif, leaves_qty=request.order_qty, cum_qty=0,
                               **({"expire_date": extra["expire_date"]} if extra else {}))
    with step("Check the order rests in the book"):
        check_order_rests(market_data.snapshot(instrument.symbol), Side.BUY, request.price, request.order_qty,
                          f"Book with {tif.name} order")


# GoodTillDate needs exactly one of ExpireDate (432) / ExpireTime (126), in the future.
# Note: the RoE reject table names these rows "GoodTillCancel"; the field definitions (432/126 "conditionally
# required if TimeInForce = GTD") and the venue apply them to GoodTillDate.
@pytest.mark.parametrize("extra, text", [
    ({}, "neither expire date nor expire time specified"),
    ({"expire_date": expire_date(2), "expire_time": "20991231-10:00:00"}, "both expire date and expire time specified"),
    ({"expire_date": "20200101"}, "order already expired"),
], ids=["no-expiry", "date-and-time", "date-in-past"])
def test_good_till_date_with_invalid_expiry_is_rejected(market, trading, extra, text):
    instrument = market.main
    request = passive_buy(instrument, tif=TimeInForce.GOOD_TILL_DATE, **extra)
    with step(f"Send GoodTillDate BUY {instrument} with {extra or 'no ExpireDate / ExpireTime'}"):
        _, report = trading.place(request)
    with step(f"Check ExecutionReport: Rejected, '{text}'"):
        check_execution_report(report, "ExecutionReport for GoodTillDate with invalid expiry",
                               order_id=PRESENT, exec_type=ExecType.REJECTED, ord_status=OrdStatus.REJECTED,
                               symbol=instrument.symbol, order_qty=request.order_qty, price=request.price,
                               time_in_force=TimeInForce.GOOD_TILL_DATE, text=text)
