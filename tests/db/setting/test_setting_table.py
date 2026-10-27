"""Table sim.setting: general simulator settings."""
import pytest
from allure import step

from framework.assertions.expect import check_fields

# Settings and price seeds are shared by both venues: one venue at a time (see `one_venue_at_a_time`).
pytestmark = pytest.mark.usefixtures("one_venue_at_a_time")


def test_rest_settings_equal_database_rows(api, setting_table):
    with step("Read settings from REST and from sim.setting"):
        api_settings = {s["key"]: s["value"] for s in api.get_settings().body["settings"]}
        rows = {r.key: r.value for r in setting_table.all()}
    check_fields("REST settings vs sim.setting", api_settings, rows)
    check_fields("Same keys", {"keys": sorted(api_settings)}, {"keys": sorted(rows)})
