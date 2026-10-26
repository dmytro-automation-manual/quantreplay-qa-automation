"""FIX 5.0 SP2 tags and enumerations used by the simulator (see its FIX Rules of Engagement).

Layer rule: pure constants, no imports from the framework.
"""
from enum import Enum, IntEnum


class FixEnum(str, Enum):
    """Enum whose value is the FIX wire value; prints as NAME(value) in assertion tables."""

    def __str__(self) -> str:
        return f"{self.name}({self.value})"

    __repr__ = __str__


class Tag(IntEnum):
    AVG_PX = 6
    CL_ORD_ID = 11
    CUM_QTY = 14
    CURRENCY = 15
    EXEC_ID = 17
    LAST_PX = 31
    LAST_QTY = 32
    MSG_TYPE = 35
    ORDER_ID = 37
    ORDER_QTY = 38
    ORD_STATUS = 39
    ORD_TYPE = 40
    ORIG_CL_ORD_ID = 41
    PRICE = 44
    SIDE = 54
    SYMBOL = 55
    TEXT = 58
    TIME_IN_FORCE = 59
    TRANSACT_TIME = 60
    EXPIRE_TIME = 126
    NO_RELATED_SYM = 146
    EXEC_TYPE = 150
    SECURITY_TYPE = 167
    SECURITY_EXCHANGE = 207
    LEAVES_QTY = 151
    MD_REQ_ID = 262
    SUBSCRIPTION_REQUEST_TYPE = 263
    MARKET_DEPTH = 264
    MD_UPDATE_TYPE = 265
    NO_MD_ENTRY_TYPES = 267
    NO_MD_ENTRIES = 268
    MD_ENTRY_TYPE = 269
    MD_ENTRY_PX = 270
    MD_ENTRY_SIZE = 271
    MD_ENTRY_ID = 278
    MD_UPDATE_ACTION = 279
    MD_REQ_REJ_REASON = 281
    EXPIRE_DATE = 432
    CXL_REJ_RESPONSE_TO = 434


class MsgType(FixEnum):
    EXECUTION_REPORT = "8"
    ORDER_CANCEL_REJECT = "9"
    NEW_ORDER_SINGLE = "D"
    ORDER_CANCEL_REQUEST = "F"
    ORDER_CANCEL_REPLACE_REQUEST = "G"
    MARKET_DATA_REQUEST = "V"
    MARKET_DATA_SNAPSHOT = "W"
    MARKET_DATA_INCREMENTAL = "X"
    MARKET_DATA_REQUEST_REJECT = "Y"


class Side(FixEnum):
    BUY = "1"
    SELL = "2"


class OrdType(FixEnum):
    MARKET = "1"
    LIMIT = "2"


class TimeInForce(FixEnum):
    DAY = "0"
    GOOD_TILL_CANCEL = "1"
    IMMEDIATE_OR_CANCEL = "3"
    FILL_OR_KILL = "4"
    GOOD_TILL_DATE = "6"


class ExecType(FixEnum):
    NEW = "0"
    CANCELED = "4"
    REPLACED = "5"
    REJECTED = "8"
    TRADE = "F"


class OrdStatus(FixEnum):
    NEW = "0"
    PARTIALLY_FILLED = "1"
    FILLED = "2"
    CANCELED = "4"
    REPLACED = "5"
    REJECTED = "8"


class CxlRejResponseTo(FixEnum):
    ORDER_CANCEL_REQUEST = "1"
    ORDER_CANCEL_REPLACE_REQUEST = "2"


class SubscriptionRequestType(FixEnum):
    SNAPSHOT = "0"
    SUBSCRIBE = "1"
    UNSUBSCRIBE = "2"


class MDUpdateType(FixEnum):
    FULL_REFRESH = "0"
    INCREMENTAL_REFRESH = "1"


class MDEntryType(FixEnum):
    BID = "0"
    OFFER = "1"
    TRADE = "2"


class MDUpdateAction(FixEnum):
    NEW = "0"
    CHANGE = "1"
    DELETE = "2"


class MDReqRejReason(FixEnum):
    UNKNOWN_SYMBOL = "0"
    DUPLICATE_MD_REQ_ID = "1"


TERMINAL_ORD_STATUSES = frozenset({OrdStatus.FILLED, OrdStatus.CANCELED, OrdStatus.REJECTED})
