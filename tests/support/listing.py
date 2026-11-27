"""Expected sim.listing values of a reference instrument (test_data/instruments.py) - one place for DB and REST tests."""
from typing import Any

from test_data.instruments import Instrument


def expected_listing(instrument: Instrument) -> dict[str, Any]:
    """Trading parameters, identifiers, party and random order settings the listing must have."""
    random = instrument.random
    return {
        "security_type": instrument.security_type, "price_currency": instrument.currency,
        "fx_base_currency": instrument.fx_base_currency, "security_exchange": instrument.security_exchange,
        "isin_id": instrument.isin, "cusip_id": instrument.cusip, "sedol_id": instrument.sedol,
        "ric_id": instrument.ric, "exchange_symbol_id": instrument.exchange_symbol,
        "bloomberg_symbol_id": instrument.bloomberg_symbol,
        "party_id": instrument.party_id, "party_role": instrument.party_role,
        "price_tick_size": instrument.tick_size, "qty_minimum": instrument.qty_minimum,
        "qty_maximum": instrument.qty_maximum, "qty_multiple": instrument.qty_multiple, "enabled": True,
        "random_orders_enabled": False,
        "random_qty_minimum": random.qty_minimum, "random_qty_maximum": random.qty_maximum,
        "random_amt_minimum": random.amt_minimum, "random_amt_maximum": random.amt_maximum,
        "random_aggressive_qty_minimum": random.aggressive_qty_minimum,
        "random_aggressive_qty_maximum": random.aggressive_qty_maximum,
        "random_aggressive_amt_minimum": random.aggressive_amt_minimum,
        "random_aggressive_amt_maximum": random.aggressive_amt_maximum,
        "random_depth_levels": random.depth_levels, "random_orders_spread": random.spread,
        "random_orders_rate": random.rate, "random_tick_range": random.tick_range,
    }
