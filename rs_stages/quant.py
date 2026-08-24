"""Pure reference calculations for RS-Stages.

These functions intentionally contain no Streamlit/UI/data-download code.
They are the quantitative layer used by tests and later application code.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def latest_completed_session(index: pd.DatetimeIndex, decision_date: pd.Timestamp) -> pd.Timestamp:
    """Return the latest observed session on/before the pre-market decision date."""
    idx = pd.DatetimeIndex(index).sort_values().unique()
    pos = idx.searchsorted(pd.Timestamp(decision_date), side="right") - 1
    if pos < 0:
        raise ValueError("No completed session is available before decision date")
    return idx[pos]


def calendar_asof(index: pd.DatetimeIndex, target: pd.Timestamp) -> pd.Timestamp:
    """Return the last observed session on/before a calendar reference date."""
    return latest_completed_session(index, pd.Timestamp(target))


def rs_returns(close: pd.Series, latest: pd.Timestamp) -> dict[int, float]:
    """Calculate 3/6/9/12 calendar-month simple returns."""
    close = close.sort_index().dropna()
    t = pd.Timestamp(latest)
    if t not in close.index:
        t = calendar_asof(close.index, t)
    latest_close = float(close.loc[t])
    out: dict[int, float] = {}
    for months in (3, 6, 9, 12):
        ref = calendar_asof(close.index, t - pd.DateOffset(months=months))
        out[months] = latest_close / float(close.loc[ref]) - 1.0
    return out


def rs_blend(returns: dict[int, float]) -> float:
    return (
        0.40 * returns[3]
        + 0.20 * returns[6]
        + 0.20 * returns[9]
        + 0.20 * returns[12]
    )


def rs_score(blend: pd.Series) -> pd.Series:
    """Cross-sectional RS score using pandas min-percentile ranking."""
    valid = blend.dropna()
    pct = valid.rank(pct=True, method="min")
    result = pd.Series(np.nan, index=blend.index, dtype=float)
    result.loc[valid.index] = np.rint(pct * 98.0 + 1.0)
    return result


def calendar_window(series: pd.Series, end: pd.Timestamp, weeks: int) -> pd.Series:
    end = pd.Timestamp(end)
    start = end - pd.Timedelta(weeks=weeks)
    s = series.sort_index()
    return s.loc[(s.index >= start) & (s.index <= end)]


def ma_30w(close: pd.Series, end: pd.Timestamp) -> float:
    window = calendar_window(close.dropna(), end, 30)
    if window.empty:
        raise ValueError("Insufficient history for 30W MA")
    return float(window.mean())


def ma_30w_series(close: pd.Series) -> pd.Series:
    """Calendar-window 30W MA at every available session."""
    s = close.sort_index()
    values = []
    for t in s.index:
        w = calendar_window(s.loc[:t].dropna(), t, 30)
        values.append(w.mean() if len(w) else np.nan)
    return pd.Series(values, index=s.index, dtype=float)


def ma_slope_pct(ma: pd.Series, end: pd.Timestamp, sessions: int = 10) -> float:
    s = ma.sort_index().dropna()
    pos = s.index.searchsorted(pd.Timestamp(end), side="right") - 1
    if pos < sessions:
        raise ValueError("Insufficient history for slope")
    current = float(s.iloc[pos])
    prior = float(s.iloc[pos - sessions])
    return (current / prior - 1.0) * 100.0


def classify_stage(close: float, ma: float, slope_pct: float) -> str:
    above = close > ma
    rising = slope_pct > 0.0
    if above and rising:
        return "Stage 2 — Advancing"
    if above and not rising:
        return "Stage 3 — Topping"
    if not above and not rising:
        return "Stage 4 — Declining"
    return "Stage 1 — Basing"


def high_52w(close_high: pd.Series, end: pd.Timestamp, min_sessions: int = 200) -> float:
    window = calendar_window(close_high.dropna(), end, 52)
    if len(window) < min_sessions:
        raise ValueError("Insufficient history for 52W high")
    return float(window.max())


def near_52w_high(close: float, high52: float, threshold: float = 0.03) -> bool:
    return bool(close >= (1.0 - threshold) * high52)


def volume_ratio(volume: pd.Series, end: pd.Timestamp) -> float:
    """Latest completed-session volume / prior 50 completed-session average."""
    v = volume.sort_index().astype(float)
    pos = v.index.searchsorted(pd.Timestamp(end), side="right") - 1
    if pos < 50:
        raise ValueError("Insufficient history for prior-50 volume baseline")
    baseline = float(v.iloc[pos - 50 : pos].mean())
    if baseline == 0:
        return np.inf if float(v.iloc[pos]) > 0 else np.nan
    return float(v.iloc[pos]) / baseline


def up_down_ratio(close: pd.Series, volume: pd.Series, end: pd.Timestamp) -> float:
    """20-session U/D ending at the latest completed session."""
    c, v = close.sort_index().align(volume.sort_index(), join="inner")
    c = c.astype(float)
    v = v.astype(float)
    pos = c.index.searchsorted(pd.Timestamp(end), side="right") - 1
    if pos < 20:
        raise ValueError("Insufficient history for 20-session U/D")
    delta = c.diff()
    up = v.where(delta > 0, 0.0)
    down = v.where(delta < 0, 0.0)
    up_sum = float(up.iloc[pos - 19 : pos + 1].sum())
    down_sum = float(down.iloc[pos - 19 : pos + 1].sum())
    if down_sum == 0:
        return np.inf if up_sum > 0 else np.nan
    return up_sum / down_sum


def breakout(stage: str, close: float, high52: float, vol_ratio: float) -> bool:
    return stage == "Stage 2 — Advancing" and near_52w_high(close, high52) and vol_ratio > 1.5


def breakout_confirmed(stage: str, close: float, high52: float, vol_ratio: float, ud: float) -> bool:
    return breakout(stage, close, high52, vol_ratio) and ud > 1.3
