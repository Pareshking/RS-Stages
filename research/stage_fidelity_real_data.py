"""Real-data pilot comparing locked V1 Stage labels with research candidate.

Research only. Uses the same production 30W-MA and 10-session slope primitives,
so the comparison isolates classification logic rather than indicator math.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from rs_stages.quant import classify_stage, ma_30w, ma_slope_pct
from research.stage_fidelity_experiment import research_stage


def sample_symbols(path: str, sample_size: int) -> list[str]:
    frame = pd.read_csv(path)
    symbol_col = next((c for c in frame.columns if c.strip().lower() == "symbol"), None)
    if symbol_col is None:
        raise ValueError("Universe CSV has no Symbol column")
    symbols = (
        frame[symbol_col]
        .astype(str)
        .str.strip()
        .loc[lambda s: (s != "") & ~s.str.upper().str.startswith("DUMMY")]
        .drop_duplicates()
        .tolist()
    if not symbols:
        raise ValueError("No acquisition symbols remain")
    if len(symbols) <= sample_size:
        return symbols
    positions = np.linspace(0, len(symbols) - 1, sample_size, dtype=int)
    return [symbols[i] for i in positions]


def classify_history(close: pd.Series) -> list[dict]:
    close = close.sort_index().dropna()
    ma = pd.Series({t: ma_30w(close, t) for t in close.index if len(close.loc[:t]) >= 2})
    ma = ma.dropna().sort_index()
    rows: list[dict] = []
    for t in ma.index:
        try:
            slope = ma_slope_pct(ma, t, 10)
        except ValueError:
            continue
        if t not in close.index:
            continue
        v1 = classify_stage(float(close.loc[t]), float(ma.loc[t]), float(slope))
        pos = ma.index.get_loc(t)
        start = max(0, pos - 39)
        recent_idx = ma.index[start : pos + 1]
        recent_close = close.reindex(recent_idx).dropna()
        recent_ma = ma.reindex(recent_close.index).dropna()
        if len(recent_close) < 8 or len(recent_ma) < 8:
            continue
        recent_close = recent_close.reindex(recent_ma.index)
        slope_values = {}
        for candidate_date in recent_ma.index:
            try:
                slope_values[candidate_date] = ma_slope_pct(ma, candidate_date, 10)
            except ValueError:
                continue
        recent_slope = pd.Series(slope_values, dtype=float).sort_index()
        common = recent_close.index.intersection(recent_slope.index)
        if len(common) < 8:
            continue
        candidate = research_stage(
            recent_close.reindex(common),
            recent_ma.reindex(common),
            recent_slope.reindex(common),
        )
        rows.append(
            {
                "date": t,
                "v1": v1,
                "candidate": candidate,
                "close": float(close.loc[t]),
                "ma30w": float(ma.loc[t]),
                "slope_pct": float(slope),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="data/ind_niftytotalmarket_list.csv")
    parser.add_argument("--sample-size", type=int, default=60)
    parser.add_argument("--period", default="3y")
    parser.add_argument("--output", default="stage_fidelity_real_data.csv")
    args = parser.parse_args()

    symbols = sample_symbols(args.universe, args.sample_size)
    tickers = [f"{s}.NS" for s in symbols]
    raw = yf.download(
        tickers,
        period=args.period,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    rows: list[dict] = []
    for symbol, ticker in zip(symbols, tickers):
        try:
            close = raw["Close"] if len(tickers) == 1 else raw[ticker]["Close"]
            close = close.dropna()
            for row in classify_history(close):
                row["symbol"] = symbol
                rows.append(row)
        except Exception as exc:
            rows.append({"symbol": symbol, "error": str(exc)})

    result = pd.DataFrame(rows)
    Path(args.output).write_text(result.to_csv(index=False), encoding="utf-8")
    valid = result.dropna(subset=["v1", "candidate"]) if not result.empty else result
    if len(valid):
        print("Symbols sampled:", len(symbols))
        print("Historical observations:", len(valid))
        print("Agreement rate:", f"{(valid['v1'] == valid['candidate']).mean():.2%}")
        print("V1 distribution:")
        print(valid["v1"].value_counts(normalize=True).sort_index())
        print("Candidate distribution:")
        print(valid["candidate"].value_counts(normalize=True).sort_index())
        print("Confusion matrix:")
        print(pd.crosstab(valid["v1"], valid["candidate"]))
    else:
        print("No valid historical observations produced")


if __name__ == "__main__":
    main()
