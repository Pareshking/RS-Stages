import numpy as np
import pandas as pd
import pytest

from rs_stages.quant import (
    breakout,
    breakout_confirmed,
    calendar_asof,
    classify_stage,
    high_52w,
    ma_30w,
    ma_slope_pct,
    near_52w_high,
    rs_blend,
    rs_score,
    rs_returns,
    ud_classification,
    up_down_ratio,
    volume_ratio,
)


def test_calendar_asof_uses_previous_session():
    idx = pd.DatetimeIndex(["2026-01-02", "2026-01-05", "2026-01-06"])
    assert calendar_asof(idx, pd.Timestamp("2026-01-04")) == pd.Timestamp("2026-01-02")


def test_rs_blend_exact_weights():
    r = {3: 0.10, 6: 0.20, 9: 0.30, 12: 0.40}
    assert np.isclose(rs_blend(r), 0.22)


def test_rs_score_min_percentile_and_tie():
    blend = pd.Series([0.10, 0.10, 0.20], index=["A", "B", "C"])
    got = rs_score(blend)
    assert got["A"] == got["B"] == 34.0
    assert got["C"] == 99.0


def test_rs_score_preserves_nan():
    got = rs_score(pd.Series([0.1, np.nan, 0.2], index=["A", "B", "C"]))
    assert np.isnan(got["B"])
    assert got["C"] == 99.0


def test_rs_returns_use_calendar_month_asof():
    dates = pd.date_range("2024-01-01", "2026-01-01", freq="7D")
    close = pd.Series(np.arange(len(dates), dtype=float) + 100.0, index=dates)
    latest = dates[-1]
    got = rs_returns(close, latest)
    for m in (3, 6, 9, 12):
        ref = calendar_asof(close.index, latest - pd.DateOffset(months=m))
        expected = close.loc[latest] / close.loc[ref] - 1.0
        assert np.isclose(got[m], expected)


def test_stage_boundaries():
    assert classify_stage(110, 100, 1) == "Stage 2 — Advancing"
    assert classify_stage(110, 100, 0) == "Stage 3 — Topping"
    assert classify_stage(90, 100, 0) == "Stage 4 — Declining"
    assert classify_stage(90, 100, 1) == "Stage 1 — Basing"


def test_slope_is_ten_sessions():
    idx = pd.date_range("2026-01-01", periods=11, freq="D")
    ma = pd.Series(np.linspace(100, 110, 11), index=idx)
    assert np.isclose(ma_slope_pct(ma, idx[-1], 10), 10.0)


def test_30w_ma_uses_calendar_start_asof_session():
    idx = pd.date_range("2025-01-01", "2025-07-30", freq="7D")
    close = pd.Series(100.0, index=idx)
    assert ma_30w(close, idx[-1]) == 100.0


def test_30w_ma_requires_history_before_calendar_window():
    idx = pd.date_range("2025-01-01", "2025-01-29", freq="7D")
    close = pd.Series(100.0, index=idx)
    with pytest.raises(ValueError):
        ma_30w(close, idx[-1])


def test_30w_ma_mean_over_complete_window():
    end = pd.Timestamp("2026-07-31")
    start = end - pd.Timedelta(weeks=30)
    idx = pd.date_range(start, end, freq="D")
    close = pd.Series(np.arange(len(idx), dtype=float), index=idx)
    expected = close.mean()
    assert np.isclose(ma_30w(close, end), expected)


def test_near_52w_high_boundary():
    assert near_52w_high(97, 100)
    assert not near_52w_high(96.99, 100)


def test_52w_requires_200_sessions():
    idx = pd.bdate_range("2025-01-01", periods=199)
    high = pd.Series(100.0, index=idx)
    with pytest.raises(ValueError):
        high_52w(high, idx[-1])


def test_52w_accepts_200_sessions_inside_complete_window():
    end = pd.Timestamp("2026-07-31")
    idx = pd.bdate_range(end - pd.Timedelta(weeks=52), end)
    high = pd.Series(100.0, index=idx)
    assert high_52w(high, end) == 100.0


def test_volume_ratio_excludes_latest_volume_from_baseline():
    idx = pd.date_range("2026-01-01", periods=51, freq="D")
    volume = pd.Series([100.0] * 50 + [1000.0], index=idx)
    assert np.isclose(volume_ratio(volume, idx[-1]), 10.0)


def test_ud_includes_latest_completed_session():
    idx = pd.date_range("2026-01-01", periods=21, freq="D")
    close = pd.Series([100.0] + [101.0 if i % 2 else 99.0 for i in range(1, 21)], index=idx)
    volume = pd.Series(100.0, index=idx)
    assert np.isclose(up_down_ratio(close, volume, idx[-1]), 1.0)


def test_ud_excludes_upcoming_decision_session():
    idx = pd.date_range("2026-01-01", periods=22, freq="D")
    close = pd.Series([100.0] + [101.0] * 21, index=idx)
    volume = pd.Series(100.0, index=idx)
    assert np.isinf(up_down_ratio(close, volume, idx[-2]))


def test_ud_zero_down_volume_is_infinite():
    idx = pd.date_range("2026-01-01", periods=21, freq="D")
    close = pd.Series(np.arange(21, dtype=float), index=idx)
    volume = pd.Series(100.0, index=idx)
    assert np.isinf(up_down_ratio(close, volume, idx[-1]))


def test_ud_unchanged_close_is_neither():
    idx = pd.date_range("2026-01-01", periods=21, freq="D")
    close = pd.Series(100.0, index=idx)
    volume = pd.Series(100.0, index=idx)
    assert np.isnan(up_down_ratio(close, volume, idx[-1]))


def test_ud_threshold_precedence():
    assert ud_classification(0.59) == "Heavy Distribution"
    assert ud_classification(0.60) == "Distribution Warning"
    assert ud_classification(0.70) == "Neutral"
    assert ud_classification(1.30) == "Neutral"
    assert ud_classification(1.31) == "Accumulating"
    assert ud_classification(1.50) == "Accumulating"
    assert ud_classification(1.51) == "Strong Accumulation"


def test_breakout_is_distinct_from_confirmation():
    assert breakout("Stage 2 — Advancing", 99, 100, 2.0)
    assert not breakout_confirmed("Stage 2 — Advancing", 99, 100, 2.0, 1.2)
    assert breakout_confirmed("Stage 2 — Advancing", 99, 100, 2.0, 1.31)
