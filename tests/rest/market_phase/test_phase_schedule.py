"""Market phase schedule through PUT /api/venues/{id} (field `phases`, table sim.market_phase).

The schedule is only saved here, no reset: a saved schedule is applied on the next POST /api/reset, so these
tests never change the trading phase (phase behaviour itself: test_halt_resume.py).
Teardown (fixture `undo`): the schedule is cleared again. The clear request also carries the venue name,
otherwise it would hit BUG-003 itself.
"""
import pytest
from allure import step

from framework.assertions.expect import check_fields
from tests.support.bugs import BUG_003
from tests.support.rest import check_response

# Far from any test run time; saved only, never applied (no reset).
CLOSED_PHASE = {"phase": "Closed", "startTime": "23:00", "endTime": "23:30", "endTimeRange": 0}


def _phases(api, venue_id):
    return [{k: p.get(k) for k in CLOSED_PHASE} for p in api.get_venue(venue_id).body["phases"]]


@pytest.fixture
def clear_schedule_after(market, api, undo):
    assert _phases(api, market.venue_id) == [], f"{market.venue_id} already has a phase schedule"
    undo.push("clear the phase schedule",
              lambda: api.update_venue(market.venue_id, {"name": market.venue_id, "phases": []}))


def test_schedule_saved_together_with_a_venue_field(market, api, clear_schedule_after):
    body = {"name": market.venue_id, "phases": [CLOSED_PHASE]}
    with step(f"PUT /api/venues/{market.venue_id} {body}"):
        response = api.update_venue(market.venue_id, body)
    check_response(response, "PUT venue with name + phases", status_code=200)
    check_fields("Saved schedule", {"phases": _phases(api, market.venue_id)}, {"phases": [CLOSED_PHASE]})


@pytest.mark.known_issue(BUG_003)
@pytest.mark.parametrize("phases", [[CLOSED_PHASE], []], ids=["set", "clear"])
def test_schedule_only_update_is_accepted(market, api, clear_schedule_after, phases):
    body = {"phases": phases}
    with step(f"PUT /api/venues/{market.venue_id} {body} (no other venue field)"):
        response = api.update_venue(market.venue_id, body)
    check_response(response, "PUT venue with phases only", status_code=200)
    check_fields("Saved schedule", {"phases": _phases(api, market.venue_id)}, {"phases": phases})
