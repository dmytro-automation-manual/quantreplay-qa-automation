import pytest

pytestmark = pytest.mark.fix

BUY = 1
# Far below market so the order rests on the book and is not matched by random orders.
PASSIVE_PRICE = "0.01"


@pytest.mark.smoke
def test_new_limit_order_is_accepted(fix, symbol):
    cl_ord_id, er = fix.new_order(symbol, BUY, qty=10, price=PASSIVE_PRICE)

    assert er.get(35) == b"8"
    assert er.get(150) == b"0"   # ExecType = New
    assert er.get(39) == b"0"    # OrdStatus = New
    assert er.get(55) == symbol.encode()
    assert er.get(38) == b"10"
    assert er.get(151) == b"10"  # LeavesQty
    assert er.get(14) == b"0"    # CumQty
    assert er.get(37)            # OrderID assigned

    fix.cancel_order(cl_ord_id, er.get(37).decode(), symbol, BUY)


def test_replace_order_price(fix, symbol):
    cl_ord_id, er = fix.new_order(symbol, BUY, qty=10, price=PASSIVE_PRICE)
    order_id = er.get(37).decode()

    new_id, er = fix.replace_order(cl_ord_id, order_id, symbol, BUY, qty=10, price="0.02")

    assert er.get(35) == b"8"
    assert er.get(150) == b"5"   # ExecType = Replaced
    assert er.get(39) == b"5"    # OrdStatus = Replaced
    assert er.get(44) == b"0.02"
    assert er.get(37).decode() == order_id

    fix.cancel_order(new_id, order_id, symbol, BUY)


def test_cancel_order(fix, symbol):
    cl_ord_id, er = fix.new_order(symbol, BUY, qty=10, price=PASSIVE_PRICE)
    order_id = er.get(37).decode()

    _, er = fix.cancel_order(cl_ord_id, order_id, symbol, BUY)

    assert er.get(35) == b"8"
    assert er.get(150) == b"4"   # ExecType = Canceled
    assert er.get(39) == b"4"    # OrdStatus = Canceled
    assert er.get(151) == b"0"
    assert er.get(41) == cl_ord_id.encode()
