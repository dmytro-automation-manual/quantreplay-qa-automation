"""IOC / FOK without matching liquidity (price far below the market)."""
import pytest

pytestmark = pytest.mark.fix

BUY = 1
NO_LIQUIDITY_PRICE = "0.01"
IOC, FOK = 3, 4


def test_ioc_without_liquidity_is_cancelled(fix, symbol):
    _, er = fix.new_order(symbol, BUY, qty=10, price=NO_LIQUIDITY_PRICE, tif=IOC)

    assert er.get(150) == b"4"   # ExecType = Canceled
    assert er.get(39) == b"4"    # OrdStatus = Canceled
    assert er.get(14) == b"0"
    assert er.get(58).decode() == "no facing orders found"


def test_fok_without_liquidity_is_cancelled(fix, symbol):
    _, er = fix.new_order(symbol, BUY, qty=10, price=NO_LIQUIDITY_PRICE, tif=FOK)

    assert er.get(150) == b"4"
    assert er.get(39) == b"4"
    assert er.get(58).decode() == "no facing orders found"
