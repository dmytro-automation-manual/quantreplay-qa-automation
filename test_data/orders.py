"""Order factories: tests describe intent ("passive limit buy"), the factory fills in valid defaults."""
import datetime
from decimal import Decimal

from framework.fix.tags import OrdType, Side, TimeInForce
from framework.models.orders import NewOrderRequest
from test_data.instruments import Instrument, passive_buy_price, passive_sell_price


def limit_order(instrument: Instrument, side: Side, *, qty: Decimal | None = None, price: Decimal | None = None,
                tif: TimeInForce | None = TimeInForce.DAY, **extra) -> NewOrderRequest:
    """Limit order; by default a round lot at a passive price (rests in the book, never trades)."""
    if price is None:
        price = passive_buy_price(instrument) if side == Side.BUY else passive_sell_price(instrument)
    return NewOrderRequest(symbol=instrument.symbol, side=side,
                           order_qty=qty if qty is not None else instrument.round_lot,
                           price=price, ord_type=OrdType.LIMIT, time_in_force=tif, **extra)


def passive_buy(instrument: Instrument, **kwargs) -> NewOrderRequest:
    return limit_order(instrument, Side.BUY, **kwargs)


def passive_sell(instrument: Instrument, **kwargs) -> NewOrderRequest:
    return limit_order(instrument, Side.SELL, **kwargs)


def market_order(instrument: Instrument, side: Side, *, qty: Decimal | None = None,
                 tif: TimeInForce = TimeInForce.IMMEDIATE_OR_CANCEL) -> NewOrderRequest:
    return NewOrderRequest(symbol=instrument.symbol, side=side,
                           order_qty=qty if qty is not None else instrument.round_lot,
                           price=None, ord_type=OrdType.MARKET, time_in_force=tif)


def expire_date(days_from_today: int) -> str:
    """ExpireDate (432) in the venue's local date (the test venue runs in UTC)."""
    return (datetime.datetime.now(datetime.UTC).date() + datetime.timedelta(days=days_from_today)).strftime("%Y%m%d")
