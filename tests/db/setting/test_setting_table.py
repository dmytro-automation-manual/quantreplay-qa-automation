"""Table sim.setting: general simulator settings."""
from allure import step

from framework.assertions.expect import check_fields


def test_rest_settings_equal_database_rows(api, setting_table):
    with step("Read settings from REST and from sim.setting"):
        api_settings = {s["key"]: s["value"] for s in api.get_settings().body["settings"]}
        rows = {r.key: r.value for r in setting_table.all()}
    check_fields("REST settings vs sim.setting", api_settings, rows)
    check_fields("Same keys", {"keys": sorted(api_settings)}, {"keys": sorted(rows)})
