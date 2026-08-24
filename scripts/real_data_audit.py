"""Run a reproducible real-data RS/Stage audit from the locked NSE universe."""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from rs_stages.pipeline import acquire_and_build_universe_snapshots
from rs_stages.screener import analyze_universe
from rs_stages.quant import rs_blend, rs_returns


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", required=True)
    ap.add_argument("--decision-date", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    decision = pd.Timestamp(args.decision_date)
    universe = pd.read_csv(args.universe)
    snapshots = acquire_and_build_universe_snapshots(
        args.universe, args.start, args.end, decision
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

    print(f"Universe rows: {len(universe)}")
    print(f"Research rows: {len(result)}")
    print(f"RS reconciliation failures: {len(failures)}")
    print(f"Stage counts:\n{result['Stage'].value_counts(dropna=False).to_string()}")
    print(f"Sufficient RS rows: {result['RS_Blend'].notna().sum()}")
    print(f"Sufficient 52W rows: {result['High_52W'].notna().sum()}")
    print(f"Sufficient liquidity rows: {result['AvgValue20'].notna().sum()}")


if __name__ == "__main__":
    main()
