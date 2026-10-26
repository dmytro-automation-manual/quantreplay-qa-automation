"""Table sim.price_seed: the starting market prices (Xetra close 23.10.2026)."""
from dataclasses import fields

from allure import step

from framework.assertions.expect import check_fields
from framework.services.rest_api import to_price_seed


def _row(price_seed_table, symbol):
    return next((r for r in price_seed_table.all() if r.symbol == symbol), None)


def test_row_matches_real_market_prices(price_seed_table, instrument):
    with step(f"Read sim.price_seed row of {instrument}"):
        row = _row(price_seed_table, instrument.symbol)
    check_fields(f"sim.price_seed {instrument}", row, {
        "security_type": instrument.security_type, "price_currency": instrument.currency,
        "security_id": instrument.isin,
        "bid_price": instrument.bid, "mid_price": instrument.mid, "offer_price": instrument.offer})


def test_rest_price_seed_equals_database_row(api, price_seed_table, instrument):
    with step(f"Read {instrument} seed from REST and from sim.price_seed"):
        row = _row(price_seed_table, instrument.symbol)
        api_seed = to_price_seed(api.get_price_seed(row.price_seed_id).body)
    check_fields(f"REST price seed {instrument} vs sim.price_seed", api_seed,
                 {f.name: getattr(row, f.name) for f in fields(row)})
