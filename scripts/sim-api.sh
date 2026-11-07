#!/usr/bin/env bash
# REST calls to the local QuantReplay simulator venues only (localhost).
# Usage: scripts/sim-api.sh [VENUE] METHOD PATH [JSON_BODY]
#   VENUE: XETRA (default, port 9050) | FASTMATCH (port 9052)
#   scripts/sim-api.sh GET  venues/XETRA
#   scripts/sim-api.sh FASTMATCH GET venues/FASTMATCH
#   scripts/sim-api.sh XETRA PUT venues/XETRA '{"orderOnStartup":false}'
#   scripts/sim-api.sh FASTMATCH POST genstop/FASTMATCH
set -euo pipefail

port=9050
case "${1:-}" in
  XETRA)     port=9050; shift ;;
  FASTMATCH) port=9052; shift ;;
esac
BASE_URL="http://localhost:$port/api"

method="${1:?METHOD required (GET|POST|PUT|DELETE)}"
path="${2:?PATH required, e.g. venues/XETRA}"
body="${3:-}"

case "$method" in
  GET|POST|PUT|DELETE) ;;
  *) echo "Unsupported method: $method" >&2; exit 2 ;;
esac

# Path must stay on the simulator API: no scheme, host or traversal
if [[ ! "$path" =~ ^[A-Za-z0-9/_.%-]+$ || "$path" == *..* ]]; then
  echo "Invalid path: $path" >&2; exit 2
fi

args=(-sS -X "$method" -w '\nHTTP %{http_code}\n' -H 'Accept: application/json')
if [[ -n "$body" ]]; then
  args+=(-H 'Content-Type: application/json' --data-raw "$body")
fi

curl "${args[@]}" "$BASE_URL/${path#/}"
