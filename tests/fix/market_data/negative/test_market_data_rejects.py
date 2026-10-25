"""MarketDataRequestReject (35=Y) reasons (Rules of Engagement, "Market Data Request" reject table).

Teardown (fixture `market_data`): subscriptions opened as preconditions are closed.
"""
import pytest
from allure import step

from framework.assertions.expect import ABSENT, check_fields
from framework.fix.tags import MDReqRejReason, MsgType
from framework.fix.messages import new_id
from test_data.instruments import AMZ, MSF, UNKNOWN_SYMBOL


def test_unknown_symbol_is_rejected(market_data):
    with step(f"Send Snapshot for {UNKNOWN_SYMBOL}"):
        reject = market_data.snapshot(UNKNOWN_SYMBOL)
    with step("Check MarketDataRequestReject: Unknown symbol, 'listing not found'"):
        check_fields("MarketDataRequestReject for unknown symbol", reject,
                     {"msg_type": MsgType.MARKET_DATA_REQUEST_REJECT, "reason": MDReqRejReason.UNKNOWN_SYMBOL,
                      "text": "listing not found"})


def test_duplicate_md_req_id_of_active_subscription_is_rejected(market_data):
    md_req_id = new_id()
    with step(f"Precondition: subscribe to {AMZ} with MDReqID {md_req_id}"):
        first = market_data.subscribe(AMZ.symbol, md_req_id=md_req_id)
        check_fields("Initial snapshot", first, {"msg_type": MsgType.MARKET_DATA_SNAPSHOT, "md_req_id": md_req_id})
    with step("Subscribe again with the same MDReqID"):
        reject = market_data.subscribe(AMZ.symbol, md_req_id=md_req_id)
    with step("Check MarketDataRequestReject: Duplicate MDReqID, 'request identifier is used already'"):
        check_fields("MarketDataRequestReject for duplicate MDReqID", reject,
                     {"msg_type": MsgType.MARKET_DATA_REQUEST_REJECT, "md_req_id": md_req_id,
                      "reason": MDReqRejReason.DUPLICATE_MD_REQ_ID, "text": "request identifier is used already"})


def test_unsubscribe_without_subscription_is_rejected(market_data):
    md_req_id = new_id()
    with step(f"Send Unsubscribe for MDReqID {md_req_id} that has no subscription"):
        reject = market_data.unsubscribe_unknown(md_req_id, AMZ.symbol)
    with step("Check MarketDataRequestReject: 'no subscription found for the request id'"):
        check_fields("MarketDataRequestReject for unknown subscription", reject,
                     {"msg_type": MsgType.MARKET_DATA_REQUEST_REJECT, "md_req_id": md_req_id, "reason": ABSENT,
                      "text": "no subscription found for the request id"})


@pytest.mark.known_issue("RoE text is 'market data requests on multiple securities are now allowed' (typo 'now'); "
                         "the venue sends '... are not allowed'")
def test_request_for_several_symbols_is_rejected(market_data):
    """Each market data request can be associated with only one listing."""
    with step(f"Send Snapshot with NoRelatedSym=2 ({AMZ}, {MSF})"):
        reject = market_data.snapshot((AMZ.symbol, MSF.symbol))
    with step("Check MarketDataRequestReject for several securities"):
        check_fields("MarketDataRequestReject for several symbols", reject,
                     {"msg_type": MsgType.MARKET_DATA_REQUEST_REJECT, "reason": ABSENT,
                      "text": "market data requests on multiple securities are now allowed"})
