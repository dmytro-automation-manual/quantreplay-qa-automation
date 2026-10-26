# BUG-002: OrdStatus in OrderCancelReject for a rejected replace is inconsistent

| | |
|---|---|
| Whose defect | **Simulator** (inconsistent behaviour) **and documentation** (the RoE contradicts itself) |
| Component | FIX order entry, OrderCancelReplaceRequest (35=G) -> OrderCancelReject (35=9) |
| Severity | Medium - a client that relies on OrdStatus (39) may treat a still active order as rejected, or the other way round |
| Venues | XETRA, FASTMATCH (same behaviour) |
| Found | 2026-10-26 |
| Simulator | `ghcr.io/quod-financial/deploy_marketsim:latest`, digest `sha256:cb46204b...29637c853` (built 2026-10-20) |
| Tests | `tests/fix/orders/negative/test_replace_rejects.py`: `test_replace_changing_time_in_force_is_rejected`, `test_replace_quantity_not_above_executed_is_rejected` (xfail, `BUG_002`); `tests/fix/orders/boundary/test_price_tick.py::test_replace_to_price_off_tick_is_rejected` (passes) |

## Summary

The order stays active in all three cases below (it is not modified and keeps resting in the book), but the
simulator reports a different OrdStatus (39) in the OrderCancelReject:

| Replace request | Text (58) | OrdStatus (39) sent |
|---|---|---|
| Price not on the tick grid | `order price tick constraint violated` | `8` Rejected |
| TimeInForce changed (Day -> GoodTillCancel) | `time in force can not be changed` | `0` New (current status) |
| OrderQty <= CumQty of a partially filled order | `invalid quantity` | `1` PartiallyFilled (current status) |

## Steps to reproduce (XETRA, AMZ)

1. Log on as `CLIENT_XETRA` to `localhost:9051` (FIXT.1.1 / FIX 5.0 SP2).
2. Send NewOrderSingle: BUY 50 AMZ @ 200.25, Limit, Day -> ExecutionReport New.
3. Send OrderCancelReplaceRequest with Price = 200.275 (half a tick off the 0.05 grid).
4. Repeat steps 2-3, but in step 3 change TimeInForce to GoodTillCancel (59=1) and keep the price.
5. Repeat step 2, partially fill the order with a SELL 25 AMZ @ 200.25 IOC, then send
   OrderCancelReplaceRequest with OrderQty = 25 (= CumQty).

## Expected result

One rule for every rejected replace. The documentation gives two different rules:

* `simulator/docs/FIXRulesOfEngagement/MessageFlows/MessageFlows.adoc`, "Order Cancel Replace Request":
  *"An application-level reject is always issued in the form of an OrderCancelReject message with
  CxlRejResponseTo=OrderCancelReplaceRequest, **OrdStatus=Rejected**"*.
* `simulator/docs/FIXRulesOfEngagement/TradeMessages/TradeMessages.adoc`, "OrderCancelReject (35=9)",
  tag 39: *"Describes the **current state** of the order."* This matches the FIX standard (OrdStatus after
  the cancel reject is applied; Rejected only when the order is unknown).

## Actual result (raw FIX, timestamps removed)

Price off tick - `39=8`:
```
>> 8=FIXT.1.1|35=G|49=CLIENT_XETRA|56=SIM_XETRA|41=94392a8d4e074b26|11=3c7bd4985ab14a27|37=261026180943000001|55=AMZ|54=1|40=2|44=200.275|38=50|59=0|
<< 8=FIXT.1.1|35=9|49=SIM_XETRA|56=CLIENT_XETRA|11=3c7bd4985ab14a27|37=261026180943000001|39=8|41=94392a8d4e074b26|58=order price tick constraint violated|434=2|
```

TimeInForce change - `39=0`:
```
>> 8=FIXT.1.1|35=G|49=CLIENT_XETRA|56=SIM_XETRA|41=dabbf8a16a644303|11=6955c366749d4d11|37=261026180951000003|55=AMZ|54=1|40=2|44=200.25|38=50|59=1|
<< 8=FIXT.1.1|35=9|49=SIM_XETRA|56=CLIENT_XETRA|11=6955c366749d4d11|37=261026180951000003|39=0|41=dabbf8a16a644303|58=time in force can not be changed|434=2|
```

OrderQty <= CumQty - `39=1`:
```
>> 8=FIXT.1.1|35=G|49=CLIENT_XETRA|56=SIM_XETRA|41=6804921e193a4542|11=8744475118ac4ca4|37=261026180952000004|55=AMZ|54=1|40=2|44=200.25|38=25|59=0|
<< 8=FIXT.1.1|35=9|49=SIM_XETRA|56=CLIENT_XETRA|11=8744475118ac4ca4|37=261026180952000004|39=1|41=6804921e193a4542|58=invalid quantity|434=2|
```

## Notes

* Who should fix what:
  * documentation - keep one rule for OrdStatus in OrderCancelReject (the FIX standard one: current status);
  * simulator - send the same rule for every replace reject (today the price / quantity validation path
    sends Rejected, the order state checks send the current status).
* The tests assert the RoE "Order Cancel Replace Request" section (OrdStatus=Rejected) until the vendor confirms
  the rule; then the expected value and the `known_issue` marker are updated together.
