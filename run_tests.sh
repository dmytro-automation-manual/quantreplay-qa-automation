#!/usr/bin/env bash
# Run the suite locally. Results go to the local ReportPortal (http://127.0.0.1:8080)
# and to allure-results/. Extra pytest arguments are passed through, e.g. ./run_tests.sh -m smoke
set -euo pipefail
cd "$(dirname "$0")"
set -a; . reportportal/.env; set +a
exec .venv/bin/pytest --reportportal --alluredir=allure-results --clean-alluredir "$@"
