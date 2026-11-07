# FIXYL working directory

Select this folder as the **working directory** when FIXYL asks on first start.

| Profile | Host:Port | SenderCompID | TargetCompID | Version |
|---|---|---|---|---|
| QuantReplay XETRA | 127.0.0.1:9051 | FIXYL | SIM_XETRA | FIX 5.x (FIXT.1.1 + FIX 5.0 SP2) |
| QuantReplay FASTMATCH | 127.0.0.1:9053 | FIXYL | SIM_FASTMATCH | FIX 5.x (FIXT.1.1 + FIX 5.0 SP2) |

Simulator side: `[SESSION] TargetCompID=FIXYL` in `sim-run/xetra/cfg/configSim.txt` (XETRA)
and `sim-run/fastmatch/cfg/configSim.txt` (FASTMATCH).

## Layout

```
profiles.json     connection profiles
dictionaries/     the simulator's own dictionaries (copied from sim-run/dictionaries)
  XETRA.xml, FASTMATCH.xml    symlinks to FIX50SP2_marketsimulator.xml
XETRA/            Favorites of the XETRA profile
  scenarios/      one-click scenarios of the XETRA profile
FASTMATCH/        the same for the FASTMATCH profile
```

FIXYL keeps Favorites in a folder named after the dictionary file, so each venue has its own dictionary name.
It does not read subfolders of Favorites and shows them grouped by message type, so the groups below are
number prefixes in the name. The Logon favorite must stay in both folders: auto-login looks it up there.
The paths in `profiles.json` are absolute: update them if the project moves.

## Scenarios (session tab -> Scenarios -> Run)

Every scenario checks the replies and shows SUCCESS / FAILED per stage. IDs are captured from the replies.
FIXYL lists them in random order, the number in the name gives the order.

| # | Shows |
|---|---|
| 1 | Order lifecycle: new, replace price, replace quantity, cancel |
| 2 | Full match: passive buy, aggressive sell at the same price |
| 3 | Partial match: two partial fills, the rest cancelled |
| 4 | Market order sweeping two price levels |
| 5 | IOC: filled in part, the rest killed |
| 6 | FOK: killed without enough liquidity, filled with enough |
| 7 | Incremental market data while a trade happens |

## Favorites (session tab -> Favorites)

| Group | Content |
|---|---|
| 1.x | Orders with all the supported tags: TimeInForce values, Parties, ISIN, short sell (XETRA) |
| 2.x | Lifecycle by hand: send in order, nothing to fill in |
| 3.x | Full match by hand |
| 4.x | Partial match by hand |
| 5.x | Liquidity, market order, IOC, FOK: send in order |
| 6.x | Rejects: tick, quantity limits, listing resolution, price rules, GoodTillDate, unknown order |
| 7.x | Market data: snapshots, subscribe / unsubscribe (full refresh and incremental), rejects |

Things to keep in mind:

* 2.x and 4.x use fixed ClOrdIDs. The simulator accepts a duplicate ClOrdID, then answers `order not found`
  for it: finish the group (2.4 / 4.4) before sending its first message again.
* Subscriptions (7.4, 7.6) use fixed MDReqIDs: unsubscribe (7.5, 7.7) before subscribing again, a second subscribe
  is rejected as `request identifier is used already`.
* A market order always comes back with TimeInForce ImmediateOrCancel.
* `ExpireTime` must include milliseconds and a time zone: FIXYL sends `Invalid date` otherwise.
* Orders of group 1.x stay in the book. To start from empty books:
  `cd sim-run && docker compose restart XETRA FASTMATCH`.
* Prices and quantities come from `sim-run/db/real_market_overrides.sql`.
