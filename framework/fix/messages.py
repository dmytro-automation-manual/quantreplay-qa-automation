"""FIX message mapping: models -> (tag, value) fields, raw messages -> models.

Layer rule: pure functions. Knows the FIX dictionary and the models, not the socket or the tests.
"""
import datetime
import uuid
from decimal import Decimal

import simplefix

from framework.fix.tags import (CxlRejResponseTo, ExecType, MDEntryType, MDReqRejReason, MDUpdateAction,
                                MDUpdateType, MsgType, OrdStatus, OrdType, Side, SubscriptionRequestType, Tag,
                                TimeInForce)
from framework.models.market_data import (MarketDataIncremental, MarketDataReject, MarketDataRequest,
                                          MarketDataSnapshot, MDEntry)
from framework.models.orders import ExecutionReport, NewOrderRequest, Order, OrderCancelReject

Fields = list[tuple[int, object]]


def new_id() -> str:
    """Unique ClOrdID / MDReqID."""
    return uuid.uuid4().hex[:16]


def transact_time() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]


# --- outgoing --------------------------------------------------------------------------------------
def new_order_single(order: NewOrderRequest, cl_ord_id: str, transact_time: str) -> Fields:
    return [(Tag.CL_ORD_ID, cl_ord_id), (Tag.SYMBOL, order.symbol), (Tag.SIDE, order.side.value),
            (Tag.TRANSACT_TIME, transact_time), (Tag.ORD_TYPE, order.ord_type.value),
            (Tag.PRICE, order.price), (Tag.ORDER_QTY, order.order_qty),
            (Tag.TIME_IN_FORCE, order.time_in_force.value if order.time_in_force else None),
            (Tag.EXPIRE_DATE, order.expire_date), (Tag.EXPIRE_TIME, order.expire_time)]


def order_cancel_replace_request(order: Order, cl_ord_id: str, transact_time: str, *,
                                 order_qty: Decimal, price: Decimal | None,
                                 time_in_force: TimeInForce | None) -> Fields:
    return [(Tag.ORIG_CL_ORD_ID, order.cl_ord_id), (Tag.CL_ORD_ID, cl_ord_id), (Tag.ORDER_ID, order.order_id),
            (Tag.SYMBOL, order.symbol), (Tag.SIDE, order.side.value), (Tag.TRANSACT_TIME, transact_time),
            (Tag.ORD_TYPE, order.ord_type.value), (Tag.PRICE, price), (Tag.ORDER_QTY, order_qty),
            (Tag.TIME_IN_FORCE, time_in_force.value if time_in_force else None)]


def order_cancel_request(order: Order, cl_ord_id: str, transact_time: str) -> Fields:
    return [(Tag.ORIG_CL_ORD_ID, order.cl_ord_id), (Tag.CL_ORD_ID, cl_ord_id), (Tag.ORDER_ID, order.order_id),
            (Tag.SYMBOL, order.symbol), (Tag.SIDE, order.side.value), (Tag.TRANSACT_TIME, transact_time)]


def market_data_request(request: MarketDataRequest, md_req_id: str) -> Fields:
    fields: Fields = [(Tag.MD_REQ_ID, md_req_id), (Tag.SUBSCRIPTION_REQUEST_TYPE, request.subscription.value),
                      (Tag.MARKET_DEPTH, request.market_depth)]
    if request.subscription == SubscriptionRequestType.SUBSCRIBE:
        update_type = MDUpdateType.INCREMENTAL_REFRESH if request.incremental else MDUpdateType.FULL_REFRESH
        fields.append((Tag.MD_UPDATE_TYPE, update_type.value))
    fields.append((Tag.NO_MD_ENTRY_TYPES, len(request.entry_types)))
    fields += [(Tag.MD_ENTRY_TYPE, t.value) for t in request.entry_types]
    symbols = request.symbol if isinstance(request.symbol, tuple) else (request.symbol,)
    fields.append((Tag.NO_RELATED_SYM, len(symbols)))
    fields += [(Tag.SYMBOL, s) for s in symbols]
    return fields


# --- incoming --------------------------------------------------------------------------------------
def _str(msg: simplefix.FixMessage, tag: int, nth: int = 1) -> str | None:
    value = msg.get(tag, nth)
    return value.decode() if value is not None else None


def _dec(msg: simplefix.FixMessage, tag: int, nth: int = 1) -> Decimal | None:
    value = _str(msg, tag, nth)
    return Decimal(value) if value is not None else None


def _enum(enum_cls, msg: simplefix.FixMessage, tag: int, nth: int = 1):
    value = _str(msg, tag, nth)
    return enum_cls(value) if value is not None else None


def msg_type(msg: simplefix.FixMessage) -> str:
    return _str(msg, Tag.MSG_TYPE)


def execution_report(msg: simplefix.FixMessage) -> ExecutionReport:
    return ExecutionReport(
        msg_type=MsgType(_str(msg, Tag.MSG_TYPE)),
        order_id=_str(msg, Tag.ORDER_ID), cl_ord_id=_str(msg, Tag.CL_ORD_ID),
        orig_cl_ord_id=_str(msg, Tag.ORIG_CL_ORD_ID), exec_id=_str(msg, Tag.EXEC_ID),
        exec_type=_enum(ExecType, msg, Tag.EXEC_TYPE), ord_status=_enum(OrdStatus, msg, Tag.ORD_STATUS),
        symbol=_str(msg, Tag.SYMBOL), side=_enum(Side, msg, Tag.SIDE),
        order_qty=_dec(msg, Tag.ORDER_QTY), price=_dec(msg, Tag.PRICE),
        ord_type=_enum(OrdType, msg, Tag.ORD_TYPE), time_in_force=_enum(TimeInForce, msg, Tag.TIME_IN_FORCE),
        leaves_qty=_dec(msg, Tag.LEAVES_QTY), cum_qty=_dec(msg, Tag.CUM_QTY), avg_px=_dec(msg, Tag.AVG_PX),
        last_px=_dec(msg, Tag.LAST_PX), last_qty=_dec(msg, Tag.LAST_QTY),
        expire_date=_str(msg, Tag.EXPIRE_DATE), text=_str(msg, Tag.TEXT))


def order_cancel_reject(msg: simplefix.FixMessage) -> OrderCancelReject:
    return OrderCancelReject(
        msg_type=MsgType(_str(msg, Tag.MSG_TYPE)),
        order_id=_str(msg, Tag.ORDER_ID), cl_ord_id=_str(msg, Tag.CL_ORD_ID),
        orig_cl_ord_id=_str(msg, Tag.ORIG_CL_ORD_ID), ord_status=_enum(OrdStatus, msg, Tag.ORD_STATUS),
        cxl_rej_response_to=_enum(CxlRejResponseTo, msg, Tag.CXL_REJ_RESPONSE_TO), text=_str(msg, Tag.TEXT))


def _md_entries(msg: simplefix.FixMessage, with_action: bool) -> tuple[MDEntry, ...]:
    """Repeating group 268: entries are read in order; optional tags are matched by position."""
    entries, current = [], None
    for tag, value in msg.pairs:
        tag, value = int(tag), value.decode()
        if tag == Tag.MD_UPDATE_ACTION and with_action:
            if current is not None:
                entries.append(current)
            current = {"update_action": MDUpdateAction(value)}
        elif tag == Tag.MD_ENTRY_TYPE:
            if current is not None and "entry_type" in current:
                entries.append(current)
                current = None
            current = (current or {}) | {"entry_type": MDEntryType(value)}
        elif current is not None and tag == Tag.MD_ENTRY_PX:
            current["price"] = Decimal(value)
        elif current is not None and tag == Tag.MD_ENTRY_SIZE:
            current["size"] = Decimal(value)
        elif current is not None and tag == Tag.MD_ENTRY_ID:
            current["entry_id"] = value
    if current is not None:
        entries.append(current)
    return tuple(MDEntry(entry_type=e["entry_type"], price=e.get("price"), size=e.get("size"),
                         entry_id=e.get("entry_id"), update_action=e.get("update_action")) for e in entries)


def market_data_snapshot(msg: simplefix.FixMessage) -> MarketDataSnapshot:
    return MarketDataSnapshot(msg_type=MsgType(_str(msg, Tag.MSG_TYPE)), md_req_id=_str(msg, Tag.MD_REQ_ID),
                              symbol=_str(msg, Tag.SYMBOL), entries=_md_entries(msg, with_action=False))


def market_data_incremental(msg: simplefix.FixMessage) -> MarketDataIncremental:
    return MarketDataIncremental(msg_type=MsgType(_str(msg, Tag.MSG_TYPE)), md_req_id=_str(msg, Tag.MD_REQ_ID),
                                 entries=_md_entries(msg, with_action=True))


def market_data_reject(msg: simplefix.FixMessage) -> MarketDataReject:
    return MarketDataReject(msg_type=MsgType(_str(msg, Tag.MSG_TYPE)), md_req_id=_str(msg, Tag.MD_REQ_ID),
                            reason=_enum(MDReqRejReason, msg, Tag.MD_REQ_REJ_REASON), text=_str(msg, Tag.TEXT))
