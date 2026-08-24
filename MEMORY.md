# RS-Stages — Project Memory / Engineering Operating Specification

## 1. Project Identity

- Repository: `Pareshking/RS-Stages`
- Primary branch: `main`
- Primary technology: Streamlit
- Project scope: development, quantitative research, mathematical validation, testing, auditing, continuous improvement, and professional presentation.

`MEMORY.md` is persistent project memory. Detailed quantitative inputs are authoritative in `docs/LOCKED_SPEC.md`.

## 2. Mandatory Operating Loop

**INSPECT → UNDERSTAND → FORMULATE → IMPLEMENT → TEST → VALIDATE → AUDIT → FIX → RE-TEST → VERIFY → DOCUMENT → REPEAT**

Never stop at code completion or the first green test. Failed tests must be traced to root cause rather than patched symptomatically.

For every meaningful change: identify the mathematical definition, formulate it, compare implementation with the formulation, test edge cases and numerical correctness, independently reproduce important calculations where practical, check leakage/look-ahead, check regression impact, re-run tests, verify outputs, and document evidence.

## 3. Authority

1. `docs/LOCKED_SPEC.md` — authoritative locked production inputs.
2. Supplied book/source material — methodology and intent, subject to explicit project decisions.
3. Explicitly documented implementation assumptions.
4. Conventional practice only when it does not conflict with the above.

Never change a locked definition merely because another implementation performs better.

## 4. Locked Quantitative Inputs

- Universe: symbols supplied by the NSE constituent CSV used by RS-Stages.
- Industry: exactly the CSV `Industry` field.
- No F&O filtering.
- Data: yfinance with `auto_adjust=True`; adjusted Close/High; raw Volume.
- Decisions are made pre-market. For decision session `D`, only information through the latest completed session `T` is permitted. The upcoming/incomplete session can never enter a signal calculation.
- RS lookbacks: 3/6/9/12 **calendar months**; reference price is the last available NSE session on/before each calendar reference date.
- RS blend: 40% / 20% / 20% / 20% for 3M/6M/9M/12M.
- RS score: `rank(Blend, pct=True, method='min') × 98 + 1`, rounded to integer; insufficient-history stocks excluded.
- No skip-month.
- Stage MA: **30-calendar-week Simple Moving Average**, using all valid sessions in the preceding 30 calendar weeks ending at `T`. It is not a fixed 150-row average and not a weighted MA.
- Stage slope: `(MA_30W(T) / MA_30W(T-10 sessions) - 1) × 100`.
- Stage classification: S2 = above MA and rising; S3 = above and not rising; S4 = below and not rising; S1 = below and rising.
- 52W high: preceding **52 calendar weeks** ending at `T`; adjusted High; at least 200 valid sessions required.
- Near-high: `Close_T >= 0.97 × High_52W(T)`.
- Volume baseline: `rolling(50, min_periods=50).mean().shift(1)`; latest completed session's volume is numerator and is excluded from its baseline.
- U/D: classify each completed session by Close change versus previous close; unchanged contributes to neither side. Use 20 completed sessions ending at `T`, including `T`.
- U/D: `UpVol20 / DownVol20`, no arbitrary `+1`. Down=0/up>0 → +infinity; down=0/up=0 → undefined/NaN.
- U/D thresholds: >1.5 Strong Accumulation; >1.3–1.5 Accumulating; 0.7–1.3 Neutral; <0.7 Distribution Warning; <0.6 Heavy Distribution, with boundary precedence explicitly tested.
- Breakout: Stage 2 + within 3% of 52W high + latest completed-session Volume_Ratio >1.5.
- Breakout Confirmed: Breakout + U/D >1.3. Keep the two fields separate.
- Optional liquidity filter: 20-session average `Close×Volume > ₹5 crore`, applied only after calculations and never to redefine the RS ranking universe.
- v1 RS Line: current download window only; no survivorship-free historical-universe claim.

## 5. Quantitative Integrity Rules

Audit formulas, units, scaling, normalization, weights, ranking, rolling windows, calendar boundaries, missing observations, zero/negative values, NaNs, numerical precision, trading-session alignment, signal/execution dates, leakage, survivorship, corporate actions, benchmark alignment, and data transformations.

Calendar definitions must remain calendar definitions. Fixed row counts may be implementation buffers only and may not replace the mathematical period definition.

Missing history must produce explicit insufficiency rather than fabricated values. Forward filling/interpolation requires explicit quantitative justification.

## 6. Validation and Testing Standard

Critical formulas require independent validation using manual calculations, a second implementation, NumPy/Pandas references, synthetic datasets, identities, or controlled fixtures.

Tests must include unit, mathematical, edge-case, integration, regression, and end-to-end coverage. Edge cases include empty/one-row/insufficient history, NaNs, zeros, extremes, duplicate dates, holidays, newly listed/delisted securities, corporate actions, zero down-volume, calendar boundaries, and the pre-market information boundary.

Current pure quantitative code is in `rs_stages/quant.py`; tests are in `tests/test_quant.py`. The repository also has GitHub Actions CI configured to run `pytest -q`. CI execution evidence must be obtained before tests are called passing.

The quantitative layer was tightened to enforce complete calendar windows for 30W MA and 52W high, require ≥200 valid sessions for the 52W high, implement explicit U/D classification, and test latest-session/pre-market boundaries. These are implementation/test changes; they do not alter the locked methodology.

## 7. Current Validation Status

Locked inputs are documented and reconciled. Quantitative primitives and tests exist. CI is configured, but a test suite is **not considered passed until GitHub provides actual execution evidence**.

No production Streamlit/data pipeline milestone should be declared complete until mathematical correctness, independent numerical validation, real-data validation, leakage checks, regression tests, integration behaviour, UI behaviour, output traceability, performance, and documentation have been verified.

## 8. Product Standard

Streamlit UI must be professional, clean, minimalist, light/white, readable, restrained in colour, consistent in typography/spacing, logically tabbed, responsive, and quantitatively transparent. Avoid clutter, excessive colour, heavy borders, decorative elements without purpose, oversized headings, and black-box metrics.

## 9. Working Principle

**Correctness → Evidence → Reproducibility → Robustness → Clarity → Performance → Presentation**

Never say that something is correct merely because it runs or looks plausible. Use **Claim → Evidence → Test → Result → Conclusion** and explicitly state anything that remains unverified.
