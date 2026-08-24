# RS-Stages — Decision Log

## 2026-08-24 — Initial quantitative lock

1. Use calendar dates for RS lookbacks: 3/6/9/12 calendar months.
2. Use 30-calendar-week **30W MA**, calculated as the simple mean of all valid NSE sessions in the calendar window; not a conventional weighted moving average and not a fixed 150-row approximation.
3. Use calendar dates for the 52-week high.
4. Require at least 200 valid sessions inside the 52-calendar-week window.
5. Production volume baseline: 50 prior observations, `min_periods=50`, then `.shift(1)`.
6. Breakout setup is separate from Breakout Confirmed; confirmation requires U/D > 1.3.
7. Universe/symbols and Industry come directly from the NSE constituent CSV; no F&O filtering and no WealthStar remapping.
8. Use 20 completed sessions for U/D.
9. Use yfinance with `auto_adjust=True`, adjusted Close/High, and raw Volume.
10. Fetch sufficient calendar history; fixed row counts are implementation buffers only.
11. ₹5 crore liquidity rule is an optional UI/screener filter applied after calculations.
12. Remove arbitrary `+1` from U/D denominator and handle zero denominator explicitly.
13. v1 RS Line uses current download window only.
14. **Pre-market information boundary:** decisions are made before the upcoming session opens; all calculations terminate at the latest completed NSE session. The upcoming/incomplete session can never enter a signal.
15. 10-trading-session MA slope is locked as `(MA_today / MA_10_sessions_ago - 1) × 100`.

## 2026-08-24 — Guide v2 supersedes early Action/UI specifications

1. The supplied NSE Signal Interpretation Guide is adopted as the production interpretation/action reference.
2. RS interpretation bands are now 80–99 leadership, 50–79 adequate, and <50 lagging. The former UI thresholds RS 85/70 are retired.
3. Production Action vocabulary is now `BUY★`, `BUY`, `HOLD`, `WAIT`, `WATCH★`, `WATCH`, `REDUCE`, `SELL`, `AVOID`.
4. Stage takes precedence over RS in conflicts: Stage 4 = SELL; Stage 3 = SELL when RS <50 otherwise REDUCE; Stage 1 maps to WATCH★/WATCH/AVOID by RS band.
5. Stage 2 uses the guide's RS bands, distribution warning, >20% extension timing warning, below-50DMA timing warning, breakout and confirmed-breakout states.
6. Extension is operationalized as Close > 1.20 × 30W MA; 50DMA is the 50-session simple moving average of Close.
7. Pullback/volume-drying is not fabricated without a validated quantitative definition.
8. Action logic is implemented in `rs_stages/actions.py`, separated from the quantitative engine.
9. The UI is upgraded to a six-area research platform: Dashboard, Screener, Industries, Movers, Stock, Methodology, with subtle semantic colours and TradingView Lightweight Charts driven by repository data.
10. The Action column is the final decision column in the screener and stock pages expose the underlying evidence and exact Action reason.

Locked decisions may only be changed through a new documented decision/audit item supported by evidence.
