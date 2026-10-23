import pytest

pytestmark = pytest.mark.fix

SNAPSHOT, SUBSCRIBE, UNSUBSCRIBE = 0, 1, 2


@pytest.mark.smoke
def test_snapshot_returns_full_refresh(fix, symbol):
    req_id = fix.market_data_request(symbol, subscription=SNAPSHOT)

    resp = fix.market_data_response(req_id)

    assert resp.get(35) == b"W"  # MarketDataSnapshotFullRefresh
    assert resp.get(55) == symbol.encode()


def test_snapshot_unknown_symbol_is_rejected(fix):
    req_id = fix.market_data_request("NOSUCHSYM", subscription=SNAPSHOT)

    resp = fix.market_data_response(req_id)

    assert resp.get(35) == b"Y"  # MarketDataRequestReject
    assert resp.get(281) == b"0"  # Unknown symbol
    assert resp.get(58).decode() == "listing not found"


def test_duplicate_md_req_id_is_rejected(fix, symbol):
    req_id = fix.market_data_request(symbol, subscription=SUBSCRIBE)
    assert fix.market_data_response(req_id).get(35) == b"W"

    fix.market_data_request(symbol, md_req_id=req_id, subscription=SUBSCRIBE)
    resp = fix.market_data_response(req_id)

    try:
        assert resp.get(35) == b"Y"
        assert resp.get(281) == b"1"  # Duplicate MDReqID
        assert resp.get(58).decode() == "request identifier is used already"
    finally:
        fix.market_data_request(symbol, md_req_id=req_id, subscription=UNSUBSCRIBE)
