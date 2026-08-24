# RS-Stages — Data Specification

**Authority:** `docs/LOCKED_SPEC.md` + approved project decisions

## Universe

- Symbols come from the NSE constituent CSV used by RS-Stages.
- Use the CSV's `Industry` field exactly.
- No F&O filtering.
- Do not silently remap symbols or industries.
- NSE CSV symbols are preserved exactly in the universe; `.NS` is added only when mapping an NSE symbol to Yahoo Finance.

## Market Data

Use yfinance for market history with `auto_adjust=True`.

- Close: adjusted Close
- High: adjusted High
- Volume: raw share Volume
- Open/Low are not required for core calculations.
- The acquisition layer does not silently forward-fill or interpolate market data.

## Decision Boundary

The system makes decisions before the upcoming NSE session opens.

For decision session `D`, only data through the latest completed session `T` is permitted. `T` is the latest available session **strictly before D**. If a provider already contains D because its market data was downloaded after the close, D is still excluded from the pre-market snapshot.

The production boundary is implemented by `build_decision_snapshot()` in `rs_stages/data.py` and must run before quantitative signal calculations.

## Integration Boundary

`build_universe_snapshots()` in `rs_stages/pipeline.py` is the deterministic integration boundary between the NSE universe and market histories.

`acquire_universe_histories()` now connects that universe directly to the yfinance acquisition function. `acquire_and_build_universe_snapshots()` then passes the complete acquired set through the pre-market boundary.

The production sequence is:

**NSE CSV → yfinance symbol mapping → yfinance history → market-data validation → pre-market snapshot → quantitative calculations**

The acquisition layer fails closed: if any NSE universe symbol cannot be acquired, the complete acquisition raises an error rather than silently producing a partial universe.

## Calendar Windows

All specified lookbacks are calendar-date based unless explicitly defined as session-based:

- RS: 3/6/9/12 calendar months
- Stage MA: 30 calendar weeks
- 52W high: 52 calendar weeks

If a calendar reference date is not an NSE session, use the last available NSE session on or before that date.

A calendar window is determined by dates, not by an arbitrary fixed number of rows.

## History

Download sufficient calendar history to cover the longest required calendar lookback plus all session-based warm-up requirements. Fixed row counts may be implementation buffers only and must not replace the mathematical definitions.

## Data Integrity

Audit missing observations, duplicates, timestamps, market holidays, stale values, corporate actions, symbol changes, delisted securities, volume anomalies, inconsistent frequencies, and calendar mismatches.

Duplicate sessions are rejected. Timestamps are normalized to session dates only after duplicate validation. Insufficient history remains explicitly insufficient.

## NSE CSV Ingestion

`load_nse_constituents_csv()` requires `Symbol` and `Industry`, rejects missing values and duplicate symbols, and returns the supplied universe without filtering F&O or rewriting industries.

## Yahoo Finance Acquisition

`yfinance_symbol()` maps an NSE CSV symbol to `<SYMBOL>.NS` for Yahoo Finance only. `download_yfinance_history()` uses `auto_adjust=True`, disables actions, rejects empty results, normalizes the session index, and requires `Close`, `High`, and `Volume`.

When yfinance returns a one-symbol MultiIndex, the acquisition layer removes only the symbol level. It does not transform OHLCV values.

`auto_adjust=True` is the locked price policy: returned `Close` and `High` are consumed as adjusted price fields. `Volume` is preserved as the provider's raw share-volume field. The tests explicitly verify that the acquisition function does not numerically alter these three fields.

Acquisition and decision-boundary enforcement are separate: downloaded data must pass through `build_decision_snapshot()` before any signal calculation.

## Validation

The data/integration layer is tested independently for:

1. Calendar reference-date resolution.
2. Latest-completed-session selection.
3. Strict pre-market exclusion of the upcoming session even when provider data contains it.
4. Missing/duplicate observations.
5. Holiday and non-trading-day handling.
6. Minimum-history requirements.
7. Adjusted-price versus raw-volume handling.
8. Universe/Industry ingestion from the NSE CSV.
9. Yahoo symbol mapping without changing the underlying NSE universe.
10. Required market-column validation.
11. yfinance acquisition parameters (`auto_adjust=True`, actions disabled, progress disabled).
12. yfinance one-symbol MultiIndex normalization.
13. Preservation of Close/High/Volume values through acquisition.
14. Complete NSE-universe-to-snapshot integration.
15. Rejection when any universe symbol has no supplied market history.
16. Fail-closed behaviour when any universe symbol's provider acquisition fails.
