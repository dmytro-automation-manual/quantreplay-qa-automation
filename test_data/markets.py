"""Test venues: one simulator instance each, with its own REST / FIX ports and instruments.

Every test runs once per venue (tests/conftest.py parametrizes the `market` fixture),
so the same checks cover equities on XETRA and FX spot on FASTMATCH.
"""
from dataclasses import dataclass

from test_data.instruments import FASTMATCH_INSTRUMENTS, XETRA_INSTRUMENTS, Instrument


@dataclass(frozen=True)
class Market:
    venue_id: str
    rest_port: int
    fix_port: int
    sender_comp_id: str
    target_comp_id: str
    timezone: str
    instruments: tuple[Instrument, ...]

    @property
    def main(self) -> Instrument:
        """Instrument used by the tests that need just one."""
        return self.instruments[0]

    def __str__(self) -> str:   # readable pytest ids: test_x[XETRA-AMZ]
        return self.venue_id


XETRA = Market("XETRA", 9050, 9051, "CLIENT_XETRA", "SIM_XETRA", "UTC", XETRA_INSTRUMENTS)
FASTMATCH = Market("FASTMATCH", 9052, 9053, "CLIENT_FASTMATCH", "SIM_FASTMATCH", "America/New_York",
                   FASTMATCH_INSTRUMENTS)

MARKETS = (XETRA, FASTMATCH)
