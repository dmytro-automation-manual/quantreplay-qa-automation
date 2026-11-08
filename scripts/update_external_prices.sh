#!/usr/bin/env bash
# Plays the end-of-day price job: moves the VOW and EUR/USD prices in the EXTERNAL price seed database
# (container external_price-seed-db) by a random number of ticks and stamps last_update with the current time.
# The simulator does not see it until POST /api/syncpriceseeds (add --sync to call it right away).
#
# Usage:
#   scripts/update_external_prices.sh            # update the external database only
#   scripts/update_external_prices.sh --sync     # update, then sync the simulator
# Once a day (cron, 18:00 after the Xetra close):
#   0 18 * * 1-5  /home/dmytro/fintech-project/scripts/update_external_prices.sh --sync >> /tmp/price_job.log 2>&1
#
# Demo only: after a sync the simulator seeds differ from test_data/instruments.py, so
# test_price_seed_matches_real_market fails until the stack is restarted (both databases start from their SQL files).
# The sync tests do not need this script: they write their own prices.
set -euo pipefail
cd "$(dirname "$0")/.."

CONTAINER=external_price-seed-db
psql() { docker exec -i "$CONTAINER" psql -U priceseed -d priceseed -v ON_ERROR_STOP=1 -q "$@"; }

echo "before:"
psql -c "select symbol, bid_price, mid_price, offer_price, last_update from price_seed order by price_seed_id"

# Mid moves by -5..+5 ticks; bid and offer keep their distance to the mid (the spread does not change).
psql <<'SQL'
UPDATE price_seed p SET
    mid_price   = round((p.mid_price   + s.shift)::numeric, t.decimals),
    bid_price   = round((p.bid_price   + s.shift)::numeric, t.decimals),
    offer_price = round((p.offer_price + s.shift)::numeric, t.decimals),
    last_update = to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
FROM (VALUES ('VOW', 0.02, 2), ('EUR/USD', 0.00001, 5)) AS t(symbol, tick, decimals),
     LATERAL (SELECT t.tick * (floor(random() * 11) - 5) AS shift) AS s
WHERE p.symbol = t.symbol;
SQL

echo "after:"
psql -c "select symbol, bid_price, mid_price, offer_price, last_update from price_seed order by price_seed_id"

if [[ "${1:-}" == "--sync" ]]; then
  scripts/sim-api.sh POST syncpriceseeds
  scripts/sim-api.sh GET settings | grep -o '"SeedPricesLastUpdated","value":"[^"]*"'
fi
