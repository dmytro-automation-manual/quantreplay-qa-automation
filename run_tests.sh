#!/usr/bin/env bash
# Full local run:
#   1. start the simulator stack (sim-run: XETRA, FASTMATCH, database) and wait until REST, FIX and the DB are up;
#   2. save the database state to the host: sim-run/db/snapshots/pre_run_<timestamp>.sql;
#   3. run the tests -> results and logs go to the local ReportPortal (http://127.0.0.1:8080) and allure-results/;
#   4. restart the simulator stack: the database is recreated from sim-run/db/simdb_test_data.sql,
#      the simulator starts with empty order books. ReportPortal is not touched.
# Extra pytest arguments are passed through, e.g. ./run_tests.sh -m smoke
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE=(docker compose -f sim-run/docker-compose.yml)

venue_up() {
  curl -sf "http://localhost:$1/api/venues" >/dev/null && (exec 3<>"/dev/tcp/localhost/$2") 2>/dev/null
}

wait_for_simulator() {
  for _ in $(seq 1 60); do
    if venue_up 9050 9051 && venue_up 9052 9053; then     # XETRA, FASTMATCH: REST, FIX
      return 0
    fi
    sleep 2
  done
  echo "Simulator did not start" >&2
  "${COMPOSE[@]}" logs --tail=50 >&2
  return 1
}

echo "== start simulator stack"
"${COMPOSE[@]}" up -d --wait database
"${COMPOSE[@]}" up -d
wait_for_simulator

echo "== save database state before the run"
scripts/db_snapshot.sh save "sim-run/db/snapshots/pre_run_$(date +%Y%m%d_%H%M%S).sql"

echo "== run tests"
set -a; . reportportal/.env; set +a
status=0
.venv/bin/pytest --reportportal --alluredir=allure-results --clean-alluredir "$@" || status=$?

echo "== restart simulator stack (fresh test database, empty books)"
"${COMPOSE[@]}" down
"${COMPOSE[@]}" up -d --wait database
"${COMPOSE[@]}" up -d
wait_for_simulator

exit "$status"
