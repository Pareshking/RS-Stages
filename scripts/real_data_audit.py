"""Run a reproducible real-data RS/Stage audit from the locked NSE universe."""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from rs_stages.pipeline import acquire_and_build_universe_snapshots
from rs_stages.screener import analyze_universe
from rs_stages.quant import rs_blend, rs_returns, classify_stage, calendar_asof
from rs_stages.data import load_nse_constituents_csv


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
    stage = classify_stage(float(s.loc[t]), ma, slope)
    return ma, slope, stage


def independent_high52(high: pd.Series, decision: pd.Timestamp) -> float:
    s = high.sort_index().dropna()
    t = independent_calendar_asof(s.index, decision)
    start = independent_calendar_asof(s.index, t - pd.Timedelta(weeks=52))
    window = s.loc[(s.index >= start) & (s.index <= t)]
    if len(window) < 200:
        raise ValueError("Insufficient history for independent 52W high")
    return float(window.max())


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
    snapshots = acquire_and_build_universe_snapshots(args.universe, start, end, decision).snapshots
    result = analyze_universe(snapshots)

    failures = []
    checked_stage = checked_high = checked_volume = checked_ud = checked_liquidity = 0
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
            if not np.isclose(rs_blend(expected), rs_blend(actual), rtol=0, atol=1e-12):
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

    result = result.join(universe.set_index("Symbol"), how="left", rsuffix="_NSE")
    result.to_csv(args.output)

    if failures:
        raise SystemExit("Independent research-output reconciliation failures:\n" + "\n".join(failures[:100]))

    print(f"Decision date: {decision.date()}")
    print(f"Yahoo history: {start.date()} to {end.date()} exclusive")
    print(f"Universe rows after DUMMY exclusion: {len(universe)}")
    print(f"Research rows: {len(result)}")
    print(f"RS reconciliation failures: {len(failures)}")
    print(f"Independent checks: stage={checked_stage}, high52={checked_high}, volume={checked_volume}, ud={checked_ud}, liquidity={checked_liquidity}")
    print(f"Stage counts:\n{result['Stage'].value_counts(dropna=False).to_string()}")
    print(f"Sufficient RS rows: {result['RS_Blend'].notna().sum()}")
    print(f"Sufficient 52W rows: {result['High_52W'].notna().sum()}")
    print(f"Sufficient liquidity rows: {result['AvgValue20'].notna().sum()}")


if __name__ == "__main__":
    main()
