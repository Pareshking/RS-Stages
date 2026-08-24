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
    low_52w,
    ma_10w_series,
    ma_30w,
    ma_30w_series,
    ma_slope_pct,
    rs_blend,
    rs_returns,
    rs_score,
    up_down_ratio,
    volume_ratio,
)

#: Columns the presentation layer may read without recomputing anything.
TREND_COLUMNS = ("Close", "MA_10W", "MA_30W", "Volume")

#: The five trend-health conditions, in display order. Each is a locked field or
#: a strict comparison between locked fields; none introduces new methodology.
TREND_HEALTH_CONDITIONS = (
    ("Above_MA_30W", "Close is above the 30-week line"),
    ("MA_30W_Rising", "30-week line is rising"),
    ("MA10W_Above_MA30W", "10-week line is above the 30-week line"),
    ("Above_MA_10W", "Close is above the 10-week line"),
    ("RS_Not_Lagging", "Relative strength is not lagging (RS ≥ 50)"),
)


def _analyze_symbol(
    symbol: str, snap: DecisionSnapshot, trend_sessions: int | None
) -> tuple[dict, pd.DataFrame | None]:
    """Calculate one symbol's locked fields and, optionally, its trend series.

    The trend series is a by-product of calculations the row already performs,
    so collecting it costs no additional market data and no additional moving
    average passes.
    """
    data = snap.data
    close = data["Close"].astype(float)
    high = data["High"].astype(float)
    volume = data["Volume"].astype(float)
    t = snap.latest_completed_session
    row: dict = {"Symbol": symbol, "Date": t}

    # Latest completed-session close. Every price-derived presentation field
    # below is traceable to this single observation.
    try:
        row["Close"] = float(close.loc[t])
    except (KeyError, TypeError, ValueError):
        row["Close"] = float("nan")

    try:
        returns = rs_returns(close, t)
        row.update({f"R{m}M": returns[m] for m in returns})
        row["RS_Blend"] = rs_blend(returns)
    except (ValueError, KeyError):
        row["RS_Blend"] = float("nan")

    ma_30w_full = ma_10w_full = None
    try:
        ma = ma_30w(close, t)
        ma_30w_full = ma_30w_series(close.loc[:t])
        slope = ma_slope_pct(ma_30w_full, t, sessions=10)
        row["MA_30W"] = ma
        row["MA_30W_Slope_10S_Pct"] = slope
        row["Stage"] = classify_stage(float(close.loc[t]), ma, slope)
    except (ValueError, KeyError):
        row["MA_30W"] = float("nan")
        row["MA_30W_Slope_10S_Pct"] = float("nan")
        row["Stage"] = None

    # 10-calendar-week MA — locked-spec v2.1. Same calendar-window construction
    # as the 30-week line so the two are directly comparable.
    try:
        ma_10w_full = ma_10w_series(close.loc[:t])
        row["MA_10W"] = float(ma_10w_full.loc[t])
        if not np.isfinite(row["MA_10W"]):
            row["MA_10W"] = float("nan")
    except (ValueError, KeyError):
        row["MA_10W"] = float("nan")

    try:
        h52 = high_52w(high, t)
        row["High_52W"] = h52
        row["Near_52W_High"] = bool(close.loc[t] >= 0.97 * h52)
    except (ValueError, KeyError):
        row["High_52W"] = float("nan")
        row["Near_52W_High"] = False

    # 52-week low mirrors the 52-week high window exactly. It is a range input
    # only; when the provider frame carries no Low column the field stays NaN
    # rather than being substituted with Close.
    if "Low" in data.columns:
        try:
            row["Low_52W"] = low_52w(data["Low"].astype(float), t)
        except (ValueError, KeyError):
            row["Low_52W"] = float("nan")
    else:
        row["Low_52W"] = float("nan")

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

    # Ext_Pct is the displayed extension above the 30-week line. The locked
    # Extended_20Pct condition keeps its specified form (Close > 1.20 × MA_30W)
    # rather than being re-derived from Ext_Pct: the two are algebraically
    # equivalent but not bit-identical in floating point, and the locked
    # comparison is the authority.
    row["Ext_Pct"] = (
        (row["Close"] / row["MA_30W"] - 1.0) * 100.0
        if pd.notna(row["Close"]) and pd.notna(row["MA_30W"]) and row["MA_30W"] != 0
        else np.nan
    )
    row["Extended_20Pct"] = bool(
        pd.notna(row["MA_30W"]) and float(close.loc[t]) > 1.20 * float(row["MA_30W"])
    )
    row["Pct_From_52W_High"] = (
        (row["Close"] / row["High_52W"] - 1.0) * 100.0
        if pd.notna(row["Close"]) and pd.notna(row["High_52W"]) and row["High_52W"] != 0
        else np.nan
    )

    row["Above_MA_30W"] = bool(pd.notna(row["Close"]) and pd.notna(row["MA_30W"]) and row["Close"] > row["MA_30W"])
    row["Above_MA_10W"] = bool(pd.notna(row["Close"]) and pd.notna(row["MA_10W"]) and row["Close"] > row["MA_10W"])
    row["MA10W_Above_MA30W"] = bool(
        pd.notna(row["MA_10W"]) and pd.notna(row["MA_30W"]) and row["MA_10W"] > row["MA_30W"]
    )
    row["MA_30W_Rising"] = bool(
        pd.notna(row["MA_30W_Slope_10S_Pct"]) and row["MA_30W_Slope_10S_Pct"] > 0.0
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

    trend = None
    if trend_sessions is not None:
        frame = pd.DataFrame(
            {
                "Close": close.loc[:t],
                "MA_10W": ma_10w_full if ma_10w_full is not None else np.nan,
                "MA_30W": ma_30w_full if ma_30w_full is not None else np.nan,
                "Volume": volume.loc[:t],
            }
        )
        trend = frame.tail(trend_sessions) if trend_sessions > 0 else frame

    return row, trend


def _finalize(result: pd.DataFrame) -> pd.DataFrame:
    """Apply cross-sectional fields and the trend-health count.

    RS is cross-sectional, so it can only be scored once every symbol's blend
    exists. Trend health depends on RS and is therefore also finalized here.
    """
    if result.empty:
        return result
    result["RS_Score"] = rs_score(result["RS_Blend"])
    result["Liquid_UI_Filter"] = result["AvgValue20"] > 5e7
    result["RS_Not_Lagging"] = (result["RS_Score"] >= 50).astype(bool)
    result["Trend_Health"] = (
        sum(result[field].astype(bool).astype(int) for field, _ in TREND_HEALTH_CONDITIONS)
    ).astype(int)
    return result


def analyze_universe(snapshots: dict[str, DecisionSnapshot]) -> pd.DataFrame:
    """Calculate RS/Stage fields before optional liquidity filtering.

    The guide interpretation layer consumes only fields produced here or by
    the validated stock-history path. Missing history remains explicit.
    """
    rows = [_analyze_symbol(symbol, snap, None)[0] for symbol, snap in snapshots.items()]
    return _finalize(pd.DataFrame(rows).set_index("Symbol"))


def analyze_universe_with_trend(
    snapshots: dict[str, DecisionSnapshot], trend_sessions: int = 260
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Return the locked snapshot plus each symbol's trailing trend series.

    Identical row output to :func:`analyze_universe`; the trend series is the
    per-session Close, 10-week MA, 30-week MA and Volume already computed while
    building the row. It exists so the presentation layer can draw price history
    without re-downloading market data or recomputing locked averages.
    """
    rows: list[dict] = []
    trends: dict[str, pd.DataFrame] = {}
    for symbol, snap in snapshots.items():
        row, trend = _analyze_symbol(symbol, snap, trend_sessions)
        rows.append(row)
        if trend is not None:
            trends[str(symbol)] = trend
    return _finalize(pd.DataFrame(rows).set_index("Symbol")), trends
