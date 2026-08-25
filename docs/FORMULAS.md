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

Two v2.2 boundaries are recorded here as well.

Three trend-template thresholds (a 30% minimum advance off the 52-week low, a
25% maximum distance below the 52-week high, and a relative-strength floor of
70) are the source's stated values for a different market and period. They have
not been validated against NSE history and are labelled provisional wherever
they surface. They must not be described as tuned or as verified here.

The count of volatility contractions within a base is **not implemented**. Four
detector designs were measured against two of the source's worked examples and
all four failed to reproduce the count; base duration, deepest and tightest
corrections did reproduce. The count and its footprint notation must not be
described as available, and no estimate of them may be published in place of the
measurement. LOCKED_SPEC §10.5.2 holds the evidence.

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

## v2.2 additions

### A naming collision, stated first

`RS Line` in §3 and `RS_Line` in this section are **different constructions**
that unfortunately share a name.

```
§3   (v1)    RSLine_i(t) = P_i_rebased(t) / U(t)      denominator: equal-weight universe
v2.2         RS_Line_i(t) = Close_i(t) / Close_B(t)   denominator: benchmark index
```

§3's line is rebased to the start of the download window and measures a stock
against the average of its peers. The v2.2 line is an unrebased ratio against
the benchmark, which is the construction the RS-divergence fields are defined
on. They are not interchangeable and neither is derived from the other. Only
the v2.2 line feeds `RS_Line_At_High` and `RS_Line_NH_Before_Price`.

The v2.2 ratio is taken on the sessions the two series actually share, by inner
join. A benchmark session the stock did not trade — or the reverse — is dropped
rather than filled, since supplying either side's missing price would invent the
quantity being measured. `RS_LINE_MIN_OVERLAP = 200` shared sessions are
required before a 52-week line high is reported; below that the field is
explicitly insufficient.

```
RS_Line_High_52W(T)      = max over the trailing 52 calendar weeks of RS_Line
RS_Line_At_High          = RS_Line(T) >= RS_Line_High_52W(T) * (1 - 0.005)
RS_Line_NH_Before_Price  = RS_Line_At_High AND Pct_From_52W_High < 0
```

The 0.005 tolerance exists so "at a new high" is not a floating-point equality.
The ordering in the third line is the whole signal: strength reaching a new high
while price has not is the leading tell. Once price is also at its high the
stock is already advancing, which is a breakout, not an early warning.

### Session averages

```
SMA_n(T) = mean of the n closes at or before T that exist
```

The average is taken over `n` observations that are present, never over a
window that happens to contain `n` slots. Fewer than `n` available closes is
explicit insufficiency, not a shorter average.

**These are session counts and `MA_30W` is a calendar-week window.** Thirty
calendar weeks is not 150 sessions. The two constructions must not be
substituted for one another in code or in prose.

```
SMA_Rising_n(T) = SMA_n(T) > SMA_n(T - 21 sessions)
```

### Trend template

Eight criteria, all required. Seven are structural and transfer without
interpretation; two carry numeric tolerances stated by the source for a
different market and era.

```
TT1  Close > SMA_150  and  Close > SMA_200
TT2  SMA_150 > SMA_200
TT3  SMA_200 rising over the trailing 21 sessions
TT4  SMA_50  > SMA_150  and  SMA_50 > SMA_200
TT5  Close > SMA_50
TT6  Close >= Low_52W  * 1.30           <- provisional threshold
TT7  Close >= High_52W * 0.75           <- provisional threshold
TT8  RS_Score >= 70                     <- provisional threshold

Trend_Template_Pass = TT1 AND ... AND TT8
```

TT6, TT7 and TT8 are implemented at the source's stated values and surface
labelled provisional. They are **not** retuned against NSE history, because no
holdout of sufficient size exists yet, and they are not replaced with values
chosen here, because inventing a threshold the source does not state is exactly
what this project forbids. See DECISION_LOG D-2.2.2.

TT8 is cross-sectional and therefore resolves after `RS_Score` exists, not
during per-symbol analysis.

### Average true range

```
TR(t)     = max( High(t) - Low(t),
                 |High(t) - Close(t-1)|,
                 |Low(t)  - Close(t-1)| )

ATR_Pct(T) = mean(TR over the trailing 14 sessions) / Close(T) * 100
```

### Volatility contraction — published subset

```
Base_Depth_Pct = (1 - min(Low over base) / max(High over base)) * 100
```

Measured peak to trough **across the base itself**. This is deliberately not
`Pct_From_52W_High`: a stock can sit far below a distant high while building a
shallow base, and the two quantities answer different questions.

```
Contraction_Ratio = range of the last block / range of the first block
                    over 5 blocks spanning 50 sessions

Volume_Dryup      = mean(Volume, last 10 sessions) / mean(Volume, last 50)

VCP_Setup = Contraction_Ratio <= 0.60
            AND Volume_Dryup <= 0.80
            AND Stage is Stage 2
            AND Base_Depth_Pct <= 35
            AND contractions >= 2
```

The Stage 2 gate and the depth bound are **required arguments**, not defaults.
Without them the first two conditions are satisfied by a stock declining
quietly, which is the opposite of the pattern being screened for; 33 of 112
flagged symbols were in decline. A default parameter would have let existing
call sites retain that defect silently. See DECISION_LOG D-2.2.5.

```
VCP_Pivot    = highest High within the final contraction
Pct_To_Pivot = (VCP_Pivot / Close(T) - 1) * 100
```

### Stage 1 readiness

A count in [0, 4] over stocks classified Stage 1, resolved cross-sectionally
after `RS_Score` is available:

```
Stage1_Readiness = |{ Slope_30W >= 0,
                      Close > MA_30W,
                      RS_Score >= 50,
                      Volume_Dryup <= 0.80 }|
```

### Fields specified but not computed

`VCP_Contractions` and the `nW d/t nT` footprint notation are specified in
LOCKED_SPEC §10.5.1 and are **not** published. Four detector designs failed
validation against the source's own worked examples; §10.5.2 carries the record.
The base window, depth, pivot and volume rule above are the validated subset and
are published. The contraction count is withheld rather than estimated.
