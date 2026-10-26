"""GET /api/datasources: the VOW historical order book (CSV) configured on the test venue.

Unknown id: the venue's text is checked (the REST API document writes 'No such datasource').
"""
from allure import step

from framework.assertions.expect import check_fields, check_true
from tests.support.rest import check_response

VOW_HISTORY = "XETRA-VOW-HISTORY"


def _vow_history(api):
    return next(d for d in api.get_datasources().body["dataSources"] if d["name"] == VOW_HISTORY)


def test_get_all_datasources_contains_vow_history(api):
    with step("GET /api/datasources"):
        response = api.get_datasources()
    check_response(response, "GET /api/datasources", status_code=200)
    datasource = next((d for d in response.body["dataSources"] if d["name"] == VOW_HISTORY), None)
    check_fields(VOW_HISTORY, datasource, {
        "venueId": "XETRA", "format": "CSV", "type": "OrderBook", "enabled": True,
        "connection": "/market-simulator/quod/data/datasources/xetra_vow_history.csv",
        "textDelimiter": ",", "textHeaderRow": 1, "textDataRow": 2})


def test_get_datasource_by_id(api):
    datasource = _vow_history(api)
    with step(f"GET /api/datasources/{datasource['id']}"):
        response = api.get_datasource(datasource["id"])
    check_response(response, "GET datasource by id", status_code=200)
    check_true("Same datasource as in the list", response.body == datasource, f"{response.body} / {datasource}")


def test_unknown_datasource_returns_404(api):
    check_response(api.get_datasource(999999), "GET unknown datasource", status_code=404,
                   result="Can not resolve a single datasource by a given key")
