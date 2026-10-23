import pytest

from framework import config

pytestmark = [pytest.mark.rest, pytest.mark.smoke]

DEMO_SYMBOLS = {"AMZ", "MSF", "NFC", "VODI", "VOW"}


def test_get_venues_returns_configured_venue(rest):
    resp = rest.get_venues()

    assert resp.status_code == 200
    venue_ids = [v["id"] for v in resp.json()["venues"]]
    assert config.VENUE in venue_ids


def test_get_listings_returns_demo_instruments(rest):
    resp = rest.get_listings()

    assert resp.status_code == 200
    symbols = {l["symbol"] for l in resp.json()["listings"] if l["venueId"] == config.VENUE}
    assert DEMO_SYMBOLS <= symbols
