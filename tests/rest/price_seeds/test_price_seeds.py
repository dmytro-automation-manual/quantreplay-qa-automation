"""/api/priceseeds: the reference prices the random order generator starts from.

Seeds must be the real market levels (test_data/instruments.py) and lie on each instrument's tick grid.
Teardown (fixture `undo`): added seeds are deleted, changed seeds restored.
"""
from decimal import Decimal

import pytest
from allure import step

from framework.assertions.expect import check_fields, check_true
from framework.services.rest_api import to_price_seed
from tests.support.rest import check_response

NOT_FOUND = "Can not resolve a single PriceSeed by a given key"


def _seed_by_symbol(api, symbol):
    seeds = [s for s in api.get_price_seeds().body["priceSeeds"] if s["symbol"] == symbol]
    return seeds[0] if seeds else None


@pytest.mark.smoke
def test_price_seed_matches_real_market(api, instrument):
    with step("GET /api/priceseeds"):
        response = api.get_price_seeds()
    check_response(response, "GET /api/priceseeds", status_code=200)
    seed = next((to_price_seed(s) for s in response.body["priceSeeds"] if s["symbol"] == instrument.symbol), None)
    check_fields(f"Price seed {instrument}", seed, {
        "symbol": instrument.symbol, "security_type": instrument.security_type, "price_currency": instrument.currency,
        "security_id": instrument.isin, "bid_price": instrument.bid, "mid_price": instrument.mid,
        "offer_price": instrument.offer})
    with step("Check bid < mid < offer, all on the tick grid"):
        prices = (seed.bid_price, seed.mid_price, seed.offer_price)
        check_true(f"{instrument}: bid < mid < offer", prices[0] < prices[1] < prices[2], str(prices))
        check_true(f"{instrument}: prices on tick {instrument.tick_size}",
                   all(p % instrument.tick_size == 0 for p in prices), str(prices))


def test_get_price_seed_by_id(market, api):
    instrument = market.main
    seed = _seed_by_symbol(api, instrument.symbol)
    with step(f"GET /api/priceseeds/{seed['id']}"):
        response = api.get_price_seed(seed["id"])
    check_response(response, "GET price seed by id", status_code=200)
    check_true("Same seed as in the list", response.body == seed, f"{response.body} / {seed}")


def test_add_and_delete_price_seed(api, undo):
    new_seed = {"symbol": "QATEST", "securityType": "CS", "priceCurrency": "EUR",
                "bidPrice": Decimal("9.99"), "midPrice": Decimal("10.00"), "offerPrice": Decimal("10.01")}
    with step("POST /api/priceseeds"):
        response = api.add_price_seed(new_seed)
    check_response(response, "POST price seed", status_code=201, result="Successfully inserted new price seed")
    created = _seed_by_symbol(api, "QATEST")
    if created:
        undo.push("delete seed QATEST", lambda: api.delete_price_seed(created["id"]))
    check_fields("Created seed", to_price_seed(created) if created else None,
                 {"symbol": "QATEST", "bid_price": Decimal("9.99"), "mid_price": Decimal("10.00"),
                  "offer_price": Decimal("10.01")})

    with step(f"DELETE /api/priceseeds/{created['id']}"):
        response = api.delete_price_seed(created["id"])
    check_response(response, "DELETE price seed", status_code=204)
    check_response(api.get_price_seed(created["id"]), "GET deleted seed", status_code=404, result=NOT_FOUND)


def test_update_price_seed(market, api, undo):
    instrument = market.main
    seed = _seed_by_symbol(api, instrument.symbol)
    original = {"midPrice": seed["midPrice"]}
    undo.push(f"restore {instrument} seed {original}", lambda: api.update_price_seed(seed["id"], original))
    new_mid = instrument.mid + instrument.tick_size
    with step(f"PUT /api/priceseeds/{seed['id']} midPrice {instrument.mid} -> {new_mid}"):
        response = api.update_price_seed(seed["id"], {"midPrice": new_mid})
    check_response(response, "PUT price seed", status_code=200,
                   result=f"Successfully updated the price seed with {seed['id']} identifier")
    check_fields("Seed after update", to_price_seed(api.get_price_seed(seed["id"]).body), {"mid_price": new_mid})


def test_unknown_price_seed_returns_404(api):
    check_response(api.get_price_seed(999999), "GET unknown seed", status_code=404, result=NOT_FOUND)
    check_response(api.update_price_seed(999999, {"midPrice": 1}), "PUT unknown seed", status_code=404,
                   result=NOT_FOUND)


@pytest.mark.known_issue("Documented DELETE of an unknown seed: 404 'Can not resolve a single PriceSeed by a given key'; "
                         "the venue answers 400")
def test_delete_unknown_price_seed_returns_404(api):
    check_response(api.delete_price_seed(999999), "DELETE unknown seed", status_code=404, result=NOT_FOUND)
