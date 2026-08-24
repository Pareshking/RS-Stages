"""Run a reproducible real-data RS/Stage audit from the locked NSE universe."""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from rs_stages.pipeline import acquire_and_build_universe_snapshots
from rs_stages.screener import analyze_universe
from rs_stages.quant import rs_blend, rs_returns
from rs_stages.data import load_nse_constituents_csv


def independent_calendar_asof(index: pd.DatetimeIndex, target: pd.Timestamp) -> pd.Timestamp:
    """Resolve a calendar target independently of the production calendar helper."""
    idx = pd.DatetimeIndex(index).sort_values().unique()
    pos = idx.searchsorted(pd.Timestamp(target), side="right") - 1
    if pos < 0:
        raise ValueError("No completed session exists on or before target date")
    return idx[pos]


def independent_rs(close: pd.Series, decision: pd.Timestamp) -> dict[int, float]:
    """Independent reference implementation for the RS return/blend path."""
    s = close.sort_index().dropna()
    t = independent_calendar_asof(s.index, decision)
    latest = float(s.loc[t])
    out = {}
    for m in (3, 6, 9, 12):
        ref = independent_calendar_asof(s.index, t - pd.DateOffset(months=m))
        out[m] = latest / float(s.loc[ref]) - 1.0
    return out


def resolve_dates(decision_arg: str | None, start_arg: str | None, end_arg: str | None) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """Resolve optional audit dates using the current date in Asia/Kolkata."""
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
    snapshots = acquire_and_build_universe_snapshots(
        args.universe, start, end, decision
    ).snapshots
    result = analyze_universe(snapshots)

    failures = []
    for symbol, snap in snapshots.items():
        try:
            expected = independent_rs(snap.data["Close"], snap.latest_completed_session)
            actual = rs_returns(snap.data["Close"], snap.latest_completed_session)
            for m in (3, 6, 9, 12):
                if not np.isclose(expected[m], actual[m], rtol=0, atol=1e-12):
                    failures.append(f"{symbol}: R{m}M mismatch")
            if not np.isclose(rs_blend(expected), rs_blend(actual), rtol=0, atol=1e-12):
                failures.append(f"{symbol}: RS blend mismatch")
        except ValueError:
            continue

    result = result.join(universe.set_index("Symbol"), how="left", rsuffix="_NSE")
    result.to_csv(args.output)

    if failures:
        raise SystemExit("Independent RS reconciliation failures:\n" + "\n".join(failures[:50]))

    print(f"Decision date: {decision.date()}")
    print(f"Yahoo history: {start.date()} to {end.date()} exclusive")
    print(f"Universe rows after DUMMY exclusion: {len(universe)}")
    print(f"Research rows: {len(result)}")
    print(f"RS reconciliation failures: {len(failures)}")
    print(f"Stage counts:\n{result['Stage'].value_counts(dropna=False).to_string()}")
    print(f"Sufficient RS rows: {result['RS_Blend'].notna().sum()}")
    print(f"Sufficient 52W rows: {result['High_52W'].notna().sum()}")
    print(f"Sufficient liquidity rows: {result['AvgValue20'].notna().sum()}")


if __name__ == "__main__":
    main()
