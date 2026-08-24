# RS-Stages — Methodology Overview

This document describes the locked quantitative workflow at a conceptual level. Exact formulas are maintained in `docs/FORMULAS.md`; locked inputs are maintained in `docs/LOCKED_SPEC.md`.

## 1. Information Boundary

RS-Stages makes its decision before the upcoming NSE session opens. The latest completed NSE session is therefore the terminal observation for every signal calculation.

## 2. Universe and Data

The stock universe and Industry classification come from the NSE constituent CSV used by the project, with no F&O filtering. Market history is obtained from yfinance using adjusted Close/High and raw Volume.

## 3. Relative Strength

For each eligible stock, calculate simple Close returns over 3, 6, 9, and 12 calendar months. Combine them using the locked 40/20/20/20 weights and convert the cross-sectional blend into the locked 1–99 percentile-style RS score.

## 4. Stage Analysis

Stage analysis uses a 30-calendar-week Simple Moving Average. The MA contains all valid sessions in the calendar window rather than a fixed number of trading rows. Its direction is measured using the locked 10-session percentage slope. Price-versus-MA and slope sign determine Stages 1–4.

## 5. High and Volume Conditions

The high reference is the maximum adjusted High over the preceding 52 calendar weeks, subject to at least 200 valid sessions. Near-high means the latest completed Close is within 3% of that high.

Volume strength uses the latest completed session's raw volume divided by the mean of its 50 prior completed observations, implemented as a 50-observation rolling mean followed by `shift(1)`.

## 6. Up/Down Volume

Each completed session is classified from Close-to-prior-Close movement. Rising Close assigns volume to Up Volume; falling Close assigns it to Down Volume; unchanged Close contributes to neither. The ratio uses the 20 completed sessions ending at the latest completed session, with explicit zero-denominator handling.

## 7. Breakout Signals

Breakout requires Stage 2, the 3%-from-52W-high condition, and Volume Ratio above 1.5. Breakout Confirmed adds U/D above 1.3. These are intentionally separate outputs.

## 8. Liquidity

The ₹5 crore 20-session average value threshold is an optional UI/screener filter applied after the core calculations. It must not alter RS ranking.

## 9. Validation

Every critical calculation must be independently validated using controlled datasets, manual/reference calculations, and regression tests. The pre-market boundary and calendar-window definitions are explicit look-ahead controls.
