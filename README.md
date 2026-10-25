# QuantReplay QA Automation

[![autotests](https://github.com/dmytro-automation-manual/quantreplay-qa-automation/actions/workflows/autotests.yml/badge.svg)](https://github.com/dmytro-automation-manual/quantreplay-qa-automation/actions/workflows/autotests.yml)
[![Allure report](https://img.shields.io/badge/report-Allure-orange)](https://dmytro-automation-manual.github.io/quantreplay-qa-automation/)

Test automation and manual-testing setup for **[QuantReplay](https://github.com/Quod-Financial/quantreplay)**,
an open-source multi-asset market simulator (matching engine) by Quod Financial.

The suite checks the simulator through all of its interfaces:

| Interface | Protocol | What is tested |
|---|---|---|
| Trading | **FIX** - FIXT.1.1 / FIX 5.0 SP2 (per the simulator's Rules of Engagement) | order lifecycle (new / replace / cancel), rejects, quantity / tick limits, all TimeInForce values, market data |
| Administration | **REST** | every documented endpoint: settings, venues, listings, price seeds, datasources, venue status, order generator, halt / resume |
| Storage | **PostgreSQL** (schema created by Liquibase) | reference data in each table, REST <-> DB consistency |

## Stack

Python, pytest, simplefix, httpx, psycopg, Docker Compose, GitHub Actions, Allure, ReportPortal

## Framework architecture

Each layer depends only on layers below it, never on a layer above; transport, config and assertions
know nothing about the rest of the framework. The layers are wired together in one place,
`tests/conftest.py` (composition root). A layer can be replaced (another FIX engine, another DB driver)
without touching the tests.

```
tests            what is checked: steps + expected values, nothing about sockets or SQL
  │ fixtures (tests/conftest.py) build the objects and own setup / teardown
test_data        reference instruments (real Xetra data), order factories, price helpers
framework/
  assertions     expected-vs-actual tables (logged, attached to Allure / ReportPortal)
  services       business actions: trading, market data, REST API, DB tables - no assertions
  fix            FIX dictionary (tags, enums) and message mapping models <-> fields
  models         plain dataclasses: orders, execution reports, market data, reference data
  transport      FIX session, HTTP client, DB client - know nothing about the business
  config         environment variables, read only by the composition root
```

## Test layout

```
tests/
  fix/
    orders/
      positive/          new order, replace (price, then quantity), cancel, market orders
      negative/          new order / cancel / replace rejects
      boundary/          qty min / max / lot size, price tick - for every instrument
      time_in_force/     Day, GTC, GTD (and its expiry rules), IOC, FOK
    market_data/
      positive/          snapshots, subscriptions
      negative/          MarketDataRequestReject reasons
    orders_and_market_data/  the book seen through market data while orders change it
  rest/                  one folder per API function: settings, venues, listings, price_seeds,
                         datasources, venue_status, order_generation, market_phase (halt / resume)
  db/                    one folder per table: venue, listing, price_seed, setting
  support/               test-side helpers: isolation (undo stack), order book checks, REST checks
```

Folder names are markers: `pytest -m negative`, `pytest -m "fix and boundary"`, `pytest -m smoke`.
`smoke` = core trading flow and everything that can lose money (fills, fat-finger and tick limits,
halt, reference data of the instruments).

Every test: **precondition** (fixtures) -> **steps** (`allure.step`) -> **teardown** (fixtures undo the change).
Every order check states OrderID, ExecType, OrdStatus, Symbol, OrderQty and Price - the check function
does not accept a call without them.

### Known issues

Tests marked `known_issue` assert the documented behaviour and are reported as `xfail` until the simulator
is fixed (a fixed issue turns the test into a strict-xfail failure, so the marker must then be removed).
Found so far: reject texts `... constraint violated` vs documented `... constraint is violated`,
OrdStatus in OrderCancelReject for an active order, outdated REST answer texts, DELETE of an unknown
price seed answers 400 instead of 404.

## Test data

`sim-run/db/simdb_test_data.sql` is the test database (in git). The database container loads it on every
start and keeps its data in memory (tmpfs), so each start is clean. It is the QuantReplay demo data plus
`sim-run/db/real_market_overrides.sql`: real Xetra instruments (close of 23.10.2026) - prices, ISINs,
tick sizes (band 11 table for non-EU shares, ESMA band 5 for VOW), lot size 1, fat-finger qty limits.
The same values are the reference in `test_data/instruments.py`. Rebuild the dump with
`scripts/build_test_db.sh` after changing the overrides.

| Symbol | Instrument | Mid, EUR | Tick | Max qty |
|---|---|---|---|---|
| AMZ | Amazon.com | 222.55 | 0.05 | 20 000 |
| MSF | Microsoft | 468.90 | 0.05 | 10 000 |
| NFC | Netflix | 59.58 | 0.01 | 50 000 |
| VODI | Vodafone Group | 1.410 | 0.001 | 2 000 000 |
| VOW | Volkswagen St. | 68.70 | 0.02 | 50 000 |

### Isolation

* session start: generator stopped, all order books empty (otherwise the venue is reset), DB content captured;
* each test: orders left active are cancelled **and the cancel report is checked**, subscriptions closed,
  REST changes undone (undo stack, last in - first out);
* session end: the run fails if any order is left in a book or any configuration table differs from the start.

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd reportportal && docker compose -p reportportal up -d && cd ..   # UI: http://127.0.0.1:8080

./run_tests.sh              # all tests
./run_tests.sh -m smoke     # smoke only
```

`run_tests.sh`: starts the simulator stack -> saves the DB to `sim-run/db/snapshots/pre_run_<time>.sql` ->
runs pytest (results and logs to ReportPortal and `allure-results/`) -> restarts the simulator stack
(fresh test database, empty books). `reportportal/.env` (not committed) holds the passwords and the API key.

Without the wrapper: `cd sim-run && docker compose up -d`, then `.venv/bin/pytest`.
Save / restore the DB by hand: `scripts/db_snapshot.sh save [FILE]`, `scripts/db_snapshot.sh restore FILE`.

## CI/CD

Every push and pull request runs `.github/workflows/autotests.yml`:

1. starts the simulator with Docker Compose,
2. runs the whole suite,
3. shows a test summary on the run page,
4. on `main` publishes the **[Allure report](https://dmytro-automation-manual.github.io/quantreplay-qa-automation/)** with run history to GitHub Pages.

## Manual testing tools

| Tool | Used for |
|---|---|
| FIXYL | FIX client on the spec session `FIXYL -> SIM_XETRA` (FIXT.1.1 / FIX 5.0 SP2) |
| Postman | REST API (`postman/QuantReplay.postman_collection.json`) |
| DBeaver | browsing `simdb` (user `sim`, port 15432) |
| MiniFIX | quick checks on a FIX 4.4 session - not the simulator's spec version, findings are re-checked on FIXT.1.1 |

## FIX sessions

| SenderCompID (client) | TargetCompID | Version | Purpose |
|---|---|---|---|
| `CLIENT_XETRA` | `SIM_XETRA` | FIXT.1.1 / FIX 5.0 SP2 | autotests |
| `FIXYL` | `SIM_XETRA` | FIXT.1.1 / FIX 5.0 SP2 | manual testing (FIXYL) |
| `MINIFIX` | `SIM_XETRA` | FIX 4.4 | manual testing (MiniFIX) |
