"""Reference instruments of the test venues - real market data of 23.10.2026.

This is the expected configuration: the same values are loaded into the test database
(sim-run/db/real_market_overrides.sql), and the DB/REST tests check that the venues really have them.

XETRA (equities, Xetra close):
  Tick sizes: AMZ, MSF, NFC, VODI - non-EU shares, liquidity band 11 (WM tick table S):
      0-9.999: 0.001 | 10-49.995: 0.005 | 50-99.99: 0.01 | >=100: 0.05
  VOW - EU share, ESMA RTS 11 tick table, liquidity band 5, price 50-100: 0.02
  Quantities: lot size 1 share; qty_maximum is a fat-finger limit of roughly EUR 3-5M per order.

FASTMATCH (FX spot, ECB reference rates; GBP/USD, USD/JPY, USD/CHF are cross rates):
  Tick sizes: 5 decimals, JPY pairs 3 decimals. Bid / offer one tick around the mid.
  Quantities in the base currency: minimum 10 000, multiple of 1 000, fat-finger limit 50 000 000.
"""
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

D = Decimal


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    isin: str | None
    currency: str
    security_exchange: str
    tick_size: Decimal
    qty_minimum: Decimal
    qty_maximum: Decimal
    qty_multiple: Decimal
    bid: Decimal
    mid: Decimal
    offer: Decimal
    round_lot: Decimal          # typical order size used by tests (~EUR 5-20k, 1M for FX)
    security_type: str = "CS"
    fx_base_currency: str | None = None     # FX only: currency of the quantity

    def __str__(self) -> str:   # readable pytest ids: test_x[XETRA-AMZ]
        return self.symbol

    @property
    def order_currency(self) -> str:
        """Currency (15) in an order (RoE): currency of the quantity for FX, of the price otherwise."""
        return self.fx_base_currency or self.currency

    @property
    def other_currency(self) -> str:
        """A currency the listing is not quoted in: the quote currency for FX, USD for EUR shares."""
        return self.currency if self.fx_base_currency else "USD"


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

XETRA_INSTRUMENTS = (AMZ, MSF, NFC, VODI, VOW)


def _fx(symbol: str, tick: str, bid: str, mid: str, offer: str) -> Instrument:
    base, quote = symbol.split("/")
    return Instrument(symbol, symbol, None, quote, "FASTMATCH", D(tick), D(10000), D(50000000), D(1000),
                      D(bid), D(mid), D(offer), D(1000000), security_type="FXSPOT", fx_base_currency=base)


EUR_USD = _fx("EUR/USD", "0.00001", "1.11929", "1.11930", "1.11931")
GBP_USD = _fx("GBP/USD", "0.00001", "1.33682", "1.33683", "1.33684")
USD_JPY = _fx("USD/JPY", "0.001", "156.802", "156.803", "156.804")
USD_CHF = _fx("USD/CHF", "0.00001", "0.82434", "0.82435", "0.82436")
EUR_GBP = _fx("EUR/GBP", "0.00001", "0.83727", "0.83728", "0.83729")

FASTMATCH_INSTRUMENTS = (EUR_USD, GBP_USD, USD_JPY, USD_CHF, EUR_GBP)
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
