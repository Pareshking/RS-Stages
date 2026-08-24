"""Pure reference calculations for RS-Stages.

No Streamlit/UI/data-download code belongs here. Functions are deterministic
quantitative primitives used by tests and later application code.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def latest_completed_session(index: pd.DatetimeIndex, decision_date: pd.Timestamp) -> pd.Timestamp:
    """Return the latest observed session strictly before a pre-market decision date."""
    idx = pd.DatetimeIndex(index).sort_values().unique()
    pos = idx.searchsorted(pd.Timestamp(decision_date), side="left") - 1
    if pos < 0:
        raise ValueError("No completed session is available before decision date")
    return idx[pos]


def calendar_asof(index: pd.DatetimeIndex, target: pd.Timestamp) -> pd.Timestamp:
    """Return the last observed session on or before a calendar reference date."""
    idx = pd.DatetimeIndex(index).sort_values().unique()
    pos = idx.searchsorted(pd.Timestamp(target), side="right") - 1
    if pos < 0:
        raise ValueError("No session exists on or before calendar reference date")
    return idx[pos]


def rs_returns(close: pd.Series, latest: pd.Timestamp) -> dict[int, float]:
    """Calculate 3/6/9/12 calendar-month simple returns."""
    close = close.sort_index().dropna()
    t = calendar_asof(close.index, pd.Timestamp(latest))
    latest_close = float(close.loc[t])
    out: dict[int, float] = {}
    for months in (3, 6, 9, 12):
        ref = calendar_asof(close.index, t - pd.DateOffset(months=months))
        out[months] = latest_close / float(close.loc[ref]) - 1.0
    return out


def rs_blend(returns: dict[int, float]) -> float:
    return 0.40 * returns[3] + 0.20 * returns[6] + 0.20 * returns[9] + 0.20 * returns[12]


def rs_score(blend: pd.Series) -> pd.Series:
    """Cross-sectional RS score using rank(pct=True, method='min') × 98 + 1."""
    valid = blend.dropna()
    pct = valid.rank(pct=True, method="min")
    result = pd.Series(np.nan, index=blend.index, dtype=float)
    result.loc[valid.index] = np.rint(pct * 98.0 + 1.0)
    return result


def calendar_window(series: pd.Series, end: pd.Timestamp, weeks: int) -> pd.Series:
    """Return observations from the calendar start reference session through end."""
    s = series.sort_index()
    t = calendar_asof(s.index, pd.Timestamp(end))
    start_ref = calendar_asof(s.index, t - pd.Timedelta(weeks=weeks))
    return s.loc[(s.index >= start_ref) & (s.index <= t)]


def ma_30w(close: pd.Series, end: pd.Timestamp) -> float:
    """30-calendar-week simple moving average using calendar start as-of session."""
    s = close.sort_index().dropna()
    t = calendar_asof(s.index, pd.Timestamp(end))
    start_ref = calendar_asof(s.index, t - pd.Timedelta(weeks=30))
    window = s.loc[(s.index >= start_ref) & (s.index <= t)]
    if len(window) < 2:
        raise ValueError("Insufficient history for 30W MA window")
    return float(window.mean())


def ma_30w_series(close: pd.Series) -> pd.Series:
    """Calendar-window 30W MA at each session where a reference session exists."""
    s = close.sort_index()
    values = []
    for t in s.index:
        try:
            values.append(ma_30w(s, t))
        except ValueError:
            values.append(np.nan)
    return pd.Series(values, index=s.index, dtype=float)


def ma_slope_pct(ma: pd.Series, end: pd.Timestamp, sessions: int = 10) -> float:
    """10-session percentage change in the 30W MA."""
    s = ma.sort_index().dropna()
    pos = s.index.searchsorted(pd.Timestamp(end), side="right") - 1
    if pos < sessions:
        raise ValueError("Insufficient history for slope")
    prior = float(s.iloc[pos - sessions])
    if prior == 0:
        raise ValueError("Cannot calculate slope from zero prior MA")
    return (float(s.iloc[pos]) / prior - 1.0) * 100.0


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
    """Maximum adjusted High in a 52-calendar-week window."""
    s = close_high.sort_index().dropna()
    t = calendar_asof(s.index, pd.Timestamp(end))
    start_ref = calendar_asof(s.index, t - pd.Timedelta(weeks=52))
    window = s.loc[(s.index >= start_ref) & (s.index <= t)]
    if len(window) < min_sessions:
        raise ValueError("Insufficient history for 52W high")
    return float(window.max())


def near_52w_high(close: float, high52: float, threshold: float = 0.03) -> bool:
    return bool(close >= (1.0 - threshold) * high52)


def volume_ratio(volume: pd.Series, end: pd.Timestamp) -> float:
    """Latest completed-session volume / preceding 50-session average."""
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
    c, v = c.astype(float), v.astype(float)
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


def ud_classification(ud: float) -> str:
    """Apply locked U/D thresholds with Heavy Distribution taking precedence."""
    if np.isnan(ud):
        return "Undefined"
    if ud < 0.6:
        return "Heavy Distribution"
    if ud < 0.7:
        return "Distribution Warning"
    if ud <= 1.3:
        return "Neutral"
    if ud <= 1.5:
        return "Accumulating"
    return "Strong Accumulation"


def breakout(stage: str, close: float, high52: float, vol_ratio: float) -> bool:
    return stage == "Stage 2 — Advancing" and near_52w_high(close, high52) and vol_ratio > 1.5


def breakout_confirmed(stage: str, close: float, high52: float, vol_ratio: float, ud: float) -> bool:
    return breakout(stage, close, high52, vol_ratio) and ud > 1.3
