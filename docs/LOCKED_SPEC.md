# RS-Stages — Locked Quantitative Specification

**Status:** LOCKED INPUTS — v1.0
**Date:** 2026-08-24
**Repository:** `Pareshking/RS-Stages`
**Primary technology:** Streamlit

This document contains the project-level quantitative decisions explicitly locked for RS-Stages after review of the supplied NSE Momentum System specification and discussion. It is the authoritative implementation input for the decisions below.

A locked decision must not be silently changed. If later evidence suggests that a decision is mathematically wrong, inconsistent with the source methodology, or impossible to implement correctly, raise a new decision/audit item and document the evidence before changing it.

## 1. Decision Hierarchy

1. Explicit project decisions recorded in this document.
2. The supplied methodology/source material, subject to explicit project decisions above.
3. Clearly documented implementation assumptions.
4. Conventional practice is not a substitute for the specified methodology.

Performance or backtest improvement is never sufficient reason to change a locked mathematical definition.

## 2. Universe and Sector Classification

- The mathematical universe is determined by the NSE constituent CSV used by RS-Stages.
- Symbols are taken from that NSE CSV.
- Sector/industry classification follows exactly the `Industry` information supplied by that NSE CSV.
- No F&O filtering.
- No WealthStar sector remapping.
- No consolidation of NSE industries unless a future explicit decision changes this.
- The universe used for cross-sectional RS ranking is not reduced by the optional liquidity filter.

## 3. Market Data

Production data source:

- **yfinance**.
- `auto_adjust=True`.
- Required price fields: adjusted Close and adjusted High.
- Volume remains raw/unadjusted.
- No Open or Low is required for the core RS-Stages calculations.

Data transformations must be explicit and auditable. Missing observations, duplicate dates, stale data, corporate actions, and calendar mismatches must be tested rather than silently normalized.

## 4. Historical Data / Warm-up

The implementation must fetch **sufficient calendar history** to guarantee that every required calendar lookback and warm-up calculation can be evaluated correctly.

A fixed row count such as 400 rows may be used as an implementation buffer after obtaining sufficient history, but it is **not a mathematical definition** of any RS-Stages lookback period.

The implementation must never substitute fixed trading-row counts for calendar-date definitions merely because a row count is convenient.

## 5. Relative Strength (RS)

### 5.1 Lookback convention

All RS lookbacks are **calendar-date based**:

- 3 calendar months
- 6 calendar months
- 9 calendar months
- 12 calendar months

For each reference date, use the last available NSE trading session on or before that calendar reference date.

Do **not** implement production RS lookbacks as fixed 63/126/189/252-row offsets.

### 5.2 Returns

For each stock and period:

`R_period = Close_latest / Close_reference - 1`

where `Close_reference` is the last available adjusted Close on or before the calendar reference date.

### 5.3 Blend

`Blend = 0.40 × R3M + 0.20 × R6M + 0.20 × R9M + 0.20 × R12M`

### 5.4 Cross-sectional RS score

RS is an IBD/O'Neil-style cross-sectional momentum ranking, not a Jegadeesh-Titman score.

Across the valid universe:

`RS = rank(Blend, pct=True, method='min') × 98 + 1`

Then round to an integer, producing the intended 1–99 scale.

Stocks without sufficient valid history are excluded from the ranking rather than assigned a misleading numerical score.

### 5.5 No skip-month

The 1-month recent period is not skipped. The 3/6/9/12 calendar-month returns are used directly.

## 6. Weinstein Stage Moving Average

### 6.1 Moving-average window

The production stage moving average is a **30-calendar-week moving average (30 WMA)**.

It is calculated from all valid NSE trading sessions contained in the preceding 30 calendar weeks ending at the latest available trading session.

This is **not** a fixed 150-row moving average.

The label `30 WMA` should be preferred in new implementation/documentation to avoid confusing the production definition with a 150-trading-day approximation.

### 6.2 Minimum history

A stock must have a complete 30-calendar-week history sufficient for the production 30 WMA. Stocks without sufficient history are classified as `Insufficient history` for calculations that require the WMA.

### 6.3 Slope

The slope window is **10 trading sessions**.

The working production formulation is:

`Slope % = (MA_today / MA_10_sessions_ago - 1) × 100`

The 10-session slope is a project-selected implementation rule. It must not be described as independently proven to be WealthStar's undisclosed exact internal window.

### 6.4 Stage classification

Let:

`above_ma = Close_today > MA_today`

`rising = Slope > 0`

Then:

- Stage 2 — Advancing: `above_ma = True` and `rising = True`
- Stage 3 — Topping: `above_ma = True` and `rising = False`
- Stage 4 — Declining: `above_ma = False` and `rising = False`
- Stage 1 — Basing: `above_ma = False` and `rising = True`

Stages are categorical/cyclical states. Never infer transition direction using numeric stage ordering.

## 7. 52-Week High

The 52-week high is **calendar-date based**.

Use the preceding **52 calendar weeks** ending at the latest available trading session and evaluate the maximum valid adjusted High within that calendar window.

Minimum history requirement:

- At least **200 valid sessions** must be available within the 52-calendar-week window.
- If fewer than 200 valid sessions are available, `near_high` must not be treated as valid.

This is deliberately a calendar-window definition and must not be replaced by a fixed 252-row rolling window.

## 8. Volume Baseline

The volume baseline uses the prior 50 complete sessions:

`Volume_MA50 = rolling(50, min_periods=50).mean().shift(1)`

The current session must not enter its own volume baseline.

Therefore:

`Volume_Ratio = Current_Volume / Prior_50_Session_Average_Volume`

A stock without a complete prior 50-session baseline is not eligible for calculations requiring this ratio.

## 9. Up/Down Volume Ratio

Use a 20-session window:

- Up-volume = sum of volume on sessions classified as up sessions.
- Down-volume = sum of volume on sessions classified as down sessions.
- No shift: the current session is included in the 20-session U/D calculation when calculating today's signal.

The production ratio is:

`U_D = Up_Volume / Down_Volume`

Do **not** add an arbitrary `+1` to the denominator.

If `Down_Volume == 0`, the implementation must handle the condition explicitly and deterministically (for example, as an infinite/undefined ratio according to the signal semantics) rather than altering the formula with an arbitrary constant.

Thresholds:

- `> 1.5` — Strong Accumulation
- `> 1.3` — Accumulating
- `0.7–1.3` — Neutral
- `< 0.7` — Distribution Warning
- `< 0.6` — Heavy Distribution

Boundary precedence must be explicitly tested because the threshold intervals overlap semantically.

## 10. Breakout / Volume Signal Logic

`Breakout` and `Breakout Confirmed` are separate concepts and must remain separate fields in the UI/data model.

### 10.1 Breakout — Setup

A Breakout setup requires:

- Stage 2
- Price within 3% of the 52-week high
- Current volume ratio > 1.5× prior-50-session baseline

No U/D requirement is applied to the `Breakout` setup label.

### 10.2 Breakout Confirmed

A Breakout Confirmed signal requires all Breakout setup conditions plus:

- U/D ratio > 1.3

### 10.3 Stage-2 volume decision precedence

For Stage 2, evaluate in this conceptual order:

1. Breakout setup condition.
2. U/D condition.
3. Volume-ratio condition.
4. Otherwise Normal.

The exact output labels and precedence must preserve the distinction between price/setup state and volume confirmation.

## 11. Liquidity Filter

Liquidity is an **optional UI/screener filter only**.

Definition:

`Daily traded value ≈ Close × Volume`

`20-day average traded value > ₹5 crore`

The filter must be applied **after** RS and stage calculations.

It must never be applied before cross-sectional RS ranking because pre-filtering changes the population against which percentile ranks are calculated.

Therefore:

- Mathematical universe = all symbols from the NSE constituent CSV.
- Liquidity filter = optional presentation/screener filter.
- RS/stage values are not recomputed after liquidity filtering.

## 12. RS Line

RS Line scope for v1 is limited to the **current download window**.

No historical constituent adjustment is required for v1.

No survivorship-free historical universe reconstruction is claimed by this v1 RS Line definition.

Any future historical RS-line research must be treated as a separate methodology decision.

## 13. Important Mathematical Integrity Rules

The following are mandatory implementation constraints:

- Calendar-month and calendar-week definitions must remain calendar-based.
- Fixed row counts must never be silently substituted for calendar periods.
- Lookback reference dates must use only information available on or before the reference date.
- Volume baselines must not include today's volume.
- Current-session U/D calculations may include today's volume as explicitly defined.
- Cross-sectional ranking must occur against the specified mathematical universe before optional UI filters.
- Missing history must produce explicit insufficiency rather than fabricated values.
- Forward filling or interpolation must not be introduced without a separately documented quantitative justification.
- Any optimization must be numerically regression-tested against the reference implementation.

## 14. Locked Decision Summary

| Topic | Locked production definition |
|---|---|
| Universe | NSE constituent CSV symbols |
| Industry | Exact NSE CSV `Industry` field |
| F&O filtering | None |
| Data source | yfinance |
| Price | `auto_adjust=True`, adjusted Close/High |
| Volume | Raw Volume |
| History | Sufficient calendar history; row count only an implementation buffer |
| RS periods | 3/6/9/12 calendar months |
| RS reference price | Last session on/before calendar reference date |
| RS weights | 40/20/20/20 |
| RS rank | `rank(pct=True, method='min') × 98 + 1` |
| Skip month | No |
| Stage MA | 30-calendar-week WMA |
| Stage MA rows | All valid sessions inside calendar window |
| Slope | 10 trading sessions |
| Stages | Price vs MA + slope sign |
| 52W high | 52 calendar weeks |
| 52W minimum history | ≥200 valid sessions |
| Volume baseline | Prior 50 sessions, `min_periods=50`, `.shift(1)` |
| U/D | 20-session ratio, no shift |
| U/D denominator | No arbitrary `+1`; explicit zero handling |
| Breakout | S2 + within 3% of 52W high + volume >1.5× |
| Breakout Confirmed | Breakout + U/D >1.3 |
| Liquidity | Optional UI-only, 20d avg Close×Volume > ₹5Cr |
| RS Line | Current download window only |

## 15. Validation Status

These are **locked project inputs**, not yet proof that the implementation is correct.

Before any production implementation is declared complete, each definition must be translated into explicit mathematics, independently tested with synthetic data, tested on real NSE data, audited for time-series leakage, and regression-tested.

Where the supplied source material itself contains conflicting historical formulas, this locked document supersedes those obsolete implementation snippets according to the explicit project decisions recorded during the 2026-08-24 review.
