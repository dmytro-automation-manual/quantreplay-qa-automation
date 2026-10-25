#!/usr/bin/env bash
# Save or restore the simulator database (schema `sim`) to / from a file on the host.
# Usage:
#   scripts/db_snapshot.sh save    [FILE]   default FILE: sim-run/db/snapshots/simdb_<timestamp>.sql
#   scripts/db_snapshot.sh restore FILE     replaces schema `sim` with the file content, then resets the venue
set -euo pipefail
cd "$(dirname "$0")/.."

CONTAINER=market-simulator-database
action="${1:?save|restore}"

case "$action" in
  save)
    file="${2:-sim-run/db/snapshots/simdb_$(date +%Y%m%d_%H%M%S).sql}"
    mkdir -p "$(dirname "$file")"
    docker exec "$CONTAINER" pg_dump -U postgres -d simdb -n sim --no-comments > "$file"
    echo "$file"
    ;;
  restore)
    file="${2:?FILE required}"
    [[ -f "$file" ]] || { echo "No such file: $file" >&2; exit 2; }
    { echo "DROP SCHEMA IF EXISTS sim CASCADE;"; cat "$file"; } \
      | docker exec -i "$CONTAINER" psql -U postgres -d simdb -v ON_ERROR_STOP=1 -q
    curl -sf -X POST http://localhost:9050/api/reset >/dev/null   # simulator reloads the restored config
    echo "restored $file"
    ;;
  *)
    echo "Unknown action: $action (save|restore)" >&2; exit 2
    ;;
esac
