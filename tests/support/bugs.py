"""Open defects (details in bug_reports/). Used as the reason of @pytest.mark.known_issue."""

BUG_001 = ("BUG-001 (simulator): DELETE /api/priceseeds/{id} for an unknown id answers 400 instead of the "
           "documented 404")

BUG_002 = ("BUG-002 (simulator + documentation): OrdStatus in OrderCancelReject for a rejected replace of an "
           "active order is inconsistent - Rejected for an off-tick price, the current status (New / "
           "PartiallyFilled) for a TimeInForce change or OrderQty <= CumQty; the RoE contradicts itself")

BUG_003 = ("BUG-003 (simulator): PUT /api/venues/{id} with only `phases` in the body (set or clear the "
           "market phase schedule) answers 400 'Required fields missing for Venue model in request'; "
           "it works when any venue field is sent too")
