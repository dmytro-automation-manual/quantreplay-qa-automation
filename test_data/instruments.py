"""Reference instruments of the XETRA test venue - real Xetra data (close of 23.10.2026).

This is the expected configuration: the same values are loaded into the test database
(sim-run/db/real_market_overrides.sql), and the DB/REST tests check that the venue really has them.

Tick sizes:
  AMZ, MSF, NFC, VODI - non-EU shares on Xetra, liquidity band 11 (WM tick table S):
      0-9.999: 0.001 | 10-49.995: 0.005 | 50-99.99: 0.01 | >=100: 0.05
  VOW - EU share, ESMA RTS 11 tick table, liquidity band 5, price 50-100: 0.02
Quantities: lot size 1 share; qty_maximum is a fat-finger limit of roughly EUR 3-5M per order.
"""
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

D = Decimal


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    isin: str
    currency: str
    security_exchange: str
    tick_size: Decimal
    qty_minimum: Decimal
    qty_maximum: Decimal
    qty_multiple: Decimal
    bid: Decimal
    mid: Decimal
    offer: Decimal
    round_lot: Decimal          # typical order size used by tests (~EUR 5-20k)

    def __str__(self) -> str:   # readable pytest ids: test_x[AMZ]
        return self.symbol


AMZ = Instrument("AMZ", "Amazon.com Inc.", "US0231351067", "EUR", "XETR", D("0.05"),
                 D(1), D(20000), D(1), D("222.50"), D("222.55"), D("222.60"), D(50))
MSF = Instrument("MSF", "Microsoft Corp.", "US5949181045", "EUR", "XETR", D("0.05"),
                 D(1), D(10000), D(1), D("468.85"), D("468.90"), D("468.95"), D(20))
NFC = Instrument("NFC", "Netflix Inc.", "US64110L1061", "EUR", "XETR", D("0.01"),
                 D(1), D(50000), D(1), D("59.57"), D("59.58"), D("59.59"), D(200))
VODI = Instrument("VODI", "Vodafone Group plc", "GB00BH4HKS39", "EUR", "XETR", D("0.001"),
                  D(1), D(2000000), D(1), D("1.409"), D("1.410"), D("1.411"), D(5000))
VOW = Instrument("VOW", "Volkswagen AG St.", "DE0007664005", "EUR", "XETR", D("0.02"),
                 D(1), D(50000), D(1), D("68.68"), D("68.70"), D("68.72"), D(150))

INSTRUMENTS = (AMZ, MSF, NFC, VODI, VOW)
UNKNOWN_SYMBOL = "NOSUCHSYM"


# --- prices ----------------------------------------------------------------------------------------
def floor_to_tick(price: Decimal, tick: Decimal) -> Decimal:
    return (price / tick).to_integral_value(ROUND_FLOOR) * tick


def ceil_to_tick(price: Decimal, tick: Decimal) -> Decimal:
    return (price / tick).to_integral_value(ROUND_CEILING) * tick


def passive_buy_price(i: Instrument) -> Decimal:
    """A valid bid ~10% below the market: rests in the book and is never matched by another bid/ask."""
    return floor_to_tick(i.bid * D("0.90"), i.tick_size)


def passive_sell_price(i: Instrument) -> Decimal:
    """A valid offer ~10% above the market."""
    return ceil_to_tick(i.offer * D("1.10"), i.tick_size)


def ticks_away(price: Decimal, i: Instrument, ticks: int) -> Decimal:
    return price + i.tick_size * ticks


def off_tick_price(i: Instrument) -> Decimal:
    """Half a tick off the valid grid - must be rejected by the price tick check."""
    return passive_buy_price(i) + i.tick_size / 2
