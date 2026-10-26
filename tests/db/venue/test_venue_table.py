"""Table sim.venue: matching rules of the venue (supported TIFs, own-order matching, start-up behaviour)."""
from dataclasses import fields

import pytest
from allure import step

from framework.assertions.expect import check_fields
from framework.services.rest_api import to_venue



@pytest.mark.smoke
def test_row_has_test_venue_configuration(market, venue_table):
    """All TIFs on, own orders match (tests trade against themselves), no generator start, no persisted book."""
    with step(f"Read sim.venue row {market.venue_id}"):
        row = venue_table.get(market.venue_id)
    check_fields(f"sim.venue {market.venue_id}", row, {
        "engine_type": "Matching", "support_tif_ioc": True, "support_tif_fok": True, "support_tif_day": True,
        "include_own_orders": True, "order_on_startup": False, "persistence_enabled": False,
        "cancel_on_disconnect": False, "timezone": market.timezone})


def test_rest_venue_equals_database_row(market, api, venue_table):
    with step(f"Read {market.venue_id} from REST and from sim.venue"):
        api_venue = to_venue(api.get_venue(market.venue_id).body)
        row = venue_table.get(market.venue_id)
    check_fields("REST venue vs sim.venue", api_venue, {f.name: getattr(row, f.name) for f in fields(row)})
