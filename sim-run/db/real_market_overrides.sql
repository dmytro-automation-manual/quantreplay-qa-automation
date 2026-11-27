-- Real-market reference data for the test venues:
--   XETRA     - equities, Xetra close 23.10.2026;
--   FASTMATCH - FX spot, ECB reference rates 23.10.2026 (EUR/USD 1.1193, EUR/GBP 0.83728, EUR/JPY 175.51,
--               EUR/CHF 0.9227; GBP/USD, USD/JPY, USD/CHF are the cross rates).
-- Applied on top of the QuantReplay demo data; the result is dumped to simdb_test_data.sql
-- (scripts/build_test_db.sh), which the database container loads on start.
--
-- Tick sizes:
--   AMZ, MSF, NFC, VODI - non-EU shares on Xetra, liquidity band 11 (WM tick table S):
--       0-9.999: 0.001 | 10-49.995: 0.005 | 50-99.99: 0.01 | >=100: 0.05
--   VOW - EU share, ESMA RTS 11 tick table, liquidity band 5, price 50-100: 0.02
-- Quantities: Xetra lot size is 1 share; qty_maximum acts as a fat-finger limit (~EUR 3-5M per order).

BEGIN;

UPDATE sim.venue SET
    order_on_startup = false,        -- the random order generator does not start by itself
    persistence_enabled = false,     -- every simulator start begins with an empty order book
    cancel_on_disconnect = false
WHERE venue_id = 'XETRA';

UPDATE sim.listing l SET
    instr_symbol = v.symbol,
    security_type = 'CS',
    price_currency = 'EUR',
    security_exchange = 'XETR',
    isin_id = v.isin,
    qty_minimum = 1,
    qty_multiple = 1,
    qty_maximum = v.qty_max,
    price_tick_size = v.tick,
    random_orders_enabled = false,   -- random generator off by default; tests enable it via REST
    enabled = true
FROM (VALUES
    ('AMZ',  'US0231351067', 0.05::real,  20000::real),
    ('MSF',  'US5949181045', 0.05::real,  10000::real),
    ('NFC',  'US64110L1061', 0.01::real,  50000::real),
    ('VODI', 'GB00BH4HKS39', 0.001::real, 2000000::real),
    ('VOW',  'DE0007664005', 0.02::real,  50000::real)
) AS v(symbol, isin, tick, qty_max)
WHERE l.symbol = v.symbol AND l.venue_id = 'XETRA';
-- Identifiers and random order settings of every listing: see "Per-listing profile" below.

UPDATE sim.price_seed p SET
    security_id = v.isin,
    security_id_source = 'ISI',
    instrument_symbol = p.symbol,
    price_currency = 'EUR',
    bid_price = v.bid,
    mid_price = v.mid,
    offer_price = v.offer,
    last_update = '2026-10-23 17:30:00'
FROM (VALUES
    ('AMZ',  'US0231351067', 222.50::real, 222.55::real, 222.60::real),
    ('MSF',  'US5949181045', 468.85::real, 468.90::real, 468.95::real),
    ('NFC',  'US64110L1061',  59.57::real,  59.58::real,  59.59::real),
    ('VODI', 'GB00BH4HKS39',   1.409::real,  1.410::real,  1.411::real),
    ('VOW',  'DE0007664005',  68.68::real,  68.70::real,  68.72::real)
) AS v(symbol, isin, bid, mid, offer)
WHERE p.symbol = v.symbol;

-- Historical VOW order book (CSV, Xetra levels around EUR 68.70) for manual playback tests:
-- one row every 3 s, 3 depth levels per side, every order has its own party:
-- CP1, CP2, ... CP60, row by row, in column order (row 1: bid 1 = CP1, ask 1 = CP2, ... ask 3 = CP6; row 2: CP7...).
-- CSV columns = simulator field name + '_' + depth level (BidPrice_1, BidQuantity_1, BidParty_1, ...); only the
-- instrument column has its own name (Symbol). Column mapping: column_from = simulator field,
-- column_to = CSV column; '#' = depth level (1, 2, 3).
INSERT INTO sim.data_source (data_source_id, enabled, name, venue_id, connection, format, type, repeat,
                             text_delimiter, text_header_row, text_data_row, max_depth_levels, random_price_only,
                             incremental_subscriptions)
VALUES (1, true, 'XETRA-VOW-HISTORY', 'XETRA', '/market-simulator/quod/data/datasources/xetra_vow_history.csv',
        'CSV', 'OrderBook', true, ',', 1, 2, 3, false, false)
ON CONFLICT (data_source_id) DO NOTHING;
INSERT INTO sim.column_mapping (column_from, column_to, data_source_id)
VALUES ('ReceivedTimeStamp', 'ReceivedTimeStamp', 1),
       ('MessageTimeStamp',  'MessageTimeStamp',  1),
       ('Instrument',        'Symbol',  1),
       ('BidParty#',         'BidParty_#',    1),
       ('BidQuantity#',      'BidQuantity_#', 1),
       ('BidPrice#',         'BidPrice_#',    1),
       ('AskPrice#',         'AskPrice_#',    1),
       ('AskQuantity#',      'AskQuantity_#', 1),
       ('AskParty#',         'AskParty_#',    1)
ON CONFLICT DO NOTHING;
SELECT setval('sim.data_source_data_source_id_seq', (SELECT max(data_source_id) FROM sim.data_source));

-- FASTMATCH: FX spot venue (second simulator instance, REST 9052, FIX 9053).
-- Prices: 5 decimals (0.00001), JPY pairs 3 decimals (0.001); bid / offer one tick around the mid.
-- Quantities in the base currency, own limits per pair (the most liquid pair has the widest range):
--   EUR/USD 10 000 .. 100 000 000 by 1 000 | GBP/USD 25 000 .. 50 000 000 by 5 000
--   USD/JPY 50 000 .. 75 000 000 by 10 000 | USD/CHF  5 000 .. 25 000 000 by 1 000
--   EUR/GBP 100 000 .. 20 000 000 by 50 000
INSERT INTO sim.venue (venue_id, name, engine_type, support_tif_ioc, support_tif_fok, support_tif_day,
                       include_own_orders, rest_port, order_on_startup, random_party_count, tns_enabled,
                       tns_qty_enabled, tns_side_enabled, tns_parties_enabled, timezone, cancel_on_disconnect,
                       persistence_enabled)
VALUES ('FASTMATCH', 'FASTMATCH', 'Matching', true, true, true, true, 9052, false, 10, true, true, true, true,
        'America/New_York', false, false);

INSERT INTO sim.listing (listing_id, symbol, venue_id, security_type, price_currency, fx_base_currency, instr_symbol,
                         qty_minimum, qty_maximum, qty_multiple, price_tick_size, enabled,
                         security_exchange, random_orders_enabled, random_price_exclude_current_listing)
SELECT v.id, v.symbol, 'FASTMATCH', 'FXSPOT', v.quote, v.base, v.symbol, v.qty_min, v.qty_max, v.qty_mult, v.tick,
       true, 'FASTMATCH', false, false
FROM (VALUES
    (6,  'EUR/USD', 'EUR', 'USD', 0.00001::real,  10000::real, 100000000::real,  1000::real),
    (7,  'GBP/USD', 'GBP', 'USD', 0.00001::real,  25000::real,  50000000::real,  5000::real),
    (8,  'USD/JPY', 'USD', 'JPY', 0.001::real,    50000::real,  75000000::real, 10000::real),
    (9,  'USD/CHF', 'USD', 'CHF', 0.00001::real,   5000::real,  25000000::real,  1000::real),
    (10, 'EUR/GBP', 'EUR', 'GBP', 0.00001::real, 100000::real,  20000000::real, 50000::real)
) AS v(id, symbol, base, quote, tick, qty_min, qty_max, qty_mult);
SELECT setval('sim.listing_listing_id_seq', (SELECT max(listing_id) FROM sim.listing));

INSERT INTO sim.price_seed (price_seed_id, symbol, security_type, price_currency, instrument_symbol,
                            bid_price, mid_price, offer_price, last_update)
SELECT v.id, v.symbol, 'FXSPOT', v.quote, v.symbol, v.bid, v.mid, v.offer, '2026-10-23 14:15:00'
FROM (VALUES
    (6,  'EUR/USD', 'USD', 1.11929::real, 1.11930::real, 1.11931::real),
    (7,  'GBP/USD', 'USD', 1.33682::real, 1.33683::real, 1.33684::real),
    (8,  'USD/JPY', 'JPY', 156.802::real, 156.803::real, 156.804::real),
    (9,  'USD/CHF', 'CHF', 0.82434::real, 0.82435::real, 0.82436::real),
    (10, 'EUR/GBP', 'GBP', 0.83727::real, 0.83728::real, 0.83729::real)
) AS v(id, symbol, quote, bid, mid, offer);
SELECT setval('sim.price_seed_price_seed_id_seq', (SELECT max(price_seed_id) FROM sim.price_seed));

-- External price seed database (sim-run/db/external_price_seed.sql, container external_price-seed-db):
-- POST /api/syncpriceseeds copies bid / mid / offer prices from its table price_seed into sim.price_seed.
UPDATE sim.setting SET value = 'postgresql://priceseed:priceseed@external_price-seed-db:5432/priceseed'
WHERE key = 'SeedPriceDatabaseConnection';

-- Per-listing profile: every listing has its own extra identifier and random order settings.
--
-- Extra identifier (ISIN stays in isin_id for shares; FX spot has no ISIN / CUSIP / SEDOL), one source each:
--   VOW  cusip_id    D94523145      CINS of the Volkswagen ordinary share
--   VODI sedol_id    BH4HKS3        SEDOL (part of the GB ISIN GB00BH4HKS39)
--   NFC  ric_id      NFC.DE         Xetra RIC
--   AMZ  exchange_symbol_id AMZ     Xetra trading symbol
--   MSF  bloomberg_symbol_id MSF GY Equity   Bloomberg, Xetra (GY)
--   EUR/USD ric EUR=, USD/CHF ric CHF=, GBP/USD and EUR/GBP Bloomberg "<pair> Curncy", USD/JPY exchange symbol.
--
-- No party on the listings (party_id / party_role stay NULL): a listing party would tie the listing to one firm.
--
-- Random order generator (off by default, random_orders_enabled = false):
--   passive qty range, aggressive qty range, amount ranges (price currency), depth, spread, rate, tick range.
--   Rule found on the venue: random_amt_minimum / price must not exceed random_qty_minimum - otherwise the
--   generator silently places no orders at all. Every amount minimum below keeps amount / price <= qty minimum
--   (the same is kept for the aggressive pair).
UPDATE sim.listing l SET
    cusip_id = v.cusip, sedol_id = v.sedol, ric_id = v.ric,
    exchange_symbol_id = v.exch, bloomberg_symbol_id = v.bbg,
    random_qty_minimum = v.rq_min, random_qty_maximum = v.rq_max,
    random_amt_minimum = v.ra_min, random_amt_maximum = v.ra_max,
    random_aggressive_qty_minimum = v.aq_min, random_aggressive_qty_maximum = v.aq_max,
    random_aggressive_amt_minimum = v.aa_min, random_aggressive_amt_maximum = v.aa_max,
    random_depth_levels = v.depth, random_orders_spread = v.spread,
    random_orders_rate = v.rate, random_tick_range = v.ticks
FROM (VALUES
--   venue        symbol     cusip        sedol      ric       exchange  bloomberg
--     rnd qty min / max      rnd amt min / max          aggr qty min / max   aggr amt min / max   depth spread rate ticks
    ('XETRA',     'AMZ',     NULL,        NULL,      NULL,     'AMZ',    NULL,
         10::real,     500::real,    2000::real,     100000::real,     5::real,    200::real,     1000::real,    40000::real,  7, 0.10::real,    3, 12),
    ('XETRA',     'MSF',     NULL,        NULL,      NULL,     NULL,     'MSF GY Equity',
          5::real,     250::real,    2000::real,     100000::real,     2::real,    100::real,      900::real,    45000::real,  6, 0.05::real,    2, 15),
    ('XETRA',     'NFC',     NULL,        NULL,      'NFC.DE', NULL,     NULL,
         20::real,    1000::real,    1000::real,      50000::real,    10::real,    400::real,      500::real,    20000::real,  8, 0.02::real,    4, 20),
    ('XETRA',     'VODI',    NULL,        'BH4HKS3', NULL,     NULL,     NULL,
       1000::real,   50000::real,    1200::real,      60000::real,   500::real,  20000::real,      600::real,    25000::real, 10, 0.002::real,   5, 25),
    ('XETRA',     'VOW',     'D94523145', NULL,      NULL,     NULL,     NULL,
         20::real,    1000::real,    1300::real,      60000::real,    10::real,    400::real,      600::real,    25000::real,  5, 0.04::real,    2, 10),
    ('FASTMATCH', 'EUR/USD', NULL,        NULL,      'EUR=',   NULL,     NULL,
    1000000::real, 10000000::real, 1000000::real, 10000000::real, 500000::real, 5000000::real, 500000::real, 5000000::real, 10, 0.00002::real, 8, 15),
    ('FASTMATCH', 'GBP/USD', NULL,        NULL,      NULL,     NULL,     'GBPUSD Curncy',
     500000::real,  5000000::real,  600000::real,  6000000::real, 250000::real, 2500000::real, 300000::real, 3000000::real,  8, 0.00003::real, 5, 12),
    ('FASTMATCH', 'USD/JPY', NULL,        NULL,      NULL,     'USDJPY', NULL,
    1000000::real,  8000000::real, 150000000::real, 1200000000::real, 500000::real, 4000000::real, 75000000::real, 600000000::real, 8, 0.003::real, 6, 12),
    ('FASTMATCH', 'USD/CHF', NULL,        NULL,      'CHF=',   NULL,     NULL,
     200000::real,  3000000::real,  150000::real,  2400000::real, 100000::real, 1500000::real,  80000::real, 1200000::real,  6, 0.00003::real, 3, 10),
    ('FASTMATCH', 'EUR/GBP', NULL,        NULL,      NULL,     NULL,     'EURGBP Curncy',
     500000::real,  5000000::real,  400000::real,  4000000::real, 250000::real, 2000000::real, 200000::real, 1600000::real,  5, 0.00002::real, 2, 8)
) AS v(venue, symbol, cusip, sedol, ric, exch, bbg,
       rq_min, rq_max, ra_min, ra_max, aq_min, aq_max, aa_min, aa_max, depth, spread, rate, ticks)
WHERE l.venue_id = v.venue AND l.symbol = v.symbol;

COMMIT;
