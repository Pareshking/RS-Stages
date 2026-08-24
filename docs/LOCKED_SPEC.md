# RS-Stages — Locked Quantitative Specification

**Status:** LOCKED INPUTS — v1.2
**Date:** 2026-08-24
**Repository:** `Pareshking/RS-Stages`
**Primary technology:** Streamlit

This document contains the project-level quantitative decisions explicitly locked for RS-Stages. It is the authoritative implementation input.

## 1. Decision Hierarchy

1. Explicit project decisions in this document.
2. Supplied methodology/source material, subject to explicit project decisions.
3. Clearly documented implementation assumptions.
4. Conventional practice is never a substitute for the specified methodology.

Performance or backtest improvement is never sufficient reason to change a locked mathematical definition.

## 2. Universe and Sector Classification

- **Production universe:** official Nifty Total Market constituent CSV: `https://www.niftyindices.com/IndexConstituent/ind_niftytotalmarket_list.csv`
- The Nifty Total Market is the project's broad equity universe and is described by NSE Indices as covering 750 stocks across large, mid, small and microcap segments. The downloaded official CSV is authoritative for the actual live constituent count; do not hard-code exactly 750 if the official source contains a different count. citeturn0search0turn0search1
- Repository snapshot: `data/ind_niftytotalmarket_list.csv`.
- Industry classification: exactly the CSV `Industry` field.
- No F&O filtering.
- No WealthStar sector remapping.
- No consolidation unless explicitly decided later.
- Optional liquidity filtering must not reduce the cross-sectional RS ranking universe.
- The constituent CSV is refreshed every Friday at approximately **23:30 IST** by GitHub Actions and committed to the repository when changed.

## 3. Market Data

- **yfinance**.
- `auto_adjust=True`.
- Required prices: adjusted Close and adjusted High.
- Volume: raw/unadjusted.
- Open and Low are not required for core calculations.

All transformations must be explicit and auditable.

## 4. Pre-Market Information Boundary — LOCKED

RS-Stages generates decisions **before the upcoming NSE trading session opens**.

For decision/execution session `D`, let `T` be the most recent completed NSE trading session before `D`.

All calculations must use only information available through `T`:

`InformationSet(D) = data through T`

No price, High, Close, Volume, or derived value from the upcoming/incomplete session `D` may enter any signal calculation.

Whenever methodology says "current day/session included", RS-Stages interprets that as **the latest completed session `T`**, never the upcoming session `D`.

This is a global look-ahead-bias rule.

## 5. Historical Data / Warm-up

Fetch sufficient **calendar history** to guarantee every required calendar lookback and warm-up calculation.

A fixed row count such as 400 may be an implementation buffer only; it is not a mathematical definition.

Never replace calendar periods with fixed trading-row counts for convenience.

## 6. Relative Strength (RS)

### 6.1 Lookbacks

All RS lookbacks are calendar-date based:

- 3 calendar months
- 6 calendar months
- 9 calendar months
- 12 calendar months

For each calendar reference date, use the last available NSE session on or before that date.

### 6.2 Returns

`R_period = Close_latest / Close_reference - 1`

`Close_reference` is adjusted Close at the last available session on or before the calendar reference date.

### 6.3 Blend

`Blend = 0.40 × R3M + 0.20 × R6M + 0.20 × R9M + 0.20 × R12M`

### 6.4 Cross-sectional score

Across the valid mathematical universe:

`RS = rank(Blend, pct=True, method='min') × 98 + 1`

Then round to an integer, intended 1–99 scale.

Stocks without sufficient valid history are excluded from ranking.

### 6.5 Skip month

No skip-month is applied. The specified 3/6/9/12 calendar-month returns are used directly.

## 7. Stage Moving Average — 30W MA

**30W MA means a 30-calendar-week Simple Moving Average.** It is **not** a conventional Weighted Moving Average and is **not** a fixed 150-row trading-day average.

Use all valid NSE trading sessions contained in the preceding 30 calendar weeks ending at `T`, the latest completed session available before the decision.

`MA_30W(T) = mean(Close_s)` for all valid sessions `s` in that calendar window.

A complete 30-calendar-week history is required.

### 7.1 Slope

Slope window: **10 trading sessions**.

`Slope%(T) = (MA_30W(T) / MA_30W(T-10 sessions) - 1) × 100`

This is a project-selected implementation rule and must not be represented as a proven undisclosed WealthStar internal parameter.

### 7.2 Stage classification

`above_ma = Close_T > MA_30W(T)`

`rising = Slope%(T) > 0`

- Stage 2 — Advancing: above MA and rising.
- Stage 3 — Topping: above MA and not rising.
- Stage 4 — Declining: below MA and not rising.
- Stage 1 — Basing: below MA and rising.

Stages are categorical/cyclical states. Never infer transitions from numeric ordering of labels.

## 8. 52-Calendar-Week High

Use the preceding **52 calendar weeks** ending at `T`, not a fixed 252-row window.

`High_52W(T) = max(adjusted High)` over all valid sessions in the calendar window.

At least **200 valid sessions** must exist inside the window. Otherwise `near_high` is invalid/false for production signal purposes.

`near_high = Close_T >= 0.97 × High_52W(T)`

## 9. Volume Baseline

Prior-50-session baseline:

`Volume_MA50 = rolling(50, min_periods=50).mean().shift(1)`

The baseline excludes the latest completed session's own volume.

`Volume_Ratio(T) = Volume_T / Prior_50_Session_Average_Volume`

The latest completed session `T` is the numerator session. The upcoming session `D` is never used.

## 10. Up/Down Volume Ratio

For each completed session `t`:

- If `Close_t > Close_(t-1)`, classify `Volume_t` as Up Volume.
- If `Close_t < Close_(t-1)`, classify `Volume_t` as Down Volume.
- If unchanged, volume contributes to neither side.

For the latest completed session `T`, use the **20 completed sessions ending at T**, including `T`:

`UpVol20(T) = sum(UpVol over T-19 ... T)`

`DownVol20(T) = sum(DownVol over T-19 ... T)`

`U_D(T) = UpVol20(T) / DownVol20(T)`

No arbitrary `+1` denominator is permitted.

Explicit zero handling:

- Down > 0 → ordinary ratio.
- Down = 0 and Up > 0 → +infinity.
- Down = 0 and Up = 0 → undefined/NaN.

Complete 20-session history is required.

Thresholds:

- `> 1.5` — Strong Accumulation
- `> 1.3` and `<= 1.5` — Accumulating
- `0.7 <= U_D <= 1.3` — Neutral
- `< 0.7` — Distribution Warning
- `< 0.6` — Heavy Distribution

Boundary precedence must be explicitly tested.

## 11. Breakout / Volume Signals

`Breakout` and `Breakout Confirmed` remain separate fields.

### 11.1 Breakout setup

Requires:

- Stage 2;
- price within 3% of 52W high;
- latest completed-session Volume_Ratio > 1.5.

No U/D requirement for the setup label.

### 11.2 Breakout Confirmed

Requires all Breakout setup conditions plus `U_D > 1.3`.

### 11.3 Stage-2 precedence

Preserve the source decision-tree distinction between setup and volume confirmation. Do not collapse the two concepts into one label.

## 12. Liquidity Filter

Optional UI/screener filter only; it is not part of the mathematical universe.

`DailyValue ≈ Close × Volume`

`AvgValue20 = mean(DailyValue over latest 20 completed sessions)`

Liquid when:

`AvgValue20 > ₹5 crore`

Apply only after RS/stage calculations. Never recompute RS after filtering.

## 13. RS Line

v1 RS Line is limited to the **current download window**.

No historical constituent adjustment or survivorship-free historical universe reconstruction is claimed for v1.

Future historical RS-line research requires a separate methodology decision.

## 14. Mathematical Integrity Rules

- Calendar months/weeks remain calendar-based.
- Fixed row counts cannot replace calendar definitions.
- Every reference date uses information available on or before that date.
- The upcoming decision session is excluded globally.
- Volume baseline excludes the latest session's own volume.
- U/D includes the latest completed session and excludes the upcoming session.
- Cross-sectional ranking occurs against the specified Nifty Total Market mathematical universe before optional UI filters.
- Missing history produces explicit insufficiency, never fabricated values.
- Forward filling/interpolation requires explicit quantitative justification.
- Optimizations require numerical regression testing against an independent/reference calculation.

## 15. Locked Decision Summary

| Topic | Locked production definition |
|---|---|
| Universe | Official Nifty Total Market constituent CSV |
| Universe source | `ind_niftytotalmarket_list.csv` |
| Universe storage | `data/ind_niftytotalmarket_list.csv` |
| Industry | Exact NSE CSV `Industry` field |
| F&O filtering | None |
| Data source | yfinance |
| Price | `auto_adjust=True`, adjusted Close/High |
| Volume | Raw Volume |
| Decision timing | Pre-market; information through latest completed session |
| RS periods | 3/6/9/12 calendar months |
| RS reference | Last session on/before calendar reference date |
| RS weights | 40/20/20/20 |
| RS rank | `rank(pct=True, method='min') × 98 + 1`, rounded |
| Stage MA | 30-calendar-week **30W MA** |
| Stage MA observations | All valid sessions in calendar window |
| Slope | 10 trading sessions |
| 52W high | 52 calendar weeks |
| 52W minimum | ≥200 valid sessions |
| Volume baseline | Prior 50 sessions, `min_periods=50`, `.shift(1)` |
| U/D | 20 completed sessions ending at latest completed session |
| U/D denominator | No arbitrary `+1`; explicit zero handling |
| Breakout | S2 + within 3% of 52W high + volume >1.5× |
| Breakout Confirmed | Breakout + U/D >1.3 |
| Liquidity | Optional UI-only, 20-session avg Close×Volume > ₹5Cr |
| RS Line | Current download window only |
| Universe refresh | Every Friday ~23:30 IST; GitHub Actions |

## 16. Validation Status

These are locked inputs, not proof of implementation correctness. Each definition must be independently tested on synthetic data, tested on real Nifty Total Market data, audited for leakage, and regression-tested before production completion.
