#!/usr/bin/env bash
# Import a MiniFIX connection config (.reg) into Wine. Close MiniFIX first:
# on exit it saves its current settings and would overwrite the imported ones.
set -euo pipefail
cfg="$(realpath "${1:?usage: ./import.sh <config>.reg}")"
if pgrep -fi 'minifix.exe' >/dev/null; then
    echo "MiniFIX is running - close it and run again." >&2
    exit 1
fi
WINEDEBUG=-all wine regedit /S "Z:${cfg//\//\\}"
echo "Imported: $(basename "$cfg"). Start MiniFIX from the dock."
