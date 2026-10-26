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
    random_qty_minimum = v.rnd_qty_min,
    random_qty_maximum = v.rnd_qty_max,
    random_orders_spread = v.tick,
    random_depth_levels = 5,
    random_orders_rate = 2,
    random_tick_range = 10,
    random_orders_enabled = true,
    enabled = true
FROM (VALUES
    ('AMZ',  'US0231351067', 0.05::real,  20000::real,    10::real,   500::real),
    ('MSF',  'US5949181045', 0.05::real,  10000::real,     5::real,   250::real),
    ('NFC',  'US64110L1061', 0.01::real,  50000::real,    20::real,  1000::real),
    ('VODI', 'GB00BH4HKS39', 0.001::real, 2000000::real, 1000::real, 50000::real),
    ('VOW',  'DE0007664005', 0.02::real,  50000::real,    20::real,  1000::real)
) AS v(symbol, isin, tick, qty_max, rnd_qty_min, rnd_qty_max)
WHERE l.symbol = v.symbol AND l.venue_id = 'XETRA';

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

-- Historical VOW order book (CSV, Xetra levels around EUR 68.70) for manual playback tests.
INSERT INTO sim.data_source (data_source_id, enabled, name, venue_id, connection, format, type, repeat,
                             text_delimiter, text_header_row, text_data_row, random_price_only, incremental_subscriptions)
VALUES (1, true, 'XETRA-VOW-HISTORY', 'XETRA', '/market-simulator/quod/data/datasources/xetra_vow_history.csv',
        'CSV', 'OrderBook', false, ',', 1, 2, false, false)
ON CONFLICT (data_source_id) DO NOTHING;
INSERT INTO sim.column_mapping (column_from, column_to, data_source_id)
SELECT c, c, 1 FROM unnest(ARRAY['ReceivedTimeStamp', 'MessageTimeStamp', 'Instrument', 'BidParty', 'BidQuantity',
                                 'BidPrice', 'AskPrice', 'AskQuantity', 'AskParty']) AS c
ON CONFLICT DO NOTHING;
SELECT setval('sim.data_source_data_source_id_seq', (SELECT max(data_source_id) FROM sim.data_source));

-- FASTMATCH: FX spot venue (second simulator instance, REST 9052, FIX 9053).
-- Prices: 5 decimals (0.00001), JPY pairs 3 decimals (0.001); bid / offer one tick around the mid.
-- Quantities in the base currency: minimum 10 000, multiple of 1 000, fat-finger limit 50 000 000.
INSERT INTO sim.venue (venue_id, name, engine_type, support_tif_ioc, support_tif_fok, support_tif_day,
                       include_own_orders, rest_port, order_on_startup, random_party_count, tns_enabled,
                       tns_qty_enabled, tns_side_enabled, tns_parties_enabled, timezone, cancel_on_disconnect,
                       persistence_enabled)
VALUES ('FASTMATCH', 'FASTMATCH', 'Matching', true, true, true, true, 9052, false, 10, true, true, true, true,
        'America/New_York', false, false);

INSERT INTO sim.listing (listing_id, symbol, venue_id, security_type, price_currency, fx_base_currency, instr_symbol,
                         qty_minimum, qty_maximum, qty_multiple, price_tick_size, enabled, random_qty_minimum,
                         random_qty_maximum, random_depth_levels, random_orders_spread, random_orders_rate,
                         random_tick_range, security_exchange, random_orders_enabled,
                         random_price_exclude_current_listing)
SELECT v.id, v.symbol, 'FASTMATCH', 'FXSPOT', v.quote, v.base, v.symbol, 10000, 50000000, 1000, v.tick, true,
       100000, 5000000, 5, v.tick, 2, 10, 'FASTMATCH', true, false
FROM (VALUES
    (6,  'EUR/USD', 'EUR', 'USD', 0.00001::real),
    (7,  'GBP/USD', 'GBP', 'USD', 0.00001::real),
    (8,  'USD/JPY', 'USD', 'JPY', 0.001::real),
    (9,  'USD/CHF', 'USD', 'CHF', 0.00001::real),
    (10, 'EUR/GBP', 'EUR', 'GBP', 0.00001::real)
) AS v(id, symbol, base, quote, tick);
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

COMMIT;
