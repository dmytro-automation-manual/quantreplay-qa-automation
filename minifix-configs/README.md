# MiniFIX connection configs

One `.reg` file = one MiniFIX setup (connection, session, message templates).

| File | Venue | Host:Port | SenderCompID | TargetCompID | FIX |
|---|---|---|---|---|---|
| `quantreplay-xetra.reg` | QuantReplay XETRA | localhost:9051 | MINIFIX | SIM_XETRA | FIX.4.4 |

Import: close MiniFIX, then
```bash
./import.sh quantreplay-xetra.reg
```
Import replaces the current MiniFIX connection settings and the listed message templates.

Templates in `quantreplay-xetra.reg`: Logon (141=Y), NewOrderSingle (VOW BUY 10 @ 0.01 Day),
OrderCancelReplaceRequest / OrderCancelRequest (fill 41 = ClOrdID of the order), MarketDataRequest (VOW snapshot).
