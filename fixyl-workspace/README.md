# FIXYL working directory

Select this folder as the **working directory** when FIXYL asks on first start.

| Profile | Host:Port | SenderCompID | TargetCompID | Version |
|---|---|---|---|---|
| QuantReplay XETRA | 127.0.0.1:9051 | FIXYL | SIM_XETRA | FIX 5.x (FIXT.1.1 + FIX 5.0 SP2) |
| QuantReplay FASTMATCH | 127.0.0.1:9053 | FIXYL | SIM_FASTMATCH | FIX 5.x (FIXT.1.1 + FIX 5.0 SP2) |

- `dictionaries/` - the simulator's own dictionaries (copied from `sim-run/cfg/default`).
- `FIX50SP2_marketsimulator/` - message templates (Favorites): Logon (auto-login), Buy VOW limit,
  Replace VOW, Cancel VOW (fill OrigClOrdID / OrderID), Snapshot VOW.
- `profiles.json` - the connection profiles.

Simulator side: `[SESSION] TargetCompID=FIXYL` in `sim-run/cfg/configSim.txt` (XETRA)
and `sim-run/fastmatch/cfg/configSim.txt` (FASTMATCH).
