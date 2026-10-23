"""REST API must expose exactly what is stored in the simulator database."""
import pytest

from framework import config

pytestmark = [pytest.mark.db, pytest.mark.rest]


def test_venue_matches_db(rest, db):
    api = next(v for v in rest.get_venues().json()["venues"] if v["id"] == config.VENUE)
    row = db.query("select * from sim.venue where venue_id = %s", (config.VENUE,))[0]

    assert api["name"] == row["name"]
    assert api["restPort"] == row["rest_port"]
    assert api["supportTifIoc"] == row["support_tif_ioc"]
    assert api["supportTifFok"] == row["support_tif_fok"]
    assert api["supportTifDay"] == row["support_tif_day"]
    assert api["timezone"] == row["timezone"]


def test_listings_match_db(rest, db):
    api = {l["id"]: l for l in rest.get_listings().json()["listings"] if l["venueId"] == config.VENUE}
    rows = {r["listing_id"]: r for r in db.query("select * from sim.listing where venue_id = %s", (config.VENUE,))}

    assert api.keys() == rows.keys()
    for listing_id, row in rows.items():
        listing = api[listing_id]
        assert listing["symbol"] == row["symbol"]
        assert listing["enabled"] == row["enabled"]
        assert listing["randomOrdersEnabled"] == row["random_orders_enabled"]
        assert listing["qtyMinimum"] == float(row["qty_minimum"])
        assert listing["qtyMaximum"] == float(row["qty_maximum"])
