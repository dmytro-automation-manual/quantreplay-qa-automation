"""GET / PUT /api/settings (general simulator settings).

Teardown (fixture `undo`): the changed setting is restored.
"""
import pytest
from allure import step

from framework.assertions.expect import check_fields
from tests.support.rest import check_response


def _settings(api) -> dict:
    return {s["key"]: s["value"] for s in api.get_settings().body["settings"]}


def test_get_settings_returns_documented_keys(api):
    with step("GET /api/settings"):
        response = api.get_settings()
    check_response(response, "GET /api/settings", status_code=200)
    keys = sorted(s["key"] for s in response.body["settings"])
    check_fields("Setting keys", {"keys": keys},
                 {"keys": ["DisplayName", "SeedPriceDatabaseConnection", "SeedPricesLastUpdated"]})


def test_update_display_name(api, setting_table, undo):
    original = _settings(api)["DisplayName"]
    undo.push(f"restore DisplayName '{original}'",
              lambda: api.update_settings([{"key": "DisplayName", "value": original}]))
    with step("PUT /api/settings DisplayName -> 'MKTSIMULATOR-QA'"):
        response = api.update_settings([{"key": "DisplayName", "value": "MKTSIMULATOR-QA"}])
    check_response(response, "PUT /api/settings", status_code=200, result="General settings updated successfully")
    with step("Check REST and database show the new value"):
        check_fields("Settings in REST", _settings(api), {"DisplayName": "MKTSIMULATOR-QA"})
        check_fields("Settings in DB", {s.key: s.value for s in setting_table.all()},
                     {"DisplayName": "MKTSIMULATOR-QA"})


def test_update_unknown_setting_is_rejected(api):
    with step("PUT /api/settings with key BadKey"):
        response = api.update_settings([{"key": "BadKey", "value": "x"}])
    check_response(response, "PUT unknown setting", status_code=400)


@pytest.mark.known_issue("Documented 'Unknown BadKey setting update requested'; "
                         "the venue quotes the key: 'Unknown `BadKey' setting update requested'")
def test_unknown_setting_message_matches_documentation(api):
    check_response(api.update_settings([{"key": "BadKey", "value": "x"}]), "PUT unknown setting",
                   status_code=400, result="Unknown BadKey setting update requested")


def test_seed_prices_last_updated_is_read_only(api):
    """SeedPricesLastUpdated is ignored in an update request."""
    original = _settings(api)["SeedPricesLastUpdated"]
    with step("PUT /api/settings SeedPricesLastUpdated -> 2000-01-01 00:00:00"):
        api.update_settings([{"key": "SeedPricesLastUpdated", "value": "2000-01-01 00:00:00"}])
    check_fields("SeedPricesLastUpdated unchanged", _settings(api), {"SeedPricesLastUpdated": original})
