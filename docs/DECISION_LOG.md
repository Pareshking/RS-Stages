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

Locked decisions may only be changed through a new documented decision/audit item supported by evidence.
