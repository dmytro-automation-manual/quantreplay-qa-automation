"""Fixtures shared by the REST tests."""
import pytest


@pytest.fixture
def remember_listing(api, undo):
    """remember_listing("AMZ", ["qtyMaximum"]) - the fields are restored through REST after the test."""
    def remember(symbol: str, fields: list[str]) -> dict:
        original = api.get_listing(symbol).body
        values = {f: original.get(f) for f in fields}
        undo.push(f"restore listing {symbol} {values}", lambda: api.update_listing(symbol, values))
        return values
    return remember
