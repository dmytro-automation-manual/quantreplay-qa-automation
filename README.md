# QuantReplay QA Automation

[![autotests](https://github.com/dmytro-automation-manual/quantreplay-qa-automation/actions/workflows/autotests.yml/badge.svg)](https://github.com/dmytro-automation-manual/quantreplay-qa-automation/actions/workflows/autotests.yml)
[![Allure report](https://img.shields.io/badge/report-Allure-orange)](https://dmytro-automation-manual.github.io/quantreplay-qa-automation/)

Test automation and manual-testing setup for **[QuantReplay](https://github.com/Quod-Financial/quantreplay)**,
an open-source multi-asset market simulator (matching engine) by Quod Financial.

The suite checks the simulator through all of its interfaces:

| Interface | Protocol | What is tested |
|---|---|---|
| Trading | **FIX** - FIXT.1.1 / FIX 5.0 SP2 (per the simulator's Rules of Engagement) | order lifecycle (new / replace / cancel), rejects, IOC / FOK, market data |
| Administration | **REST** | venues, listings |
| Storage | **PostgreSQL** (schema created by Liquibase) | REST <-> DB consistency |

## Stack

Python, pytest, simplefix, httpx, psycopg, Docker Compose, GitHub Actions, Allure, ReportPortal

## Project layout

```
framework/            FIX client, REST client, DB client, config (env-driven)
tests/
  fix/                order lifecycle, rejects, time in force, market data
  rest/               reference data
  db/                 REST vs database consistency
sim-run/              docker-compose for the simulator + its config (FIX sessions, dictionaries)
reportportal/         docker-compose for a local ReportPortal (bound to 127.0.0.1)
postman/              Postman collection for manual REST testing
fixyl-workspace/      FIXYL profile + message templates for manual FIX testing (FIXT.1.1)
minifix-configs/      MiniFIX config (FIX 4.4 session, for quick manual checks only)
.github/workflows/    CI pipeline
```

## Run locally

```bash
# 1. simulator (REST :9050, FIX :9051, Postgres :15432)
cd sim-run && docker compose up -d && cd ..

# 2. tests
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest                  # all tests
.venv/bin/pytest -m smoke         # smoke only
.venv/bin/pytest -m "fix and not smoke"
```

### With ReportPortal

```bash
cd reportportal && docker compose -p reportportal up -d   # UI: http://127.0.0.1:8080
./run_tests.sh                                             # sends the launch to ReportPortal + allure-results/
```
`reportportal/.env` (not committed) holds the generated passwords and the API key.

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
