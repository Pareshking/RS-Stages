"""Run a reproducible real-data RS/Stage audit from the locked NSE universe."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from rs_stages.actions import with_actions
from rs_stages.market import breadth_history_from_trends
from rs_stages.pipeline import acquire_universe_histories
from rs_stages.screener import analyze_universe, analyze_universe_with_trend
from rs_stages.quant import rs_blend, rs_returns, calendar_asof
from rs_stages.data import (
    INDEX_TICKERS,
    build_decision_snapshot,
    download_index_history,
    load_nse_constituents_csv,
)

#: Sessions of Close retained per symbol so the UI can draw price history and
#: recompute the locked moving averages for a single symbol without a download.
PANEL_SESSIONS = 420

#: Sessions of universe-wide participation retained for the breadth trend.
BREADTH_SESSIONS = 250

#: Benchmark plotted beside market breadth. It is reference data only: no RS
#: ranking, Stage classification or Action rule reads it. Note that it tracks
#: 500 companies while our breadth tracks the Nifty Total Market universe, so a
#: divergence between the two lines can be composition, not market behaviour.
BENCHMARK_KEY = "NIFTY_500"


def independent_calendar_asof(index: pd.DatetimeIndex, target: pd.Timestamp) -> pd.Timestamp:
    idx = pd.DatetimeIndex(index).sort_values().unique()
    pos = idx.searchsorted(pd.Timestamp(target), side="right") - 1
    if pos < 0:
        raise ValueError("No completed session exists on or before target date")
    return idx[pos]


def independent_rs(close: pd.Series, decision: pd.Timestamp) -> dict[int, float]:
    s = close.sort_index().dropna()
    t = independent_calendar_asof(s.index, decision)
    latest = float(s.loc[t])
    out = {}
    for m in (3, 6, 9, 12):
        ref = independent_calendar_asof(s.index, t - pd.DateOffset(months=m))
        out[m] = latest / float(s.loc[ref]) - 1.0
    return out


def independent_stage(close: pd.Series, decision: pd.Timestamp) -> tuple[float, float, str]:
    """Independently reproduce 30W MA, 10-session slope and Stage truth table."""
    s = close.sort_index().dropna()
    t = independent_calendar_asof(s.index, decision)
    start_ref = independent_calendar_asof(s.index, t - pd.Timedelta(weeks=30))
    window = s.loc[(s.index >= start_ref) & (s.index <= t)]
    if len(window) < 2:
        raise ValueError("Insufficient history for independent 30W MA")
    ma = float(window.mean())

    ma_values = []
    for point in s.index:
        try:
            point_t = independent_calendar_asof(s.index, point)
            point_start = independent_calendar_asof(s.index, point_t - pd.Timedelta(weeks=30))
            point_window = s.loc[(s.index >= point_start) & (s.index <= point_t)]
            if len(point_window) < 2:
                continue
            ma_values.append((point_t, float(point_window.mean())))
        except ValueError:
            continue
    ma_series = pd.Series(dict(ma_values)).sort_index().dropna()
    pos = ma_series.index.searchsorted(t, side="right") - 1
    if pos < 10:
        raise ValueError("Insufficient history for independent MA slope")
    prior = float(ma_series.iloc[pos - 10])
    if prior == 0:
        raise ValueError("Cannot calculate independent slope from zero prior MA")
    slope = (float(ma_series.iloc[pos]) / prior - 1.0) * 100.0

    # Independent truth table: do not call production classify_stage().
    above = float(s.loc[t]) > ma
    rising = slope > 0.0
    if above and rising:
        stage = "Stage 2 — Advancing"
    elif above and not rising:
        stage = "Stage 3 — Topping"
    elif not above and not rising:
        stage = "Stage 4 — Declining"
    else:
        stage = "Stage 1 — Basing"
    return ma, slope, stage


def independent_high52(high: pd.Series, decision: pd.Timestamp) -> float:
    s = high.sort_index().dropna()
    t = independent_calendar_asof(s.index, decision)
    start = independent_calendar_asof(s.index, t - pd.Timedelta(weeks=52))
    window = s.loc[(s.index >= start) & (s.index <= t)]
    if len(window) < 200:
        raise ValueError("Insufficient history for independent 52W high")
    return float(window.max())


def independent_ma_10w(close: pd.Series, decision: pd.Timestamp) -> float:
    """Independent 10-calendar-week mean, written without the quant helpers."""
    s = close.sort_index().dropna()
    t = independent_calendar_asof(s.index, decision)
    start = independent_calendar_asof(s.index, t - pd.Timedelta(weeks=10))
    window = s.loc[(s.index >= start) & (s.index <= t)]
    if len(window) < 2:
        raise ValueError("Insufficient history for independent 10W MA")
    return float(window.mean())


def independent_low52(low: pd.Series, decision: pd.Timestamp) -> float:
    s = low.sort_index().dropna()
    t = independent_calendar_asof(s.index, decision)
    start = independent_calendar_asof(s.index, t - pd.Timedelta(weeks=52))
    window = s.loc[(s.index >= start) & (s.index <= t)]
    if len(window) < 200:
        raise ValueError("Insufficient history for independent 52W low")
    return float(window.min())


def independent_volume_ratio(volume: pd.Series, decision: pd.Timestamp) -> float:
    s = volume.sort_index().astype(float)
    pos = s.index.searchsorted(pd.Timestamp(decision), side="right") - 1
    if pos < 50:
        raise ValueError("Insufficient history for independent volume ratio")
    baseline = float(s.iloc[pos - 50:pos].mean())
    latest = float(s.iloc[pos])
    if baseline == 0:
        return np.inf if latest > 0 else np.nan
    return latest / baseline


def independent_ud(close: pd.Series, volume: pd.Series, decision: pd.Timestamp) -> float:
    c, v = close.sort_index().align(volume.sort_index(), join="inner")
    pos = c.index.searchsorted(pd.Timestamp(decision), side="right") - 1
    if pos < 20:
        raise ValueError("Insufficient history for independent U/D")
    delta = c.diff()
    up_sum = float(v.where(delta > 0, 0.0).iloc[pos - 19:pos + 1].sum())
    down_sum = float(v.where(delta < 0, 0.0).iloc[pos - 19:pos + 1].sum())
    if down_sum == 0:
        return np.inf if up_sum > 0 else np.nan
    return up_sum / down_sum


def resolve_dates(decision_arg: str | None, start_arg: str | None, end_arg: str | None) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    now_ist = pd.Timestamp.now(tz="Asia/Kolkata")
    decision = pd.Timestamp(decision_arg) if decision_arg else now_ist.tz_localize(None).normalize()
    start = pd.Timestamp(start_arg) if start_arg else decision - pd.Timedelta(days=500)
    end = pd.Timestamp(end_arg) if end_arg else decision + pd.Timedelta(days=1)
    if start >= end:
        raise ValueError("Audit start date must be before end date")
    return decision, start, end


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", required=True)
    ap.add_argument("--decision-date")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    decision, start, end = resolve_dates(args.decision_date, args.start, args.end)
    universe = load_nse_constituents_csv(args.universe)
    if universe["Symbol"].str.startswith("DUMMY", na=False).any():
        raise SystemExit("DUMMY symbols must never enter the analytical universe")

    # Market data is acquired once. Both decision dates are then derived from
    # the same download, so the previous-session snapshot cannot disagree with
    # the current one because of a provider revision between two calls.
    histories = acquire_universe_histories(args.universe, start, end)
    snapshots = {
        str(symbol): build_decision_snapshot(histories[str(symbol)], decision)
        for symbol in universe["Symbol"]
    }

    # The previous snapshot re-runs the identical pipeline with the information
    # boundary moved back one completed session. It is not a stored copy of an
    # earlier run, so both sides always come from the same pipeline version.
    previous_snapshots = {}
    for symbol, snap in snapshots.items():
        try:
            previous_snapshots[symbol] = build_decision_snapshot(
                histories[symbol], snap.latest_completed_session
            )
        except ValueError:
            continue

    result, trends = analyze_universe_with_trend(snapshots, trend_sessions=PANEL_SESSIONS)
    previous_result = analyze_universe(previous_snapshots) if previous_snapshots else pd.DataFrame()

    failures = []
    checked_stage = checked_high = checked_volume = checked_ud = checked_liquidity = 0
    checked_ma_10w = checked_low = checked_trend = 0
    for symbol, snap in snapshots.items():
        close = snap.data["Close"].astype(float)
        high = snap.data["High"].astype(float)
        volume = snap.data["Volume"].astype(float)
        t = snap.latest_completed_session
        try:
            expected = independent_rs(close, t)
            actual = rs_returns(close, t)
            for m in (3, 6, 9, 12):
                if not np.isclose(expected[m], actual[m], rtol=0, atol=1e-12):
                    failures.append(f"{symbol}: R{m}M mismatch")
            expected_blend = 0.40 * expected[3] + 0.20 * expected[6] + 0.20 * expected[9] + 0.20 * expected[12]
            if not np.isclose(expected_blend, float(result.loc[symbol, "RS_Blend"]), rtol=0, atol=1e-12):
                failures.append(f"{symbol}: RS blend mismatch")
        except ValueError:
            pass

        try:
            ma, slope, stage = independent_stage(close, t)
            checked_stage += 1
            row = result.loc[symbol]
            if not np.isclose(row["MA_30W"], ma, rtol=0, atol=1e-12): failures.append(f"{symbol}: 30W MA mismatch")
            if not np.isclose(row["MA_30W_Slope_10S_Pct"], slope, rtol=0, atol=1e-12): failures.append(f"{symbol}: MA slope mismatch")
            if row["Stage"] != stage: failures.append(f"{symbol}: Stage mismatch")
        except ValueError:
            pass

        try:
            expected = independent_high52(high, t)
            checked_high += 1
            if not np.isclose(result.loc[symbol, "High_52W"], expected, rtol=0, atol=1e-12): failures.append(f"{symbol}: 52W high mismatch")
        except ValueError:
            pass

        try:
            expected = independent_ma_10w(close, t)
            checked_ma_10w += 1
            if not np.isclose(result.loc[symbol, "MA_10W"], expected, rtol=0, atol=1e-12):
                failures.append(f"{symbol}: 10W MA mismatch")
        except ValueError:
            pass

        if "Low" in snap.data.columns:
            try:
                expected = independent_low52(snap.data["Low"].astype(float), t)
                checked_low += 1
                if not np.isclose(result.loc[symbol, "Low_52W"], expected, rtol=0, atol=1e-12):
                    failures.append(f"{symbol}: 52W low mismatch")
            except ValueError:
                pass

        try:
            expected = independent_volume_ratio(volume, t)
            checked_volume += 1
            if not np.isclose(result.loc[symbol, "Volume_Ratio"], expected, rtol=0, atol=1e-12): failures.append(f"{symbol}: volume ratio mismatch")
        except ValueError:
            pass

        try:
            expected = independent_ud(close, volume, t)
            checked_ud += 1
            if not np.isclose(result.loc[symbol, "U_D"], expected, rtol=0, atol=1e-12, equal_nan=True): failures.append(f"{symbol}: U/D mismatch")
        except ValueError:
            pass

        value = (close * volume).loc[:t].dropna()
        if len(value) >= 20:
            checked_liquidity += 1
            expected = float(value.iloc[-20:].mean())
            if not np.isclose(result.loc[symbol, "AvgValue20"], expected, rtol=0, atol=1e-12): failures.append(f"{symbol}: liquidity mismatch")
        elif not pd.isna(result.loc[symbol, "AvgValue20"]):
            failures.append(f"{symbol}: liquidity should be NaN")

    # The stored trend panel must agree with the row it belongs to. A panel that
    # disagreed with the snapshot would let the chart and the table tell two
    # different stories about the same session.
    for symbol, frame in trends.items():
        if frame.empty or symbol not in result.index:
            continue
        checked_trend += 1
        row = result.loc[symbol]
        last = frame.index.max()
        if last != row["Date"]:
            failures.append(f"{symbol}: trend panel ends at {last}, snapshot at {row['Date']}")
            continue
        if pd.notna(row["Close"]) and not np.isclose(
            float(frame["Close"].loc[last]), float(row["Close"]), rtol=0, atol=1e-12
        ):
            failures.append(f"{symbol}: trend panel Close disagrees with snapshot Close")
        for column in ("MA_10W", "MA_30W"):
            stored, reported = float(frame[column].loc[last]), row[column]
            if pd.notna(reported) and not np.isclose(stored, float(reported), rtol=0, atol=1e-12):
                failures.append(f"{symbol}: trend panel {column} disagrees with snapshot")

    result = result.join(universe.set_index("Symbol"), how="left", rsuffix="_NSE")
    result = with_actions(result)
    result.to_csv(args.output)

    output_dir = Path(args.output).resolve().parent

    # Previous-session snapshot: same columns, boundary moved back one session.
    previous_path = output_dir / "previous_research.csv"
    if not previous_result.empty:
        previous_result = previous_result.join(universe.set_index("Symbol"), how="left", rsuffix="_NSE")
        previous_result = with_actions(previous_result)
        previous_result.to_csv(previous_path)

    # Price panel: Close only. The moving averages are deliberately not stored —
    # the UI recomputes them for the one symbol it draws using the same locked
    # functions, so a chart line can never drift from the locked definition.
    #
    # Stored as a compressed NumPy grid rather than Parquet. Every symbol shares
    # the same completed-session calendar, so the panel is a dense
    # sessions x symbols matrix; that is smaller than Parquet (measured 0.88 MB
    # against 1.39 MB) and, more importantly, it is read with NumPy alone. The
    # presentation layer therefore needs no Arrow runtime to draw a chart.
    #
    # It is published as a release asset rather than committed: it is a
    # regenerated binary that changes completely every run, so Git cannot delta
    # it and would store a fresh blob per run, permanently. Measured history
    # cost: 1.43 MB/run committed against 0 MB/run as a replaced asset.
    panel_path = output_dir / "price_panel.npz"
    frames = {symbol: frame for symbol, frame in trends.items() if not frame.empty}
    symbols = sorted(frames)
    sessions = np.array(sorted({stamp for f in frames.values() for stamp in f.index}))

    closes = np.full((len(sessions), len(symbols)), np.nan, dtype="float32")
    position = {stamp: i for i, stamp in enumerate(sessions)}
    for column, symbol in enumerate(symbols):
        frame = frames[symbol]
        rows = np.fromiter((position[stamp] for stamp in frame.index), dtype=np.intp, count=len(frame))
        closes[rows, column] = frame["Close"].to_numpy(dtype="float32")

    np.savez_compressed(
        panel_path,
        close=closes,
        symbols=np.array(symbols, dtype="U32"),
        dates=pd.DatetimeIndex(sessions).to_numpy().astype("datetime64[D]"),
    )

    # The panel and the committed snapshot are published to different places, so
    # they could drift. Refuse to publish a panel whose terminal session
    # disagrees with the snapshot's decision date: a chart and a table must
    # never describe different sessions.
    panel_end = pd.Timestamp(sessions[-1]) if len(sessions) else pd.NaT
    snapshot_end = pd.Timestamp(pd.to_datetime(result["Date"]).max())
    if pd.isna(panel_end) or panel_end.normalize() != snapshot_end.normalize():
        failures.append(
            f"price panel ends at {panel_end} but the snapshot decision date is {snapshot_end}"
        )

    # Breadth history: point-in-time participation counts, one row per session.
    breadth_path = output_dir / "breadth_history.csv"
    breadth = breadth_history_from_trends(trends, sessions=BREADTH_SESSIONS)

    # Benchmark index, aligned onto the breadth session calendar. A failure to
    # fetch it must not fail the audit: breadth is ours and computed, the index
    # is an external convenience, so the column is simply absent and the chart
    # says so.
    if not breadth.empty:
        ticker = INDEX_TICKERS[BENCHMARK_KEY]
        try:
            index_history = download_index_history(
                ticker,
                start=pd.Timestamp(breadth["Date"].min()),
                end=pd.Timestamp(breadth["Date"].max()) + pd.Timedelta(days=1),
            )
            closes = index_history["Close"].astype(float)
            aligned = closes.reindex(pd.DatetimeIndex(breadth["Date"]))
            breadth["Benchmark_Close"] = aligned.to_numpy()
            breadth["Benchmark_Ticker"] = ticker
            covered = int(breadth["Benchmark_Close"].notna().sum())
            print(f"Benchmark {ticker}: {covered} of {len(breadth)} sessions aligned")
        except (ImportError, ValueError, KeyError, OSError) as exc:
            print(f"Benchmark {ticker} unavailable ({type(exc).__name__}); breadth published without it")

        breadth.to_csv(breadth_path, index=False)

    if failures:
        raise SystemExit("Independent research-output reconciliation failures:\n" + "\n".join(failures[:100]))

    print(f"Decision date: {decision.date()}")
    print(f"Yahoo history: {start.date()} to {end.date()} exclusive")
    print(f"Universe rows after DUMMY exclusion: {len(universe)}")
    print(f"Research rows: {len(result)}")
    print(f"Independent checks: stage={checked_stage}, high52={checked_high}, volume={checked_volume}, ud={checked_ud}, liquidity={checked_liquidity}")
    print(f"Independent checks (v2.1): ma10w={checked_ma_10w}, low52={checked_low}, trend_panel={checked_trend}")
    print(f"Previous-session rows: {len(previous_result)}")
    print(f"Price panel grid: {closes.shape[0]} sessions x {closes.shape[1]} symbols")
    print(f"Price panel size: {panel_path.stat().st_size / 1e6:.2f} MB (published as a release asset)")
    print(f"Breadth history sessions: {len(breadth)}")
    print(f"Action counts:\n{result['Action'].value_counts().to_string()}")
    print(f"Stage counts:\n{result['Stage'].value_counts(dropna=False).to_string()}")
    print(f"Sufficient RS rows: {result['RS_Blend'].notna().sum()}")
    print(f"Sufficient 52W rows: {result['High_52W'].notna().sum()}")
    print(f"Sufficient liquidity rows: {result['AvgValue20'].notna().sum()}")


if __name__ == "__main__":
    main()
