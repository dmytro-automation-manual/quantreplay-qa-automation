# BUG-001: DELETE of an unknown price seed returns 400 instead of 404

| | |
|---|---|
| Whose defect | **Simulator** (the documentation is correct) |
| Component | REST API, `DELETE /api/priceseeds/{id}` |
| Severity | Medium - a client cannot tell "no such seed" from "bad request" |
| Venues | XETRA, FASTMATCH (same behaviour) |
| Found | 2026-10-26 |
| Simulator | `ghcr.io/quod-financial/deploy_marketsim:latest`, digest `sha256:cb46204b...29637c853` (built 2026-10-20) |
| Test | `tests/rest/price_seeds/test_price_seeds.py::test_delete_unknown_price_seed_returns_404` (xfail, `BUG_001`) |

## Steps to reproduce

1. Start the simulator stack: `docker compose -f sim-run/docker-compose.yml up -d`
2. Make sure price seed `999999` does not exist: `GET /api/priceseeds/999999` -> `404 Not Found`
3. Send `DELETE http://localhost:9050/api/priceseeds/999999`

## Expected result

`404 Not Found`, body `{"result": "Can not resolve a single PriceSeed by a given key"}`

Source - REST API document:
* `simulator/docs/RESTAPI/General/General.adoc`, "HTTP DELETE": *404 NOT FOUND - The requested URI or resource
  identifier is unknown.*
* `simulator/docs/RESTAPI/AdministrativeSettings/AdministrativeSettings.adoc`, "Delete Price Seeds",
  negative reply example: `HTTP/1.1 404 Not Found`.

## Actual result

```
DELETE /api/priceseeds/999999 HTTP/1.1

HTTP/1.1 400 Bad Request
Connection: Close
Content-Length: 62

{"result":"Can not resolve a single PriceSeed by a given key"}
```

The body text is the documented one, only the status code is wrong.

## Notes

* The same unknown id gets `404` from `GET /api/priceseeds/999999` and `PUT /api/priceseeds/999999`
  (checked by `test_unknown_price_seed_returns_404`), so only DELETE is inconsistent.
* Impact: a client that treats 4xx codes differently (e.g. retries on 400, ignores 404 on cleanup) handles
  a repeated delete wrongly.
