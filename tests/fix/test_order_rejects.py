"""New order and cancel rejects, per FIX Rules of Engagement."""
import pytest

from framework.fix_client import new_cl_ord_id, utc_ts

pytestmark = pytest.mark.fix

BUY = 1


def assert_rejected(er, text):
    assert er.get(35) == b"8"
    assert er.get(150) == b"8"   # ExecType = Rejected
    assert er.get(39) == b"8"    # OrdStatus = Rejected
    assert er.get(58).decode() == text


def test_unknown_symbol_is_rejected(fix):
    _, er = fix.new_order("NOSUCHSYM", BUY, qty=10, price="0.01")

    assert_rejected(er, "listing not found")


def test_limit_order_without_price_is_rejected(fix, symbol):
    cl_ord_id = new_cl_ord_id()
    fix.send("D", [(11, cl_ord_id), (55, symbol), (54, BUY), (60, utc_ts()),
                   (40, 2), (38, 10), (59, 0)])

    assert_rejected(fix.execution_report(cl_ord_id), "order price missing")


def test_market_order_with_price_is_rejected(fix, symbol):
    _, er = fix.new_order(symbol, BUY, qty=10, price="0.01", ord_type=1, tif=3)

    assert_rejected(er, "order price is not allowed")


def test_cancel_already_cancelled_order_is_rejected(fix, symbol):
    cl_ord_id, er = fix.new_order(symbol, BUY, qty=10, price="0.01")
    order_id = er.get(37).decode()
    cancel_id, _ = fix.cancel_order(cl_ord_id, order_id, symbol, BUY)

    _, rej = fix.cancel_order(cancel_id, order_id, symbol, BUY)

    assert rej.get(35) == b"9"   # OrderCancelReject
    assert rej.get(434) == b"1"  # CxlRejResponseTo = OrderCancelRequest
    assert rej.get(39) == b"8"   # OrdStatus = Rejected
    assert rej.get(58).decode() == "order not found"
