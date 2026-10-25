"""Market data service: snapshots and subscriptions over the FIX session.

Layer rule: depends on an injected session, the FIX mapping and the models; makes no assertions.
"""
from dataclasses import replace
from typing import Protocol

from framework.fix import messages
from framework.fix.tags import MsgType, SubscriptionRequestType, Tag
from framework.models.market_data import (MarketDataIncremental, MarketDataReject, MarketDataRequest,
                                          MarketDataSnapshot)


class Session(Protocol):
    def send(self, msg_type: str, fields) -> None: ...
    def receive(self, predicate, timeout: float | None = None): ...


class MarketDataService:
    """One instance per test: remembers active subscriptions so the teardown can unsubscribe them."""

    def __init__(self, session: Session):
        self._session = session
        self.subscriptions: dict[str, MarketDataRequest] = {}

    def request(self, request: MarketDataRequest) -> MarketDataSnapshot | MarketDataReject:
        """Send MarketDataRequest and return the answer (snapshot or reject)."""
        md_req_id = request.md_req_id or messages.new_id()
        self._session.send(MsgType.MARKET_DATA_REQUEST.value, messages.market_data_request(request, md_req_id))
        answer = self._wait(md_req_id, (MsgType.MARKET_DATA_SNAPSHOT, MsgType.MARKET_DATA_REQUEST_REJECT))
        if isinstance(answer, MarketDataSnapshot) and request.subscription == SubscriptionRequestType.SUBSCRIBE:
            self.subscriptions[md_req_id] = replace(request, md_req_id=md_req_id)
        return answer

    def snapshot(self, symbol: str, **kwargs) -> MarketDataSnapshot | MarketDataReject:
        return self.request(MarketDataRequest(symbol=symbol, **kwargs))

    def subscribe(self, symbol: str, **kwargs) -> MarketDataSnapshot | MarketDataReject:
        return self.request(MarketDataRequest(symbol=symbol, subscription=SubscriptionRequestType.SUBSCRIBE,
                                              **kwargs))

    def unsubscribe(self, md_req_id: str, symbol: str) -> None:
        """Send Unsubscribe. The venue sends nothing back on success."""
        request = MarketDataRequest(symbol=symbol, subscription=SubscriptionRequestType.UNSUBSCRIBE,
                                    md_req_id=md_req_id)
        self._session.send(MsgType.MARKET_DATA_REQUEST.value, messages.market_data_request(request, md_req_id))
        self.subscriptions.pop(md_req_id, None)

    def unsubscribe_unknown(self, md_req_id: str, symbol: str) -> MarketDataReject:
        """Unsubscribe for an id that has no subscription: the venue answers with a reject."""
        self.unsubscribe(md_req_id, symbol)
        return self._wait(md_req_id, (MsgType.MARKET_DATA_REQUEST_REJECT,))

    def next_update(self, md_req_id: str, timeout: float | None = None) -> MarketDataIncremental | MarketDataSnapshot:
        """Next streamed update (incremental or full refresh) of a subscription."""
        return self._wait(md_req_id, (MsgType.MARKET_DATA_INCREMENTAL, MsgType.MARKET_DATA_SNAPSHOT), timeout)

    def no_update(self, md_req_id: str, wait: float = 1.0) -> bool:
        try:
            self.next_update(md_req_id, timeout=wait)
        except TimeoutError:
            return True
        return False

    def _wait(self, md_req_id: str, types: tuple[MsgType, ...], timeout: float | None = None):
        wanted_id, wanted_types = md_req_id.encode(), {t.value.encode() for t in types}
        msg = self._session.receive(
            lambda m: m.get(Tag.MSG_TYPE) in wanted_types and m.get(Tag.MD_REQ_ID) == wanted_id, timeout)
        kind = messages.msg_type(msg)
        if kind == MsgType.MARKET_DATA_SNAPSHOT.value:
            return messages.market_data_snapshot(msg)
        if kind == MsgType.MARKET_DATA_INCREMENTAL.value:
            return messages.market_data_incremental(msg)
        return messages.market_data_reject(msg)
