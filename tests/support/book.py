"""Order book checks through market data: the only way a FIX client can see that an order still rests."""
from decimal import Decimal

from framework.assertions.expect import check_fields, check_true
from framework.fix.tags import MDEntryType, Side
from framework.models.market_data import MarketDataSnapshot


def entry_type_for(side: Side) -> MDEntryType:
    return MDEntryType.BID if side == Side.BUY else MDEntryType.OFFER


def check_order_rests(snapshot: MarketDataSnapshot, side: Side, price: Decimal, qty: Decimal, title: str) -> None:
    """The book shows exactly one entry at the price on that side, with the order's quantity."""
    entries = [e for e in snapshot.side(entry_type_for(side)) if e.price == price]
    check_true(f"{title}: one {entry_type_for(side).name} at {price}", len(entries) == 1, f"found {len(entries)}")
    check_fields(title, entries[0], {"entry_type": entry_type_for(side), "price": price, "size": qty})


def check_book_empty(snapshot: MarketDataSnapshot, title: str) -> None:
    check_true(title, not snapshot.entries, f"entries: {list(snapshot.entries)}")
