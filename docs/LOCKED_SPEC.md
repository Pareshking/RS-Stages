# RS-Stages — Locked Quantitative & Decision Specification

**Status:** LOCKED — v2.1  
**Date:** 2026-08-24  
**Repository:** `Pareshking/RS-Stages`  
**Primary technology:** Streamlit

> **Specification change:** The supplied **NSE Signal Interpretation Guide (Aug 2026)** is now the production specification for RS/Stage interpretation and Action decisions. The earlier v1.2 document was an engineering baseline and is superseded where this v2 document differs.

## 1. Authority hierarchy

1. Explicit project decisions in this v2 specification.
2. The supplied NSE Signal Interpretation Guide for interpretation/action rules.
3. Source books for their documented concepts: Weinstein stage structure and O'Neil RS/breakout principles.
4. Clearly documented implementation assumptions.

No implementation may silently invent a missing mathematical definition. If the guide names a condition without enough information to calculate it, the condition remains explicitly unavailable until operationalized and tested.

## 2. Universe and classification

- Production universe: official Nifty Total Market constituent CSV: `data/ind_niftytotalmarket_list.csv`.
- The official CSV is authoritative for the live constituent count; do not hard-code exactly 750.
- Industry is exactly the NSE CSV `Industry` field.
- No F&O filtering.
- No WealthStar sector remapping.
- Optional liquidity filtering never changes the mathematical RS ranking universe.
- Universe refresh remains the repository's scheduled Friday process.

## 3. Market data and information boundary

- Data source: yfinance.
- `auto_adjust=True`.
- Core price inputs: adjusted Close and adjusted High.
- Volume: raw/unadjusted.
- Decisions are pre-market for the upcoming NSE session.
- For decision session D, only information through the latest completed NSE session T may be used.
- No upcoming/incomplete-session data may enter calculations.
- Missing history produces explicit insufficiency; never fabricated values.

## 4. Relative Strength

- Lookbacks: 3, 6, 9 and 12 **calendar months**.
- Reference: last available NSE session on or before each calendar reference date.
- `R_period = Close_latest / Close_reference - 1`.
- Blend: `0.40×R3M + 0.20×R6M + 0.20×R9M + 0.20×R12M`.
- Cross-sectional score: `rank(Blend, pct=True, method='min') × 98 + 1`, rounded to integer 1–99.
- No skip month.
- Ranking occurs before optional liquidity UI filters.

### RS interpretation — NEW v2

- **80–99:** leadership.
- **50–79:** adequate, not leadership.
- **<50:** lagging.

The previous UI thresholds of RS 85/70 are retired.

## 5. Stage — 30W MA

The 30W MA remains a **30-calendar-week SMA over all valid NSE sessions in the calendar window**, ending at T. It is not a fixed 150-row trading-day average.

Slope remains:

`Slope%(T) = (MA_30W(T) / MA_30W(T-10 sessions) - 1) × 100`.

Classification:

- Stage 2 — Advancing: Close > MA and slope > 0.
- Stage 3 — Topping: Close > MA and slope ≤ 0.
- Stage 4 — Declining: Close ≤ MA and slope ≤ 0.
- Stage 1 — Basing: Close ≤ MA and slope > 0.

Stage is categorical; never treat stage numbers as arithmetic quantities.

## 6. 52-calendar-week high

- Use the preceding 52 calendar weeks ending at T.
- Minimum 200 valid sessions.
- `High_52W = max(adjusted High)` in the window.
- `Near_52W_High = Close_T >= 0.97 × High_52W`.

## 7. Volume

Prior-50-session baseline:

`Volume_MA50 = rolling(50, min_periods=50).mean().shift(1)`.

`Volume_Ratio = Volume_T / Volume_MA50`.

The latest completed session is the numerator; its volume is excluded from the baseline.

## 8. Up/Down volume

For each completed session:

- Close up → volume is Up Volume.
- Close down → volume is Down Volume.
- Unchanged → neither.

Use the 20 completed sessions ending at T, including T.

`U_D = UpVol20 / DownVol20`.

No arbitrary denominator offset is permitted. Zero-denominator handling remains explicit.

Interpretation:

- >1.5: Strong Accumulation.
- >1.3 to 1.5: Accumulating.
- 0.7 to 1.3: Neutral.
- <0.7: Distribution Warning.
- <0.6: Heavy Distribution.

## 8.1 Data integrity

- Calendar periods remain calendar based.
- The information boundary is global.
- Forward filling/interpolation requires explicit justification.
- Missing history produces explicit insufficiency.
- Optimizations require numerical regression testing against an independent/reference calculation.
- No performance improvement is a valid reason to change a locked mathematical definition.

## 9. Breakout

`Breakout` remains separate from `Breakout_Confirmed`.

Breakout setup:

- Stage 2.
- Close within 3% of 52W High.
- Volume Ratio >1.5×.

Confirmed breakout:

- Breakout setup.
- U/D >1.3.

The two states must never be collapsed.

## 9.1 Published snapshot fields — NEW v2.1

The audit publishes, in addition to the fields above:

- `Close` — the adjusted close of the latest completed session T. Every
  price-derived presentation value traces to this single observation.
- `Ext_Pct` = `(Close / MA_30W - 1) × 100`. This is the **displayed** extension.
  The locked `Extended_20Pct` condition keeps its specified form
  `Close > 1.20 × MA_30W` and is **not** re-derived from `Ext_Pct`: the two are
  algebraically equal but not bit-identical in floating point, and the
  comparison in section 10.1 remains the authority.
- `Pct_From_52W_High` = `(Close / High_52W - 1) × 100`.
- `Above_MA_30W`, `Above_MA_10W`, `MA10W_Above_MA30W`, `MA_30W_Rising` — strict
  comparisons between locked fields.
- `Trend_Health` — an integer 0–5, the count of the five conditions in
  section 9.3. It is a display aggregate; no locked signal consumes it.

## 9.2 The 10-calendar-week MA — NEW v2.1

`MA_10W` is a simple average over **every valid NSE session in a 10-calendar-week
window** ending at T, constructed exactly as the 30-week MA in section 5. It is
not a fixed 50-row trading-day average.

The alternative interpretation — reusing the 50-session `SMA_50` already
computed for the guide's below-50DMA condition — was considered and rejected:
placing a trading-day average beside a calendar-week average would make the two
trend lines non-comparable. `SMA_50` remains, unchanged, for its own condition
in section 10.2.

`MA_10W` is a trend reference and a checklist input only:

- it does **not** reclassify Stage;
- no locked signal, breakout condition or Action rule depends on it;
- the Stage definition in section 5 is unchanged.

## 9.3 Trend health — NEW v2.1

`Trend_Health` counts these five conditions, all locked fields or strict
comparisons between them:

1. `Close > MA_30W`
2. `MA_30W_Slope_10S_Pct > 0`
3. `MA_10W > MA_30W`
4. `Close > MA_10W`
5. `RS_Score >= 50` (the locked "not lagging" band from section 4)

## 9.4 52-week low — NEW v2.1

`Low_52W` is the minimum adjusted Low over the preceding 52 calendar weeks
ending at T, requiring at least 200 valid sessions — the same window and the
same guard as `High_52W` in section 6. It is a presentation/range input; no
locked signal consumes it. When the provider frame carries no `Low` column the
field is explicit insufficiency (NaN) and is never substituted with `Close`.

## 10. New guide-derived timing fields

### 10.1 Extension

The guide's **extended >20%** condition is operationalized as:

`Extended_20Pct = Close > 1.20 × MA_30W`.

This is a timing warning, not a Stage reclassification.

### 10.2 50DMA

The guide's **below 50DMA** condition is operationalized as the 50 completed-session simple moving average of Close:

`SMA50(T) = mean(Close over the latest 50 completed sessions)`.

`Below_50DMA = Close_T < SMA50(T)`.

This is a timing warning, not a Stage reclassification.

## 10.3 Pullback / volume drying

The guide references pullback + volume drying as a buy-timing condition but does not supply a sufficiently precise quantitative definition in the repository adaptation. RS-Stages therefore does **not** fabricate a detector for this condition. It remains an explicit future specification item.

## 11. Production Action framework — NEW v2

The production Action vocabulary is now:

`BUY★`, `BUY`, `HOLD`, `WAIT`, `WATCH★`, `WATCH`, `REDUCE`, `SELL`, `AVOID`.

### Stage 4

**Always SELL**, regardless of RS.

### Stage 3

- RS <50 → SELL.
- RS ≥50 → REDUCE.

### Stage 1

- RS ≥80 → WATCH★.
- RS 50–79 → WATCH.
- RS <50 → AVOID.

### Stage 2 — RS ≥80

- Distribution (`U_D <0.7`) → REDUCE.
- Extended >20% → WAIT.
- Below 50DMA → WAIT.
- Confirmed breakout → BUY★.
- Breakout without confirmation → BUY.
- Otherwise → HOLD.

### Stage 2 — RS 50–79

- Distribution → REDUCE.
- Breakout/pullback without leadership → WAIT.
- Otherwise accumulating/holding → HOLD.

### Stage 2 — RS <50

**WAIT.**

The complete deterministic mapping is documented separately in `docs/ACTION_SPEC.md` and implemented in `rs_stages/actions.py`.

## 12. Action transparency

Every Action shown to a user must expose:

- Action.
- Stage.
- RS score and RS band.
- 30W MA and slope.
- 52W High and proximity.
- Volume Ratio.
- U/D and distribution state.
- Breakout and Breakout Confirmed.
- 50DMA state.
- Extension state.
- Exact reason for the Action.
- Source/design attribution.

The Action is never permitted to hide the underlying mathematics.

## 12.1 Published artifacts — NEW v2.1

The audit downloads market data once and runs the identical pipeline at two
decision dates, publishing:

| Artifact | Contents |
| --- | --- |
| `data/latest_research.csv` | The snapshot at decision date D (latest completed session T). |
| `data/previous_research.csv` | The same pipeline with the boundary moved back one completed session (latest completed T-1). |
| `price_panel.npz` | A dense sessions x symbols grid of `Close` (float32) for the trailing 420 sessions, plus the session calendar and symbol list. **Published as a rolling release asset, never committed.** |
| `data/breadth_history.csv` | Point-in-time participation counts for the trailing 120 sessions. |

Constraints:

- Both snapshots must come from the same pipeline version. Diffing against a
  snapshot produced before a field existed would report the field's *arrival* as
  a market change, so any field missing from either side is skipped entirely.
- The price panel stores `Close` only. The moving averages are deliberately
  **not** stored: the presentation layer recomputes them for the single symbol
  it draws, using the same locked functions, so a drawn line cannot drift from
  the definition it claims to show.
- The breadth history is a stack of point-in-time counts. Each session's count
  uses only moving averages evaluated at that session, so the series carries no
  look-ahead. Symbols without a valid average at a session are excluded from
  both that session's numerator and its denominator.
- The panel is **never committed**. It is a regenerated binary that changes
  completely each run, so Git cannot delta it: measured cost is 1.43 MB of
  permanent history per run if committed, against 0 MB as a replaced release
  asset. It is published to the rolling `data-latest` release tag, whose single
  asset is overwritten every run.
- The panel is stored as a compressed NumPy grid rather than Parquet. Every
  symbol shares the same completed-session calendar, so a dense matrix is both
  smaller (measured 0.88 MB against 1.39 MB) and readable with NumPy alone. The
  presentation layer therefore requires no Arrow runtime to draw a chart.
- Because the panel and the committed snapshot are published to different
  places, they can drift. The audit refuses to publish a panel whose terminal
  session disagrees with the snapshot's decision date, and the presentation
  layer withholds a mismatched panel rather than drawing it. A chart and a table
  must never describe different sessions.
- The panel is loaded lazily and held by reference, never serialised into the
  snapshot cache. Only the two views that draw price history load it, so a
  failure to read it degrades those two rather than the whole terminal.

## 13. Liquidity

Liquidity remains a UI/screener filter only:

`AvgValue20 = mean(Close × raw Volume over latest 20 completed sessions)`.

Liquid when `AvgValue20 > ₹5 crore`.

RS ranking is never recomputed after applying this filter.

## 14. UI specification — NEW v2

The platform is a **quantitative research product**, not a plain Streamlit form.

Required information architecture:

1. **Dashboard** — market snapshot, stage breadth, action distribution, strongest setups, recent movers.
2. **Screener** — dense sortable table with Action as the final decision column, filters for Stage/Action/RS/Industry/Liquidity, search, and clear evidence fields.
3. **Industries** — industry leadership, breadth and action concentration.
4. **Movers** — strongest RS changes and stage/action transitions where data supports them.
5. **Stock** — professional individual-stock research page with TradingView Lightweight Charts, 30W MA overlay, decision evidence and Action card.
6. **Methodology** — plain-language formulas, source attribution, information boundary and Action rules.

Visual direction:

- White/light neutral canvas.
- Strong typography hierarchy.
- Subtle green/blue/amber/red accents with semantic meaning.
- Compact professional tables.
- No oversized meaningless numeric cards.
- Numbers must be formatted for human reading: RS as integer, percentages as percentages, volume ratio with ×, U/D to sensible precision, INR with Cr/L notation.
- Mobile-first responsive behavior.
- TradingView Lightweight Charts is a charting library/component only; it is not the source of quantitative calculations.

## 15. Superseded v1 behaviour

The following early design decisions are retired:

- Five-label Action system (`BUY/HOLD/WAIT/REDUCE/SELL`).
- RS ≥85 BUY threshold.
- RS ≥70 HOLD threshold.
- Action logic embedded directly inside `app.py`.
- UI that presents raw decimal returns/values without human formatting.
- UI whose Action explanation is less detailed than the underlying evidence.

The quantitative RS/Stage definitions remain unchanged unless explicitly modified above.

## 16. v2.1 change summary

Additive only. No v2.0 definition was altered:

- Added `MA_10W`, `Low_52W`, `Close`, `Ext_Pct`, `Pct_From_52W_High`,
  `Trend_Health` and the trend-health booleans to the published snapshot.
- Generalised the calendar-window moving average into a single shared
  definition. `ma_30w` and `ma_30w_series` now delegate to it and are proven
  bit-identical to the previous implementation, including on gapped history.
- Added the previous-session snapshot, the price panel and the breadth history
  as published artifacts.
- Extended the independent reconciliation in the audit to the 10-week MA, the
  52-week low and the price panel.

RS, Stage, the 52-week high, volume ratio, U/D, breakout, confirmation, the
timing warnings, liquidity and the nine-label Action framework are byte-for-byte
unchanged.
