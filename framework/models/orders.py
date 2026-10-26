"""Order entry models: what the client sends and what the venue answers. Plain data, no behaviour."""
from dataclasses import dataclass, field
from decimal import Decimal

from framework.fix.tags import CxlRejResponseTo, ExecType, MsgType, OrdStatus, OrdType, Side, TimeInForce


@dataclass(frozen=True)
class NewOrderRequest:
    """NewOrderSingle (35=D). None means "tag not sent" - used by negative tests (e.g. no price)."""
    symbol: str
    side: Side
    order_qty: Decimal | None
    price: Decimal | None
    ord_type: OrdType = OrdType.LIMIT
    time_in_force: TimeInForce | None = TimeInForce.DAY
    expire_date: str | None = None         # YYYYMMDD, local market date
    expire_time: str | None = None         # YYYYMMDD-HH:MM:SS, UTC
    security_type: str | None = None       # optional instrument attributes: the venue resolves the listing
    security_exchange: str | None = None   # by Symbol and checks every attribute that is sent
    currency: str | None = None            # FX: currency of the quantity (base currency)


@dataclass
class Order:
    """A live order on the venue as known by the client: updated on every accepted replace/fill/cancel."""
    order_id: str
    cl_ord_id: str                         # ClOrdID of the last accepted request (next OrigClOrdID)
    symbol: str
    side: Side
    order_qty: Decimal
    price: Decimal | None
    ord_type: OrdType
    time_in_force: TimeInForce | None
    ord_status: OrdStatus
    history: list = field(default_factory=list, repr=False)   # all execution reports, oldest first


@dataclass(frozen=True)
class ExecutionReport:
    """ExecutionReport (35=8)."""
    msg_type: MsgType
    order_id: str | None
    cl_ord_id: str | None
    orig_cl_ord_id: str | None
    exec_id: str | None
    exec_type: ExecType
    ord_status: OrdStatus
    symbol: str | None
    side: Side | None
    order_qty: Decimal | None
    price: Decimal | None
    ord_type: OrdType | None
    time_in_force: TimeInForce | None
    leaves_qty: Decimal | None
    cum_qty: Decimal | None
    avg_px: Decimal | None
    last_px: Decimal | None
    last_qty: Decimal | None
    expire_date: str | None
    text: str | None


@dataclass(frozen=True)
class OrderCancelReject:
    """OrderCancelReject (35=9): the answer to a rejected cancel or replace request."""
    msg_type: MsgType
    order_id: str | None
    cl_ord_id: str | None
    orig_cl_ord_id: str | None
    ord_status: OrdStatus
    cxl_rej_response_to: CxlRejResponseTo
    text: str | None
