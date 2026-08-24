"""Universe-level RS/Stage calculations on validated pre-market snapshots."""
from __future__ import annotations

import numpy as np
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
    """Calculate RS/Stage fields before optional liquidity filtering.

    The guide interpretation layer consumes only fields produced here or by
    the validated stock-history path. Missing history remains explicit.
    """
    rows: list[dict] = []

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
            row["Volume_Ratio"] = volume_ratio(volume, t)
        except (ValueError, KeyError):
            row["Volume_Ratio"] = float("nan")

        try:
            row["U_D"] = up_down_ratio(close, volume, t)
        except (ValueError, KeyError):
            row["U_D"] = float("nan")

        value = (close * volume).loc[:t].dropna()
        row["AvgValue20"] = float(value.iloc[-20:].mean()) if len(value) >= 20 else np.nan

        try:
            close_50 = close.loc[:t].dropna()
            row["SMA_50"] = float(close_50.iloc[-50:].mean()) if len(close_50) >= 50 else np.nan
            row["Below_50DMA"] = bool(close.loc[t] < row["SMA_50"]) if pd.notna(row["SMA_50"]) else False
        except (ValueError, KeyError):
            row["SMA_50"] = np.nan
            row["Below_50DMA"] = False

        row["Extended_20Pct"] = bool(
            pd.notna(row["MA_30W"]) and float(close.loc[t]) > 1.20 * float(row["MA_30W"])
        )
        row["Distribution"] = bool(pd.notna(row["U_D"]) and row["U_D"] < 0.7)
        row["Heavy_Distribution"] = bool(pd.notna(row["U_D"]) and row["U_D"] < 0.6)

        row["Breakout"] = (
            breakout(
                row.get("Stage"),
                float(close.loc[t]),
                row.get("High_52W", float("nan")),
                row.get("Volume_Ratio", float("nan")),
            )
            if row.get("Stage")
            else False
        )
        row["Breakout_Confirmed"] = (
            breakout_confirmed(
                row.get("Stage"),
                float(close.loc[t]),
                row.get("High_52W", float("nan")),
                row.get("Volume_Ratio", float("nan")),
                row.get("U_D", float("nan")),
            )
            if row.get("Stage")
            else False
        )
        rows.append(row)

    result = pd.DataFrame(rows).set_index("Symbol")
    if not result.empty:
        result["RS_Score"] = rs_score(result["RS_Blend"])
        result["Liquid_UI_Filter"] = result["AvgValue20"] > 5e7
    return result
