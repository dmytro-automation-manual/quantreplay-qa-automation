# BUG-003: PUT /api/venues with only `phases` returns 400 "Required fields missing"

| | |
|---|---|
| Whose defect | **Simulator** (the documentation is correct) |
| Component | REST API, `PUT /api/venues/{venueId}`, field `phases` (market phase schedule, table `sim.market_phase`) |
| Severity | Medium - the phase schedule cannot be set or cleared on its own; the error text points to a wrong cause. Workaround: send any venue field too |
| Venues | XETRA, FASTMATCH (same behaviour) |
| Found | 2026-11-04 |
| Simulator | `ghcr.io/quod-financial/deploy_marketsim:latest`, digest `sha256:cb46204b...29637c853` (built 2026-10-20) |
| Tests | `tests/rest/market_phase/test_phase_schedule.py::test_schedule_only_update_is_accepted` (xfail, `BUG_003`, `set` and `clear`); `test_schedule_saved_together_with_a_venue_field` passes |

## Steps to reproduce

1. Start the simulator stack: `docker compose -f sim-run/docker-compose.yml up -d`
2. Send `PUT http://localhost:9050/api/venues/XETRA` with the body
   ```json
   {"phases": [{"phase": "Closed", "startTime": "23:00", "endTime": "23:30", "endTimeRange": 0}]}
   ```
3. Send `PUT http://localhost:9050/api/venues/XETRA` with the body `{"phases": []}` (clear the schedule)
4. Send step 2 again with one more venue field: `{"name": "XETRA", "phases": [ ...same phase... ]}`
5. `GET http://localhost:9050/api/venues/XETRA`, field `phases`

## Actual result

Steps 2 and 3:
```
HTTP 400 Bad Request
{"result":"Required fields missing for Venue model in request"}
```
The schedule is not changed. The request has every field the phases sub-list requires (`phase`, `startTime`).

Step 4: `HTTP 200`, `{"result":"Successfully updated the XETRA venue"}`; step 5 shows the saved phase
`{"phase":"Closed","startTime":"23:00","endTime":"23:30","venueId":"XETRA","endTimeRange":0}`.
The same schedule is accepted only when the body also changes the venue itself.

## Expected result

Steps 2 and 3: `200 OK`; step 5 shows the new schedule (step 2) or an empty `phases` list (step 3).

Source - REST API document, `simulator/docs/RESTAPI/AdministrativeSettings/AdministrativeSettings.adoc`:
* "Update Venue": `PUT /api/venues/{venueId}` updates the given fields; the example sends two fields only,
  no field of the venue is mandatory in an update;
* Venue fields: `phases` - *Array - Scheduled phase changes*, with the "Phases Sub-List" (`phase`,
  `startTime`, `endTime`, `endTimeRange`, `allowCancels`).

## Notes

* Cause (simulator source): the schedule is stored in its own table `market_phase`; the other fields of the
  request become a SQL `UPDATE` of table `venue`. With `phases` only, that `UPDATE` has no column to set, and
  `simulator/project/data_layer/ih/pqxx/queries/detail/update_query_builder.hpp:124` throws
  `MalformedPatch("a patch with no fields is passed into UPDATE query builder")`; the REST layer turns it into
  the generic "Required fields missing" message (`project/http/src/controllers/venue_controller.cpp:173`).
* The phases themselves work: with the workaround (`name` sent too) and `POST /api/reset`, a `Closed` phase
  rejects new orders and an empty schedule opens the market again (checked over FIX on XETRA, 2026-11-04).
* The Postman collection (`postman/QuantReplay.postman_collection.json`, folder "Market phases") sends
  `"name": "{{venueId}}"` in every phase request as the workaround.
