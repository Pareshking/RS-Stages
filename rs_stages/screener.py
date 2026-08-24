"""Universe-level RS/Stage calculations on validated pre-market snapshots."""
from __future__ import annotations

import pandas as pd

from .data import DecisionSnapshot
from .quant import (
    breakout,
    breakout_confirmed,
    classify_stage,
    high_52w,
    ma_30w,
    ma_30w_series,
    ma_slope_pct,
    rs_blend,
    rs_returns,
    rs_score,
    up_down_ratio,
    volume_ratio,
)


def analyze_universe(snapshots: dict[str, DecisionSnapshot]) -> pd.DataFrame:
    """Calculate locked RS/Stage fields before optional liquidity filtering.

    Symbols with insufficient mathematical history are retained in the output
    with explicit NaNs/False signals rather than fabricated values.
    """
    rows: list[dict] = []
    blends: dict[str, float] = {}

    for symbol, snap in snapshots.items():
        data = snap.data
        close = data["Close"].astype(float)
        high = data["High"].astype(float)
        volume = data["Volume"].astype(float)
        t = snap.latest_completed_session
        row: dict = {"Symbol": symbol, "Date": t}
        try:
            returns = rs_returns(close, t)
            row.update({f"R{m}M": returns[m] for m in returns})
            row["RS_Blend"] = rs_blend(returns)
            blends[symbol] = row["RS_Blend"]
        except (ValueError, KeyError):
            row["RS_Blend"] = float("nan")

        try:
            ma = ma_30w(close, t)
            ma_series = ma_30w_series(close.loc[:t])
            slope = ma_slope_pct(ma_series, t, sessions=10)
            row["MA_30W"] = ma
            row["MA_30W_Slope_10S_Pct"] = slope
            row["Stage"] = classify_stage(float(close.loc[t]), ma, slope)
        except (ValueError, KeyError):
            row["MA_30W"] = float("nan")
            row["MA_30W_Slope_10S_Pct"] = float("nan")
            row["Stage"] = None

        try:
            h52 = high_52w(high, t)
            row["High_52W"] = h52
            row["Near_52W_High"] = bool(close.loc[t] >= 0.97 * h52)
        except (ValueError, KeyError):
            row["High_52W"] = float("nan")
            row["Near_52W_High"] = False

        try:
            vr = volume_ratio(volume, t)
            row["Volume_Ratio"] = vr
        except (ValueError, KeyError):
            row["Volume_Ratio"] = float("nan")

        try:
            ud = up_down_ratio(close, volume, t)
            row["U_D"] = ud
        except (ValueError, KeyError):
            row["U_D"] = float("nan")

        try:
            row["AvgValue20"] = float((close * volume).loc[:t].tail(20).mean())
        except Exception:
            row["AvgValue20"] = float("nan")

        row["Breakout"] = breakout(
            row.get("Stage"), float(close.loc[t]), row.get("High_52W", float("nan")), row.get("Volume_Ratio", float("nan"))
        ) if row.get("Stage") else False
        row["Breakout_Confirmed"] = breakout_confirmed(
            row.get("Stage"), float(close.loc[t]), row.get("High_52W", float("nan")), row.get("Volume_Ratio", float("nan")), row.get("U_D", float("nan"))
        ) if row.get("Stage") else False
        rows.append(row)

    result = pd.DataFrame(rows).set_index("Symbol")
    if not result.empty:
        result["RS_Score"] = rs_score(result["RS_Blend"])
        result["Liquid_UI_Filter"] = result["AvgValue20"] > 5e7
    return result
