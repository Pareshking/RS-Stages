# RS-Stages — Mathematical Formulas

**Status:** FORMULATION BASELINE  
**Authority:** `docs/LOCKED_SPEC.md` + approved project decisions  
**Purpose:** Translate locked methodology inputs into explicit mathematical definitions before implementation.

> This document defines the mathematics. It is not evidence that the mathematics has yet been independently validated in code. Validation will be recorded through tests and the validation protocol.

## 1. General Conventions

### 1.1 Universe

The mathematical universe is the set of symbols supplied by the NSE constituent CSV used by the project.

Industry classification is taken directly from that CSV's `Industry` field. No F&O filtering or WealthStar remapping is applied to the core universe.

### 1.2 Pre-market information boundary

RS-Stages makes its daily decision **before the upcoming NSE trading session opens**.

For a decision on trading day `D`, the information set ends at `T`, where `T` is the most recent completed NSE trading session before `D`.

\[
InformationSet(D)=\{data\ available\ through\ T\}
\]

No price, High, Close, Volume, or derived value from the upcoming/incomplete session `D` may enter any signal calculation.

Whenever methodology says "current day/session included", this means **the latest completed session `T`**, not the upcoming decision/execution session `D`.

This is a global look-ahead-bias control.

### 1.3 Dates

All major lookback definitions are calendar-date based unless explicitly stated otherwise.

For a reference date `t` and calendar offset `Δ`, the target date is obtained by subtracting the specified calendar period from `t`. If the target date is not an NSE trading session, use the last available NSE session on or before that target date.

A calendar window means all valid NSE observations whose dates fall within the specified calendar interval; it does not mean a fixed number of rows.

### 1.4 Price and volume inputs

Production inputs:

- `Close`: adjusted Close from yfinance with `auto_adjust=True`.
- `High`: adjusted High from yfinance with `auto_adjust=True`.
- `Volume`: raw share volume.

Open and Low are not required for core calculations.

## 2. Relative Strength Return Components

For reference date `t`, define the four calendar-date reference observations:

- `t3`: last available NSE session on or before `t - 3 calendar months`.
- `t6`: last available NSE session on or before `t - 6 calendar months`.
- `t9`: last available NSE session on or before `t - 9 calendar months`.
- `t12`: last available NSE session on or before `t - 12 calendar months`.

For each horizon `h ∈ {3,6,9,12}`:

\[
R_h(t)=\frac{Close_t}{Close_{t_h}}-1
\]

These are simple price returns, not annualized and not volatility-adjusted.

### 2.1 Weighted RS blend

\[
B(t)=0.40R_3(t)+0.20R_6(t)+0.20R_9(t)+0.20R_{12}(t)
\]

### 2.2 Cross-sectional RS score

For all eligible stocks in the mathematical universe on date `t`, rank `B(t)` using percentile ranking with `method='min'`:

\[
RS(t)=round\left(98\times PercentileRank_{min}(B(t))+1\right)
\]

Stocks without sufficient valid history for the required RS horizons are excluded from ranking.

Validation must explicitly cover ties, NaNs, minimum/maximum observations, and score boundaries.

## 3. RS Line

RS Line v1 is restricted to the current download window. No historical constituent adjustment is performed.

For stock `i`, rebase adjusted Close to its first valid observation in the available window:

\[
P_i^{rebased}(t)=\frac{Close_i(t)}{Close_i(t_0)}
\]

The equal-weight universe index is:

\[
U(t)=mean_i(P_i^{rebased}(t))
\]

The stock relative-strength line is:

\[
RSLine_i(t)=\frac{P_i^{rebased}(t)}{U(t)}
\]

This descriptive RS Line is distinct from the 1–99 RS score.

## 4. 30W MA

**30W MA means a 30-calendar-week Simple Moving Average.** It is not a conventional Weighted Moving Average and not a fixed 150-row average.

For reference date `t`, use all valid NSE sessions in the 30-calendar-week window ending at the latest completed session `T`:

\[
MA_{30W}(T)=mean(Close_s:s\in W_{30}(T))
\]

A complete 30-calendar-week history is required.

### 4.1 Slope

The locked slope window is **10 trading sessions**.

\[
Slope\%(T)=\left(\frac{MA_{30W}(T)}{MA_{30W}(T-10\ sessions)}-1\right)\times100
\]

This is a project-selected implementation rule. It is not to be represented as a proven undisclosed WealthStar internal parameter.

### 4.2 Stage classification

\[
above\_ma=Close_T>MA_{30W}(T)
\]

\[
rising=Slope\%(T)>0
\]

- Stage 2 — Advancing: above MA and rising.
- Stage 3 — Topping: above MA and not rising.
- Stage 4 — Declining: below MA and not rising.
- Stage 1 — Basing: below MA and rising.

Stages are categorical/cyclical states. Never infer transitions from numeric ordering of labels.

## 5. Extension Percentage

\[
Extension\%(T)=\left(\frac{Close_T}{MA_{30W}(T)}-1\right)\times100
\]

Positive means price is above the MA; negative means below.

## 6. 52-Calendar-Week High

Use the preceding **52 calendar weeks** ending at `T`, not a fixed 252-row window:

\[
High_{52W}(T)=max(AdjustedHigh_s:s\in W_{52}(T))
\]

At least **200 valid sessions** must exist inside the window. Otherwise the near-high signal is invalid/false for production purposes.

\[
nearHigh(T)=Close_T\ge0.97\times High_{52W}(T)
\]

## 7. Volume Ratio

The production baseline is the mean raw volume of the **50 prior completed sessions**, excluding the latest completed session's own volume:

\[
VolBase_{50}(T)=mean(V_{T-50},...,V_{T-1})
\]

Equivalent rolling implementation:

`rolling(50, min_periods=50).mean().shift(1)`

Then:

\[
VolRatio(T)=\frac{V_T}{VolBase_{50}(T)}
\]

If 50 prior valid observations are unavailable, the ratio is invalid.

## 8. Up/Down Volume Ratio

For each completed session `t`:

\[
\Delta Close_t=Close_t-Close_{t-1}
\]

\[
UpVol_t=\begin{cases}Volume_t,&\Delta Close_t>0\\0,&otherwise\end{cases}
\]

\[
DownVol_t=\begin{cases}Volume_t,&\Delta Close_t<0\\0,&otherwise\end{cases}
\]

An unchanged close contributes to neither side.

For the latest completed session `T`:

\[
UpVol20_T=\sum_{k=T-19}^{T}UpVol_k
\]

\[
DownVol20_T=\sum_{k=T-19}^{T}DownVol_k
\]

The latest completed session is included. The upcoming decision/execution session is excluded.

\[
UD_T=\frac{UpVol20_T}{DownVol20_T}
\]

No arbitrary `+1` denominator adjustment is permitted.

Zero handling:

- Down > 0 → ordinary ratio.
- Down = 0 and Up > 0 → +infinity.
- Down = 0 and Up = 0 → undefined/NaN.

Complete 20-session history is required.

Thresholds:

- `UD > 1.5` — Strong Accumulation
- `UD > 1.3` and `UD <= 1.5` — Accumulating
- `0.7 <= UD <= 1.3` — Neutral
- `UD < 0.7` — Distribution Warning
- `UD < 0.6` — Heavy Distribution

Boundary precedence must be explicitly tested.

## 9. Breakout / Volume Signals

### 9.1 Breakout setup

Requires:

- Stage 2;
- `nearHigh=True`;
- `VolRatio > 1.5`.

No U/D requirement is required for the setup label.

### 9.2 Breakout Confirmed

Requires all Breakout setup conditions plus:

\[
UD>1.3
\]

Setup and confirmation remain separate fields.

## 10. Liquidity Filter

Liquidity is an optional UI/screener filter only. It is not part of the mathematical universe and must not affect RS ranking.

\[
DailyValue_t=Close_t\times Volume_t
\]

\[
AvgValue20_T=mean(DailyValue_{T-19},...,DailyValue_T)
\]

Liquid when:

\[
AvgValue20_T>₹5\ crore
\]

Apply only after RS/stage calculations.

## 11. Data History Requirement

Fetch sufficient **calendar history** to guarantee every required calendar lookback and trading-session warm-up period.

A fixed row count such as 400 may be an implementation buffer only; it is not a mathematical definition.

## 12. Formula Validation Requirements

Before production implementation is considered mathematically validated, independently test at minimum:

1. Pre-market information boundary.
2. Calendar-month reference-date selection.
3. Four RS returns.
4. 40/20/20/20 blend.
5. Percentile ranking with `method='min'`, ties and NaNs.
6. 30-calendar-week MA.
7. 10-session slope.
8. 52-calendar-week high.
9. ≥200-session minimum.
10. 3% near-high condition.
11. Prior-50-session volume baseline with `shift(1)`.
12. Up/down volume classification.
13. 20-session U/D ratio using the latest completed session.
14. Zero-denominator U/D handling.
15. Breakout vs Breakout Confirmed distinction.
16. Optional liquidity filter isolation.

Each critical formula should have at least one controlled synthetic dataset with independently known expected output.

## 13. Known Epistemic Boundary

The 10-session slope window and formula are locked project decisions. They must not be described as an undisclosed WealthStar parameter.

Source-code snippets using fixed trading-day row counts do not override the project's newer calendar-date decisions.

## 14. Next Engineering Step

Proceed with independent synthetic tests and real-data validation before declaring any production quantitative component complete.

## v2.1 additions

### 10-calendar-week moving average

Let `S` be the sorted, non-null Close series and `T` the latest completed
session. Let `t = asof(S, T)` and `s = asof(S, t - 10 weeks)`, where `asof`
returns the last observed session **on or before** its argument.

```
MA_10W(T) = mean({ S(u) : s <= u <= t })
```

Identical in construction to `MA_30W` with the window length changed. Requires
at least two observations in the window; otherwise explicit insufficiency.

### 52-calendar-week low

With `L` the adjusted Low series, `t = asof(L, T)` and `s = asof(L, t - 52 weeks)`:

```
Low_52W(T) = min({ L(u) : s <= u <= t })       requires >= 200 observations
```

Mirrors `High_52W` exactly.

### Displayed presentation quantities

```
Ext_Pct            = (Close_T / MA_30W(T) - 1) * 100
Pct_From_52W_High  = (Close_T / High_52W(T) - 1) * 100
Range_Position     = (Close_T - Low_52W) / (High_52W - Low_52W)      in [0, 1]
```

`Ext_Pct` is for display. The locked condition remains
`Extended_20Pct = Close_T > 1.20 * MA_30W(T)` and is **not** re-derived from
`Ext_Pct`: the forms are algebraically equal but not bit-identical in floating
point.

### Trend health

```
Trend_Health = |{ Close > MA_30W,
                  Slope_30W > 0,
                  MA_10W > MA_30W,
                  Close > MA_10W,
                  RS_Score >= 50 }|                                 in [0, 5]
```

### Participation

For a set of stocks `U`, let `C` be those with a classifiable Stage:

```
Above_30W(U)     = |{ i in C : Close_i > MA_30W_i }|
Participation(U) = Above_30W(U) / |C| * 100
```

By the locked Stage classification, `{ i : Close_i > MA_30W_i } = { i : Stage_i
in {2, 3} }`, so participation may be evaluated from either form.

For the breadth history, participation at session `u` counts only symbols whose
moving average is defined at `u`, and each symbol's average at `u` is evaluated
using data through `u` only.
