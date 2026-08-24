# RS-Stages — Methodology Overview

This document describes the production quantitative workflow and its interpretation layer. Exact formulas are maintained in `docs/FORMULAS.md`; current locked inputs and decisions are maintained in `docs/LOCKED_SPEC.md`; the deterministic Action mapping is in `docs/ACTION_SPEC.md`.

## 1. Information Boundary

RS-Stages makes its decision before the upcoming NSE session opens. The latest completed NSE session is therefore the terminal observation for every signal calculation.

## 2. Universe and Data

The stock universe and Industry classification come from the NSE constituent CSV, with no F&O filtering. Market history is obtained from yfinance using adjusted Close/High and raw Volume.

## 3. Relative Strength

For each eligible stock, calculate simple Close returns over 3, 6, 9 and 12 calendar months. Combine them using 40/20/20/20 weights and convert the cross-sectional blend into the 1–99 RS score. Under the adopted guide, RS 80–99 is leadership, 50–79 is adequate, and <50 is lagging.

## 4. Stage Analysis

Stage analysis uses a 30-calendar-week Simple Moving Average containing all valid sessions in the calendar window. Its direction is measured using the 10-session percentage slope. Price-versus-MA and slope sign determine Stages 1–4.

## 5. High and Volume Conditions

The high reference is the maximum adjusted High over the preceding 52 calendar weeks, subject to at least 200 valid sessions. Near-high means the latest completed Close is within 3% of that high.

Volume strength uses the latest completed session's raw volume divided by the mean of its 50 prior completed observations, implemented as a 50-observation rolling mean followed by `shift(1)`.

## 6. Up/Down Volume

Each completed session is classified from Close-to-prior-Close movement. Rising Close assigns volume to Up Volume; falling Close assigns it to Down Volume; unchanged Close contributes to neither. The ratio uses the 20 completed sessions ending at the latest completed session, with explicit zero-denominator handling.

## 7. Breakout Signals

Breakout requires Stage 2, the 3%-from-52W-high condition, and Volume Ratio above 1.5. Breakout Confirmed adds U/D above 1.3. These remain separate outputs.

## 8. Guide-derived timing

The adopted guide adds two deterministic timing warnings:

- Extension >20% = Close >1.20 × 30W MA.
- Below 50DMA = Close below the 50-session simple moving average.

These warnings affect Action timing but do not change Stage classification. The guide mentions pullback + volume drying, but the repository does not contain a sufficiently precise validated detector, so no such state is fabricated.

## 9. Production Action

The interpretation layer now uses nine labels: `BUY★`, `BUY`, `HOLD`, `WAIT`, `WATCH★`, `WATCH`, `REDUCE`, `SELL`, `AVOID`.

Stage takes precedence over RS when they conflict. Stage 4 is SELL; Stage 3 is SELL for RS <50 and REDUCE otherwise; Stage 1 maps to WATCH★/WATCH/AVOID by RS band. Stage 2 evaluates distribution, RS band, timing warnings and breakout state. See `docs/ACTION_SPEC.md` for the complete deterministic mapping.

The Action is a transparent project specification over visible quantitative outputs, not a claim that either source book published this exact combined nine-label mechanical system.

## 10. Liquidity

The ₹5 crore 20-session average value threshold remains an optional UI/screener filter applied after the core calculations. It must not alter RS ranking.

## 11. Research Platform UI

The production UI is structured as Dashboard, Screener, Industries, Movers, Stock and Methodology. The Screener ends with the Action column. Stock pages expose the Action reason, evidence checklist, calculation detail and an interactive TradingView Lightweight Charts price/30W-MA view driven by repository data.

## 12. Validation

Every critical calculation and new Action condition must be independently validated using controlled datasets, manual/reference calculations and regression tests. The pre-market boundary and calendar-window definitions remain explicit look-ahead controls.
