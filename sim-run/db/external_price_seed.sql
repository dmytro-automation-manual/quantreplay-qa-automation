-- External price seed database (container external_price-seed-db, database priceseed, user priceseed).
-- POST /api/syncpriceseeds reads this table over the connection string in the simulator setting
-- SeedPriceDatabaseConnection and, row by row by symbol, copies mid_price / bid_price / offer_price / last_update
-- into sim.price_seed (a symbol missing in sim.price_seed is inserted), then sets SeedPricesLastUpdated.
-- The simulator reads the table by its plain name `price_seed`, so it lives in the default schema (public)
-- and has the same columns as sim.price_seed.
-- One instrument per venue (VOW for XETRA, EUR/USD for FASTMATCH): a sync touches only these two seeds,
-- the other simulator prices never move. Starting values = the simulator's own price seeds
-- (Xetra close / ECB reference rate 23.10.2026), so a sync right after start changes no price.

CREATE TABLE price_seed (
    price_seed_id      serial PRIMARY KEY,
    symbol             text NOT NULL UNIQUE,
    security_type      text,
    price_currency     text,
    security_id        text,
    security_id_source text,
    instrument_symbol  text,
    mid_price          real,
    bid_price          real,
    offer_price        real,
    last_update        text
);

INSERT INTO price_seed (symbol, security_type, price_currency, security_id, security_id_source, instrument_symbol,
                        mid_price, bid_price, offer_price, last_update) VALUES
    ('VOW',     'CS',     'EUR', 'DE0007664005', 'ISI', 'VOW',     68.7,    68.68,    68.72,    '2026-10-23 17:30:00'),
    ('EUR/USD', 'FXSPOT', 'USD', NULL,           NULL,  'EUR/USD', 1.1193,  1.11929,  1.11931,  '2026-10-23 14:15:00');
