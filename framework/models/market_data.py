"""Market data models. Plain data, no behaviour."""
from dataclasses import dataclass
from decimal import Decimal

from framework.fix.tags import MDEntryType, MDReqRejReason, MDUpdateAction, MsgType, SubscriptionRequestType


@dataclass(frozen=True)
class MarketDataRequest:
    """MarketDataRequest (35=V) for one instrument."""
    symbol: str | tuple[str, ...]          # a tuple sends several symbols (rejected by the venue)
    subscription: SubscriptionRequestType = SubscriptionRequestType.SNAPSHOT
    market_depth: int = 0                  # 0 = full book, 1 = top of book
    entry_types: tuple[MDEntryType, ...] = (MDEntryType.BID, MDEntryType.OFFER)
    incremental: bool = True               # MDUpdateType for subscriptions
    md_req_id: str | None = None           # generated when not given


@dataclass(frozen=True)
class MDEntry:
    entry_type: MDEntryType
    price: Decimal | None
    size: Decimal | None
    entry_id: str | None = None
    update_action: MDUpdateAction | None = None   # incremental refresh only


@dataclass(frozen=True)
class MarketDataSnapshot:
    """MarketDataSnapshotFullRefresh (35=W)."""
    msg_type: MsgType
    md_req_id: str
    symbol: str
    entries: tuple[MDEntry, ...]

    def side(self, entry_type: MDEntryType) -> list[MDEntry]:
        return [e for e in self.entries if e.entry_type == entry_type]


@dataclass(frozen=True)
class MarketDataIncremental:
    """MarketDataIncrementalRefresh (35=X)."""
    msg_type: MsgType
    md_req_id: str
    entries: tuple[MDEntry, ...]


@dataclass(frozen=True)
class MarketDataReject:
    """MarketDataRequestReject (35=Y)."""
    msg_type: MsgType
    md_req_id: str
    reason: MDReqRejReason | None
    text: str | None
