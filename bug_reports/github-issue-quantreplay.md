Title: Three REST/FIX bugs and a few doc mismatches (image built 2026-10-20)

---

Hi! I've been writing automated tests against QuantReplay and ran into three bugs plus some places where the docs and the simulator don't match. Could you take a look and let me know roughly when the bugs could be fixed? Happy to give more details or retest.

Version: `ghcr.io/quod-financial/deploy_marketsim@sha256:cb46204be6f93465f3aec82a51438e134cf708a3cc26b7f422ff5ef29637c853` (built 2026-10-20), source at `39111b6`. Same behaviour on two venues: XETRA (equities) and FASTMATCH (FX spot).

## Bug 1. DELETE /api/priceseeds/{id} for an unknown id returns 400 instead of 404

**Steps to reproduce:**
1. `GET /api/priceseeds/999999` returns 404 (the seed doesn't exist)
2. `DELETE /api/priceseeds/999999`

**Actual result:** `400 Bad Request`, `{"result":"Can not resolve a single PriceSeed by a given key"}`

**Expected result:** `404 Not Found` with the same body. This is what General.adoc ("HTTP DELETE") and the "Delete Price Seeds" example in AdministrativeSettings.adoc say. GET and PUT for the same id already return 404, so only DELETE differs.

## Bug 2. OrdStatus in OrderCancelReject is different depending on why the replace was rejected

In all three cases below, the order is not modified and stays active in the book, but the OrdStatus (39) differs:

| Replace request | Text (58) | OrdStatus (39) |
|---|---|---|
| Price off the tick grid | order price tick constraint violated | 8 (Rejected) |
| TimeInForce changed, Day to GTC | time in force can not be changed | 0 (New) |
| OrderQty <= CumQty on a partially filled order | invalid quantity | 1 (PartiallyFilled) |

**Steps to reproduce (XETRA, AMZ, tick 0.05):**
1. NewOrderSingle: BUY 50 AMZ @ 200.25, Limit, Day. You get an ExecutionReport with status New.
2. OrderCancelReplaceRequest with Price=200.275.
3. Place a new order as in step 1, then send OrderCancelReplaceRequest with 59=1.
4. Place a new order as in step 1, fill 25 of it with SELL 25 @ 200.25 IOC, then send OrderCancelReplaceRequest with OrderQty=25.

**Actual result:**
```
39=8 ... 58=order price tick constraint violated|434=2
39=0 ... 58=time in force can not be changed|434=2
39=1 ... 58=invalid quantity|434=2
```

**Expected result:** one rule for all replace rejects. The RoE contradicts itself here:
- MessageFlows.adoc, "Order Cancel Replace Request" says: "always issued ... with CxlRejResponseTo=OrderCancelReplaceRequest, OrdStatus=Rejected"
- TradeMessages.adoc, OrderCancelReject, tag 39 says: "Describes the current state of the order"

The second one matches the FIX standard. Which rule is the intended one?

## Bug 3. PUT /api/venues/{id} with only `phases` returns 400

**Steps to reproduce:**
1. `PUT /api/venues/XETRA` with body `{"phases": [{"phase": "Closed", "startTime": "23:00", "endTime": "23:30", "endTimeRange": 0}]}`
2. `PUT /api/venues/XETRA` with body `{"phases": []}`
3. Send step 1 again, adding `"name": "XETRA"` to the body

**Actual result:** steps 1 and 2 return `400 {"result":"Required fields missing for Venue model in request"}` and the schedule doesn't change. Step 3 returns 200 and the phase is saved.

**Expected result:** 200 for steps 1 and 2. "Update Venue" doesn't make any venue field mandatory.

Looks like the cause is this: with only `phases` in the body, there's nothing left for the UPDATE on the `venue` table. The `update_query_builder.hpp:124` then throws `MalformedPatch("a patch with no fields...")`, and `venue_controller.cpp:173` turns it into the generic "Required fields missing" message. For now we send `name` as a workaround.

## Doc vs simulator mismatches (not blocking, just so the docs match)

| Where | Docs | Simulator |
|---|---|---|
| FIX reject text: price tick, qty min / max / lot | ... constraint is violated | ... constraint violated |
| MarketDataRequestReject for several symbols | ... are now allowed (typo) | ... are not allowed |
| RoE reject table for missing / both / past ExpireDate / ExpireTime | rows say GoodTillCancel | applies to GoodTillDate (the 432/126 field definitions also say GTD) |
| REST unknown listing / venue / datasource | No such listing / No such venue / No such datasource | Can not resolve a single Listing / Venue / datasource by a given key |
| REST unknown setting | Unknown BadKey setting update requested | ``Unknown `BadKey' setting update requested`` |
| REST generator status | NotRunning; Random orders generator started / stopped successfully | Stopped; Generator was started / stopped |
| REST listing update | Requested update of the listing - &lt;symbol&gt; | Successfully updated the &lt;symbol&gt; listing |

Thanks!
