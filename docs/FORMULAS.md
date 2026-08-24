# RS-Stages — Mathematical Formulas

**Status:** FORMULATION BASELINE  
**Authority:** `docs/LOCKED_SPEC.md` + approved project decisions  
**Purpose:** Translate locked methodology inputs into explicit mathematical definitions before implementation.

> This document defines the mathematics. It is not evidence that the mathematics has yet been independently validated in code. Validation will be recorded through tests and the validation protocol.

---

## 1. General Conventions

### 1.1 Universe

The mathematical universe is the set of symbols supplied by the NSE Nifty 500 constituent CSV used by the project.

Sector/industry classification is taken directly from that CSV's `Industry` field. No F&O filtering, consolidation, or WealthStar remapping is applied to the core universe.

### 1.2 Pre-market information boundary

RS-Stages makes its daily decision **before the upcoming NSE trading session opens**.

For a decision on trading day `D`, the information set ends at `T`, where `T` is the most recent completed NSE trading session before `D`.

Therefore:

\[
InformationSet(D)=\{data\ available\ through\ T\}
\]

No price, high, volume, close, or derived value from the upcoming/incomplete session `D` may enter the signal calculation.

Whenever a methodology says "current day/session included", this means **the latest completed session `T`**, not the upcoming decision/execution session `D`.

This is a global look-ahead-bias control and applies to every quantitative component.

### 1.3 Dates

All major lookback definitions are calendar-date based unless explicitly stated otherwise.

For a reference date `t` and calendar offset `Δ`, the target date is obtained by subtracting the specified calendar period from `t`. If the target date is not an NSE trading session, use the last available NSE session on or before that target date.

A calendar window therefore means all valid NSE observations whose dates fall within the specified calendar interval; it does not mean a fixed number of rows.

### 1.4 Price and volume inputs

Production inputs:

- `Close`: adjusted Close from yfinance with `auto_adjust=True`.
- `High`: adjusted High from yfinance with `auto_adjust=True`.
- `Volume`: raw share volume.

Open and Low are not required by the locked signal definitions.

---

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

These are simple price returns, not annualized returns and not volatility-adjusted returns.

### 2.1 Weighted RS blend

\[
B(t)=0.40R_3(t)+0.20R_6(t)+0.20R_9(t)+0.20R_{12}(t)
\]

The one-month period is not separately included in the locked RS blend.

### 2.2 Universe percentile rank

For all eligible stocks in the mathematical universe on date `t`, rank the blended return `B(t)` using percentile ranking with `method='min'`.

The locked transformation is:

\[
RS(t)=round\left(98\times PercentileRank_{min}(B(t))+1\right)
\]

The intended displayed range is 1–99.

Stocks without sufficient data for the required RS horizons are excluded from the RS ranking rather than receiving a fabricated score.

**Validation requirement:** verify the exact behaviour of the percentile formula, including ties, NaNs, minimum/maximum observations, and whether rounding produces any boundary values outside the intended range.

---

## 3. RS Line

RS Line v1 is restricted to the current download window. No historical constituent adjustment is performed.

For each stock `i`, rebase its adjusted Close series to the first valid observation in the available window:

\[
P_i^{rebased}(t)=\frac{Close_i(t)}{Close_i(t_0)}
\]

The equal-weight universe index is:

\[
U(t)=mean_i\left(P_i^{rebased}(t)\right)
\]

The stock's relative-strength line is:

\[
RSLine_i(t)=\frac{P_i^{rebased}(t)}{U(t)}
\]

Interpretation:

- `RSLine > 1` means the stock is outperforming the equal-weight universe index on the rebased basis.
- Rising RS Line indicates increasing relative performance.

This is a descriptive relative-performance series and is distinct from the 1–99 RS score.

---

## 4. 30W MA

### 4.1 Definition

**30W MA means 30-calendar-week Simple Moving Average, not a weighted moving average.**

For reference date `t`, define the 30-calendar-week interval ending at `t`. Include all valid NSE trading sessions in that interval.

Then:

\[
MA_{30W}(t)=mean\left(Close_s: s\in W_{30}(t)\right)
\]

where `W30(t)` is the set of valid NSE sessions inside the defined 30-calendar-week window.

This is explicitly **not**:

- a 150-row rolling mean,
- a conventional weighted moving average,
- or a fixed trading-day approximation.

### 4.2 Minimum history

A complete 30-calendar-week window is required. If the required window cannot be established from sufficient valid observations, the stock receives `Insufficient history` rather than a partially populated MA signal.

### 4.3 MA slope

The locked slope window is **10 trading sessions**.

The precise slope formulation must be retained as an explicit implementation contract and independently validated before production implementation. The source material establishes the 10-session window but the project must not infer an alternative slope formula without documenting it.

---

## 5. Stage Classification

Stage classification uses the relationship between price and the 30W MA together with the direction of the MA slope.

The stage transition system must use the explicit `TRANSITION_DIRECTION` matrix rather than numeric ordering of stage labels.

The exact transition matrix and boundary conventions must be represented explicitly in the implementation and tests.

The production implementation must not silently infer stage order from strings such as `S1 < S2 < S3 < S4`.

---

## 6. Extension Percentage

Where defined, extension from the 30W MA is:

\[
Extension\%(t)=\left(\frac{Close_t}{MA_{30W}(t)}-1\right)\times100
\]

The sign convention is:

- positive = price above the MA;
- negative = price below the MA;
- zero = price equal to the MA.

---

## 7. 52-Calendar-Week High

### 7.1 Window

The high window is **52 calendar weeks**, not a fixed 252-row window.

Let `H52(t)` contain all valid adjusted High observations within the 52-calendar-week window ending at `t`.

Then:

\[
High_{52W}(t)=max(H52(t))
\]

### 7.2 Minimum valid observations

At least **200 valid sessions** must be available within the 52-calendar-week window.

If fewer than 200 valid sessions are available:

\[
nearHigh(t)=False
\]

and the 52-week-high signal is treated as insufficient for the near-high test.

### 7.3 Near-high condition

The locked threshold is within 3% of the 52-week high:

\[
nearHigh(t)=\left(Close_t \ge 0.97\times High_{52W}(t)\right)
\]

This condition is used for setup/breakout classification.

---

## 8. Volume Ratio

### 8.1 Prior-50-session baseline

Define the volume baseline at date `t` as the mean raw volume of the **preceding 50 trading sessions**, excluding the latest completed session itself:

\[
VolBase_{50}(t)=mean(V_{t-50},...,V_{t-1})
\]

Equivalent rolling implementation concept:

`rolling(50, min_periods=50).mean().shift(1)`

### 8.2 Volume ratio

\[
VolRatio(t)=\frac{V_t}{VolBase_{50}(t)}
\]

Here `t` is the **latest completed trading session in the pre-market information set**. The upcoming decision/execution session must never enter the calculation.

If 50 prior valid observations are unavailable, the volume ratio is not considered valid.

---

## 9. Up/Down Volume Ratio

### 9.1 Direction classification

For each completed session `t`:

\[
\Delta Close_t=Close_t-Close_{t-1}
\]

Define:

\[
UpVol_t=
\begin{cases}
Volume_t,& \Delta Close_t>0\\
0,& otherwise
\end{cases}
\]

\[
DownVol_t=
\begin{cases}
Volume_t,& \Delta Close_t<0\\
0,& otherwise
\end{cases}
\]

An unchanged close contributes to neither side.

### 9.2 Twenty-session sums

For the latest completed session `T` available before the decision:

\[
UpVol20_T=\sum_{k=T-19}^{T}UpVol_k
\]

\[
DownVol20_T=\sum_{k=T-19}^{T}DownVol_k
\]

The latest completed session **is included**. The upcoming decision/execution session is excluded because its data is not yet available.

### 9.3 U/D ratio

\[
UD_T=\frac{UpVol20_T}{DownVol20_T}
\]

The arbitrary `+1` denominator adjustment from the source implementation is **not** part of the locked RS-Stages production mathematics.

Zero-denominator handling must be deterministic:

- `DownVol20 > 0` → ordinary finite ratio.
- `DownVol20 = 0` and `UpVol20 > 0` → positive infinity.
- `DownVol20 = 0` and `UpVol20 = 0` → undefined/NaN.

A complete 20-session history is required for a valid U/D ratio.

### 9.4 Thresholds

Locked thresholds:

- `UD > 1.5` → Strong Accumulation
- `UD > 1.3` and `UD <= 1.5` → Accumulating
- `0.7 <= UD <= 1.3` → Neutral
- `UD < 0.7` → Distribution Warning
- `UD < 0.6` → Heavy Distribution

Boundary precedence must be explicit in implementation tests.

---

## 10. Breakout and Volume Signals

Two concepts remain separate.

### 10.1 Setup: Breakout

A Setup `Breakout` requires:

\[
Stage=S2
\]

AND

\[
nearHigh=True
\]

AND

\[
VolRatio>1.5
\]

No U/D condition is required for the Setup label.

### 10.2 Volume signal: Breakout Confirmed

`Breakout Confirmed` requires all Setup conditions plus:

\[
UD>1.3
\]

The UI must expose Setup and Volume signal separately. They must never be collapsed into one field.

### 10.3 Stage-2 precedence

For Stage 2, the decision logic must preserve the source-defined priority relationship:

1. Breakout condition is evaluated first.
2. U/D condition is then considered according to the locked signal classification.
3. Volume-ratio conditions are evaluated according to the explicit decision tree.
4. Normal is the residual category.

The implementation must preserve the distinction between a Breakout Setup and Breakout Confirmed volume confirmation.

---

## 11. Liquidity Filter

Liquidity is **not part of the mathematical universe and must not affect RS ranking**.

It is a post-computation UI filter.

Define daily approximate traded value:

\[
DailyValue_t=Close_t\times Volume_t
\]

Then:

\[
AvgValue20_t=mean(DailyValue_{t-19},...,DailyValue_t)
\]

The stock is liquid under the optional UI filter when:

\[
AvgValue20_t>₹5\ crore
\]

RS scores and stages must never be recomputed after applying this filter.

---

## 12. Data History Requirement

Production data retrieval must obtain sufficient **calendar history** to calculate every required calendar window and trading-session warm-up period.

A fixed row count such as 400 may be used as an implementation buffer after sufficient calendar history has been obtained, but it is not itself a mathematical definition.

The implementation must not use a row-count shortcut where it changes the locked calendar-date mathematics.

---

## 13. Formula Validation Requirements

Before production implementation is considered mathematically validated, create independent tests for at least:

1. Pre-market information boundary.
2. Calendar-month reference-date selection.
3. Four RS return calculations.
4. 40/20/20/20 RS blend.
5. Percentile ranking with `method='min'`, ties and NaNs.
6. 30-calendar-week MA.
7. 10-trading-session slope.
8. 52-calendar-week high.
9. ≥200-session minimum for the 52W high.
10. 3% near-high condition.
11. Prior-50-session volume baseline with `shift(1)`.
12. Up/down volume classification.
13. 20-session U/D ratio using the latest completed session.
14. Zero-denominator U/D handling.
15. Breakout vs Breakout Confirmed distinction.
16. Optional liquidity filter not affecting mathematical RS ranking.

Each critical formula should have at least one controlled synthetic dataset for which the expected answer is independently known.

---

## 14. Known Epistemic Boundary

The 10-trading-session MA slope window is a locked project input, but the underlying source material labels it as observed/working methodology rather than an independently proven universal definition. The project must preserve that distinction.

Likewise, source-code snippets using fixed trading-day row counts are not to override the project's newer calendar-date decisions.

---

## 15. Next Engineering Step

The next loop stage is **TEST/VALIDATE** against these formulations using synthetic datasets and independent calculations before building the production Streamlit application.
