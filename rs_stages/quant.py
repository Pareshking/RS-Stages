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


def ma_calendar_weeks(close: pd.Series, end: pd.Timestamp, weeks: int) -> float:
    """Simple moving average over every valid session in a calendar-week window.

    This is the single locked moving-average definition. The window starts at
    the last observed session on or before ``end - weeks`` and ends at the last
    observed session on or before ``end``. It is deliberately *not* a fixed
    trading-day row count, so the number of observations varies with holidays.
    """
    s = close.sort_index().dropna()
    t = calendar_asof(s.index, pd.Timestamp(end))
    start_ref = calendar_asof(s.index, t - pd.Timedelta(weeks=weeks))
    window = s.loc[(s.index >= start_ref) & (s.index <= t)]
    if len(window) < 2:
        raise ValueError(f"Insufficient history for {weeks}W MA window")
    return float(window.mean())


def ma_calendar_weeks_series(close: pd.Series, weeks: int) -> pd.Series:
    """Calendar-window MA at each session, evaluated as of that session.

    Values are identical to calling :func:`ma_calendar_weeks` at every session;
    window boundaries are resolved by position instead of by repeated sorting so
    the per-symbol cost is linear rather than quadratic. Sessions without a
    complete reference window yield NaN rather than a partial-window average.
    """
    raw = close.sort_index()
    clean = raw.dropna()
    if clean.empty:
        return pd.Series(np.nan, index=raw.index, dtype=float)

    raw_index = pd.DatetimeIndex(raw.index)
    ends = clean.index.searchsorted(raw_index, side="right") - 1
    effective = clean.index[np.clip(ends, 0, None)]
    starts = clean.index.searchsorted(effective - pd.Timedelta(weeks=weeks), side="right") - 1

    values = np.full(len(raw_index), np.nan, dtype=float)
    for position, (start, end) in enumerate(zip(starts, ends)):
        if start < 0 or end < 0 or (end - start + 1) < 2:
            continue
        values[position] = float(clean.iloc[start : end + 1].mean())
    return pd.Series(values, index=raw.index, dtype=float)


def ma_30w(close: pd.Series, end: pd.Timestamp) -> float:
    """30-calendar-week simple moving average using calendar start as-of session."""
    return ma_calendar_weeks(close, end, 30)


def ma_30w_series(close: pd.Series) -> pd.Series:
    """Calendar-window 30W MA at each session where a reference session exists."""
    return ma_calendar_weeks_series(close, 30)


def ma_10w(close: pd.Series, end: pd.Timestamp) -> float:
    """10-calendar-week simple moving average.

    Adopted in locked-spec v2.1 as the shorter trend reference. It uses exactly
    the same calendar-window construction as the 30-week MA so the two lines are
    directly comparable; it is not a 50-row trading-day average.
    """
    return ma_calendar_weeks(close, end, 10)


def ma_10w_series(close: pd.Series) -> pd.Series:
    """Calendar-window 10W MA at each session where a reference session exists."""
    return ma_calendar_weeks_series(close, 10)


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
    """Classify the locked 30W-MA stage using strict comparisons."""
    values = (close, ma, slope_pct)
    if not all(np.isfinite(float(value)) for value in values):
        raise ValueError("Stage classification requires finite Close, MA and slope")
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


def low_52w(close_low: pd.Series, end: pd.Timestamp, min_sessions: int = 200) -> float:
    """Minimum adjusted Low in a 52-calendar-week window.

    Mirrors :func:`high_52w` exactly — same calendar window, same minimum
    observation count — so the pair defines a symmetric 52-week range. It is a
    presentation/range input only; no locked signal consumes it.
    """
    s = close_low.sort_index().dropna()
    t = calendar_asof(s.index, pd.Timestamp(end))
    start_ref = calendar_asof(s.index, t - pd.Timedelta(weeks=52))
    window = s.loc[(s.index >= start_ref) & (s.index <= t)]
    if len(window) < min_sessions:
        raise ValueError("Insufficient history for 52W low")
    return float(window.min())


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


# --- v2.2: pre-breakout structure -------------------------------------------
#
# Every threshold below is a single named constant, because §5.1 records that
# the trend-template figures are transcribed from a published source and must be
# verifiable against it, and §10.5 records that the contraction thresholds are
# ours rather than the book's. Neither claim survives if the numbers are buried
# in expressions.

#: §5.1 — Minervini trend template. Transcribed, not derived.
TREND_TEMPLATE_LOW_MULTIPLE = 1.30      # TT6: >= 30% above the 52-week low
TREND_TEMPLATE_HIGH_FRACTION = 0.75     # TT7: within 25% of the 52-week high
TREND_TEMPLATE_MIN_RS = 70.0            # TT8
TREND_TEMPLATE_RISING_SESSIONS = 21     # TT3: "at least one month"

#: §4.1 — RS line.
RS_LINE_HIGH_TOLERANCE = 0.005          # "at a new high" without float equality
RS_LINE_PRICE_GAP_PCT = -5.0            # ours: price demonstrably off its high
RS_LINE_MIN_OVERLAP = 200               # sessions of stock/benchmark overlap

#: §10.4 / §10.5 / §10.6 — volatility, contraction, dry-up, pivot. All ours.
ATR_SESSIONS = 14
VCP_BASE_SESSIONS = 50
VCP_BLOCKS = 5
VCP_CONTRACTION_RATIO_MAX = 0.60
VCP_VOLUME_DRYUP_MAX = 0.80
VCP_MIN_CONTRACTIONS = 2
VOLUME_DRYUP_RECENT = 10
VOLUME_DRYUP_BASELINE = 50

#: §11.1 — Stage 1 readiness.
STAGE1_SLOPE_MIN = -0.10
STAGE1_RS_MIN = 50.0
STAGE1_CONTRACTION_MAX = 0.70
STAGE1_DRYUP_MAX = 0.90


def _position(index: pd.DatetimeIndex, end: pd.Timestamp) -> int:
    """Index position of the latest session at or before ``end``."""
    return index.searchsorted(pd.Timestamp(end), side="right") - 1


def sma(close: pd.Series, end: pd.Timestamp, sessions: int) -> float:
    """Session-based simple moving average ending at ``end`` inclusive.

    Deliberately distinct from :func:`ma_calendar_weeks`. §5 locks the 30-week
    average as a calendar-week construction; §5.1's criteria are stated by their
    author in trading sessions. Thirty calendar weeks is not 150 sessions, and
    collapsing the two would restate one author's rule in another's units.

    Sessions without a Close are dropped before the window is taken, so this is
    the mean of the latest ``sessions`` closes that exist. Averaging whatever
    survives inside a fixed slice would report the mean of 199 observations as a
    200-session average, which §3 forbids: the shortfall would be invisible.
    A calendar-window average has no such problem — its bounds are dates, so
    skipping a gap changes nothing — which is why only the session-count
    averages need this.
    """
    c = close.sort_index().astype(float).dropna()
    pos = _position(c.index, end)
    if pos + 1 < sessions:
        raise ValueError(f"Insufficient history for a {sessions}-session average")
    return float(c.iloc[pos + 1 - sessions : pos + 1].mean())


def sma_series(close: pd.Series, sessions: int) -> pd.Series:
    """The same average at every session, for slope tests and charting.

    Missing closes are dropped first, for the reason given in :func:`sma`.
    """
    valid = close.sort_index().astype(float).dropna()
    return valid.rolling(sessions, min_periods=sessions).mean()


def sma_rising(close: pd.Series, end: pd.Timestamp, sessions: int, over: int) -> bool:
    """True when the ``sessions``-session average is higher than it was ``over`` ago."""
    series = sma_series(close, sessions).dropna()
    if series.empty:
        raise ValueError(f"Insufficient history for a {sessions}-session average")
    pos = _position(series.index, end)
    if pos < over:
        raise ValueError("Insufficient history to measure the average's direction")
    return bool(series.iloc[pos] > series.iloc[pos - over])


def trend_template(
    close: float,
    sma_50: float,
    sma_150: float,
    sma_200: float,
    sma_200_rising: bool,
    low_52w: float,
    high_52w: float,
    rs: float,
) -> dict[str, bool | int]:
    """§5.1 — the eight criteria, each reported separately.

    A count alone cannot distinguish a stock failing only on RS from one failing
    on six, so every criterion is published and the count is derived from them.
    Any non-finite input fails its own criterion rather than poisoning the rest.
    """
    def ok(value: float) -> bool:
        return bool(np.isfinite(value))

    tt = {
        "TT1_Above_150_200": ok(close) and ok(sma_150) and ok(sma_200)
        and close > sma_150 and close > sma_200,
        "TT2_150_Above_200": ok(sma_150) and ok(sma_200) and sma_150 > sma_200,
        "TT3_200_Rising": bool(sma_200_rising),
        "TT4_50_Above_150_200": ok(sma_50) and ok(sma_150) and ok(sma_200)
        and sma_50 > sma_150 and sma_50 > sma_200,
        "TT5_Above_50": ok(close) and ok(sma_50) and close > sma_50,
        "TT6_Above_52W_Low": ok(close) and ok(low_52w)
        and close >= low_52w * TREND_TEMPLATE_LOW_MULTIPLE,
        "TT7_Near_52W_High": ok(close) and ok(high_52w)
        and close >= high_52w * TREND_TEMPLATE_HIGH_FRACTION,
        "TT8_RS": ok(rs) and rs >= TREND_TEMPLATE_MIN_RS,
    }
    result: dict[str, bool | int] = {k: bool(v) for k, v in tt.items()}
    result["Trend_Template_Score"] = int(sum(result.values()))
    result["Trend_Template_Pass"] = bool(result["Trend_Template_Score"] == len(tt))
    return result


def rs_line(close: pd.Series, benchmark: pd.Series) -> pd.Series:
    """§4.1 — Close / Benchmark_Close on the sessions the two actually share.

    Inner join, never a fill: a benchmark session the stock did not trade, or a
    stock session the index did not, is dropped. Manufacturing either side's
    price to complete the calendar would invent the very quantity being measured.
    """
    c, b = close.sort_index().astype(float).align(
        benchmark.sort_index().astype(float), join="inner"
    )
    valid = c.notna() & b.notna() & (b != 0)
    return (c[valid] / b[valid]).astype(float)


def rs_line_high_52w(line: pd.Series, end: pd.Timestamp, min_sessions: int = RS_LINE_MIN_OVERLAP) -> float:
    """Highest RS line value across the trailing 52 calendar weeks."""
    window = calendar_window(line, end, 52)
    if len(window) < min_sessions:
        raise ValueError("Insufficient stock/benchmark overlap for a 52-week RS line high")
    return float(window.max())


def rs_line_at_high(line_value: float, line_high: float) -> bool:
    """Within tolerance of the 52-week RS line high."""
    if not (np.isfinite(line_value) and np.isfinite(line_high)) or line_high == 0:
        return False
    return bool(line_value >= line_high * (1.0 - RS_LINE_HIGH_TOLERANCE))


def rs_line_nh_before_price(line_value: float, line_high: float, pct_from_52w_high: float) -> bool:
    """§4.1 — relative strength at a new high while price is not.

    The ordering is the signal. A stock making new price highs is already
    advancing and is O'Neil's breakout, not his leading tell; the case worth
    naming is strength leading price out of a base.
    """
    if not np.isfinite(pct_from_52w_high):
        return False
    return rs_line_at_high(line_value, line_high) and bool(
        pct_from_52w_high <= RS_LINE_PRICE_GAP_PCT
    )


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Wilder's true range; undefined on the first session, which has no prior close."""
    h, l = high.sort_index().astype(float), low.sort_index().astype(float)
    c = close.sort_index().astype(float)
    h, l = h.align(l, join="inner")
    h, c = h.align(c, join="inner")
    l = l.reindex(h.index)
    prev = c.shift(1)
    return pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)


def atr_pct(high: pd.Series, low: pd.Series, close: pd.Series, end: pd.Timestamp) -> float:
    """§10.4 — ATR(14) as a percentage of the closing price."""
    tr = true_range(high, low, close).dropna()
    pos = _position(tr.index, end)
    if pos + 1 < ATR_SESSIONS:
        raise ValueError("Insufficient history for ATR(14)")
    atr = float(tr.iloc[pos + 1 - ATR_SESSIONS : pos + 1].mean())
    c = close.sort_index().astype(float)
    last = float(c.iloc[_position(c.index, end)])
    if not np.isfinite(last) or last == 0:
        return float("nan")
    return atr / last * 100.0


def range_blocks(
    high: pd.Series, low: pd.Series, close: pd.Series, end: pd.Timestamp
) -> list[float]:
    """§10.5 — each block's high-low range as a percentage of its mean close.

    Five consecutive ten-session blocks across the fifty-session base, oldest
    first. Fixed blocks rather than detected swings: swing detection needs its
    own tunable definition of a swing, and a second undocumented parameter set
    inside a pattern the source already leaves qualitative is exactly what §1
    warns against.
    """
    h, l = high.sort_index().astype(float), low.sort_index().astype(float)
    c = close.sort_index().astype(float)
    h, l = h.align(l, join="inner")
    c = c.reindex(h.index)
    pos = _position(h.index, end)
    if pos + 1 < VCP_BASE_SESSIONS:
        raise ValueError("Insufficient history for the contraction base")
    size = VCP_BASE_SESSIONS // VCP_BLOCKS
    start = pos + 1 - VCP_BASE_SESSIONS
    out: list[float] = []
    for block in range(VCP_BLOCKS):
        lo = start + block * size
        window_h, window_l = h.iloc[lo : lo + size], l.iloc[lo : lo + size]
        mean_close = float(c.iloc[lo : lo + size].mean())
        if not np.isfinite(mean_close) or mean_close == 0:
            return [float("nan")] * VCP_BLOCKS
        out.append((float(window_h.max()) - float(window_l.min())) / mean_close * 100.0)
    return out


def vcp_contractions(blocks: list[float]) -> int:
    """How many times the range tightened against the block before it."""
    return int(
        sum(
            1
            for a, b in zip(blocks, blocks[1:])
            if np.isfinite(a) and np.isfinite(b) and b < a
        )
    )


def contraction_ratio(blocks: list[float]) -> float:
    """Final block's range against the first: below 1 means the base is tightening."""
    if len(blocks) < 2 or not np.isfinite(blocks[0]) or blocks[0] == 0:
        return float("nan")
    if not np.isfinite(blocks[-1]):
        return float("nan")
    return blocks[-1] / blocks[0]


def volume_dryup(volume: pd.Series, end: pd.Timestamp) -> float:
    """§10.5 — recent volume against the longer baseline preceding it.

    The opposite instrument to :func:`volume_ratio`, which compares one session
    to a baseline and so detects the breakout spike. This compares a sustained
    window to a longer one and detects the drought that precedes it.
    """
    v = volume.sort_index().astype(float)
    pos = _position(v.index, end)
    needed = VOLUME_DRYUP_RECENT + VOLUME_DRYUP_BASELINE
    if pos + 1 < needed:
        raise ValueError("Insufficient history for the volume dry-up baseline")
    recent_start = pos + 1 - VOLUME_DRYUP_RECENT
    recent = float(v.iloc[recent_start : pos + 1].mean())
    baseline = float(v.iloc[recent_start - VOLUME_DRYUP_BASELINE : recent_start].mean())
    if not np.isfinite(baseline) or baseline == 0:
        return float("nan")
    return recent / baseline


def vcp_setup(ratio: float, dryup: float, contractions: int) -> bool:
    """§10.5 — tightening range, drying volume, and more than a single step."""
    if not (np.isfinite(ratio) and np.isfinite(dryup)):
        return False
    return bool(
        ratio <= VCP_CONTRACTION_RATIO_MAX
        and dryup <= VCP_VOLUME_DRYUP_MAX
        and contractions >= VCP_MIN_CONTRACTIONS
    )


def vcp_pivot(high: pd.Series, end: pd.Timestamp) -> float:
    """§10.6 — the highest high of the base: the buy point at its top."""
    h = high.sort_index().astype(float)
    pos = _position(h.index, end)
    if pos + 1 < VCP_BASE_SESSIONS:
        raise ValueError("Insufficient history for the base pivot")
    return float(h.iloc[pos + 1 - VCP_BASE_SESSIONS : pos + 1].max())


def pct_to_pivot(close: float, pivot: float) -> float:
    """Distance still to travel; zero at the pivot and negative once through it."""
    if not (np.isfinite(close) and np.isfinite(pivot)) or close == 0:
        return float("nan")
    return (pivot / close - 1.0) * 100.0


def stage1_readiness(
    slope_pct: float, rs: float, ratio: float, dryup: float, close: float, ma_10w: float
) -> int:
    """§11.1 — how ready a base looks, counted 0-5.

    Ranking only. No locked signal reads this, and a Stage 1 stock scoring five
    still carries the Stage 1 action.
    """
    checks = (
        np.isfinite(slope_pct) and slope_pct >= STAGE1_SLOPE_MIN,
        np.isfinite(rs) and rs >= STAGE1_RS_MIN,
        np.isfinite(ratio) and ratio <= STAGE1_CONTRACTION_MAX,
        np.isfinite(dryup) and dryup <= STAGE1_DRYUP_MAX,
        np.isfinite(close) and np.isfinite(ma_10w) and close > ma_10w,
    )
    return int(sum(bool(c) for c in checks))
