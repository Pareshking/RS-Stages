# RS-Stages — Data Specification

**Authority:** `docs/LOCKED_SPEC.md` + approved project decisions

## Universe

- Symbols come from the NSE constituent CSV used by RS-Stages.
- Use the CSV's `Industry` field exactly.
- No F&O filtering.
- Do not silently remap symbols or industries.

## Market Data

Use yfinance for market history with `auto_adjust=True`.

- Close: adjusted Close
- High: adjusted High
- Volume: raw share Volume
- Open/Low are not required for core calculations.

## Decision Boundary

The system makes decisions before the upcoming NSE session opens.

For decision session `D`, only data through the latest completed session `T` is permitted. The upcoming/incomplete session must never enter any signal calculation.

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

Do not forward-fill or interpolate market data unless an explicitly documented methodology requires it.

Insufficient history must remain explicitly insufficient; do not fabricate values.

## Validation

The data layer must be tested independently for:

1. Calendar reference-date resolution.
2. Latest-completed-session selection.
3. Pre-market exclusion of the upcoming session.
4. Missing/duplicate observations.
5. Holiday and non-trading-day handling.
6. Minimum-history requirements.
7. Adjusted-price versus raw-volume handling.
8. Universe/Industry ingestion from the NSE CSV.
