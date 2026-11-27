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
  Quantities in the base currency, own limits per pair (min .. max by multiple):
      EUR/USD 10 000 .. 100 000 000 by 1 000 | GBP/USD 25 000 .. 50 000 000 by 5 000
      USD/JPY 50 000 .. 75 000 000 by 10 000 | USD/CHF  5 000 .. 25 000 000 by 1 000
      EUR/GBP 100 000 .. 20 000 000 by 50 000

Every listing has its own profile: one extra identifier (CUSIP / SEDOL / RIC / exchange symbol / Bloomberg)
and its own random order generator settings (the generator stays off: random_orders_enabled = false).
No listing has a party (party_id / party_role are NULL).
"""
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

D = Decimal


@dataclass(frozen=True)
class RandomOrders:
    """Random order generator settings of a listing (sim.listing.random_*); amounts are in the price currency.

    Venue rule (found by experiment, not in the documentation): amt_minimum / price must not exceed
    qty_minimum, otherwise the generator places no orders at all - every profile below keeps it.
    """
    qty_minimum: Decimal
    qty_maximum: Decimal
    amt_minimum: Decimal
    amt_maximum: Decimal
    aggressive_qty_minimum: Decimal
    aggressive_qty_maximum: Decimal
    aggressive_amt_minimum: Decimal
    aggressive_amt_maximum: Decimal
    depth_levels: int
    spread: Decimal
    rate: int
    tick_range: int


def _rnd(qty: tuple[int, int], amt: tuple[int, int], aggressive_qty: tuple[int, int],
         aggressive_amt: tuple[int, int], depth: int, spread: str, rate: int, ticks: int) -> RandomOrders:
    return RandomOrders(D(qty[0]), D(qty[1]), D(amt[0]), D(amt[1]), D(aggressive_qty[0]), D(aggressive_qty[1]),
                        D(aggressive_amt[0]), D(aggressive_amt[1]), depth, D(spread), rate, ticks)


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
    default_qty: Decimal        # typical order size used by tests (~EUR 5-20k, 1M for FX)
    security_type: str = "CS"
    fx_base_currency: str | None = None     # FX only: currency of the quantity
    cusip: str | None = None                # extra identifiers: one per listing
    sedol: str | None = None
    ric: str | None = None
    exchange_symbol: str | None = None
    bloomberg_symbol: str | None = None
    party_id: str | None = None             # PartyID / PartyRole of the listing (none is set)
    party_role: str | None = None
    random: RandomOrders | None = None

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
                 D(1), D(20000), D(1), D("222.50"), D("222.55"), D("222.60"), D(50),
                 exchange_symbol="AMZ",
                 random=_rnd((10, 500), (2000, 100000), (5, 200), (1000, 40000), 7, "0.10", 3, 12))
MSF = Instrument("MSF", "Microsoft Corp.", "US5949181045", "EUR", "XETR", D("0.05"),
                 D(1), D(10000), D(1), D("468.85"), D("468.90"), D("468.95"), D(20),
                 bloomberg_symbol="MSF GY Equity",
                 random=_rnd((5, 250), (2000, 100000), (2, 100), (900, 45000), 6, "0.05", 2, 15))
NFC = Instrument("NFC", "Netflix Inc.", "US64110L1061", "EUR", "XETR", D("0.01"),
                 D(1), D(50000), D(1), D("59.57"), D("59.58"), D("59.59"), D(200),
                 ric="NFC.DE",
                 random=_rnd((20, 1000), (1000, 50000), (10, 400), (500, 20000), 8, "0.02", 4, 20))
VODI = Instrument("VODI", "Vodafone Group plc", "GB00BH4HKS39", "EUR", "XETR", D("0.001"),
                  D(1), D(2000000), D(1), D("1.409"), D("1.410"), D("1.411"), D(5000),
                  sedol="BH4HKS3",
                  random=_rnd((1000, 50000), (1200, 60000), (500, 20000), (600, 25000), 10, "0.002", 5, 25))
VOW = Instrument("VOW", "Volkswagen AG St.", "DE0007664005", "EUR", "XETR", D("0.02"),
                 D(1), D(50000), D(1), D("68.68"), D("68.70"), D("68.72"), D(150),
                 cusip="D94523145",
                 random=_rnd((20, 1000), (1300, 60000), (10, 400), (600, 25000), 5, "0.04", 2, 10))

XETRA_INSTRUMENTS = (AMZ, MSF, NFC, VODI, VOW)


def _fx(symbol: str, tick: str, bid: str, mid: str, offer: str, qty: tuple[int, int, int],
        random: RandomOrders, **identity: str) -> Instrument:
    """qty = (minimum, maximum, multiple) in the base currency."""
    base, quote = symbol.split("/")
    return Instrument(symbol, symbol, None, quote, "FASTMATCH", D(tick), D(qty[0]), D(qty[1]), D(qty[2]),
                      D(bid), D(mid), D(offer), D(1000000), security_type="FXSPOT", fx_base_currency=base,
                      random=random, **identity)


EUR_USD = _fx("EUR/USD", "0.00001", "1.11929", "1.11930", "1.11931", (10000, 100000000, 1000),
              _rnd((1000000, 10000000), (1000000, 10000000), (500000, 5000000), (500000, 5000000),
                   10, "0.00002", 8, 15), ric="EUR=")
GBP_USD = _fx("GBP/USD", "0.00001", "1.33682", "1.33683", "1.33684", (25000, 50000000, 5000),
              _rnd((500000, 5000000), (600000, 6000000), (250000, 2500000), (300000, 3000000),
                   8, "0.00003", 5, 12), bloomberg_symbol="GBPUSD Curncy")
USD_JPY = _fx("USD/JPY", "0.001", "156.802", "156.803", "156.804", (50000, 75000000, 10000),
              _rnd((1000000, 8000000), (150000000, 1200000000), (500000, 4000000), (75000000, 600000000),
                   8, "0.003", 6, 12), exchange_symbol="USDJPY")
USD_CHF = _fx("USD/CHF", "0.00001", "0.82434", "0.82435", "0.82436", (5000, 25000000, 1000),
              _rnd((200000, 3000000), (150000, 2400000), (100000, 1500000), (80000, 1200000),
                   6, "0.00003", 3, 10), ric="CHF=")
EUR_GBP = _fx("EUR/GBP", "0.00001", "0.83727", "0.83728", "0.83729", (100000, 20000000, 50000),
              _rnd((500000, 5000000), (400000, 4000000), (250000, 2000000), (200000, 1600000),
                   5, "0.00002", 2, 8), bloomberg_symbol="EURGBP Curncy")

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
