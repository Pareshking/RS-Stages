import numpy as np
import pandas as pd

from rs_stages.quant import (
    breakout,
    breakout_confirmed,
    calendar_asof,
    classify_stage,
    high_52w,
    ma_slope_pct,
    near_52w_high,
    rs_blend,
    rs_score,
    rs_returns,
    up_down_ratio,
    volume_ratio,
)


def test_calendar_asof_uses_previous_session():
    idx = pd.DatetimeIndex(["2026-01-02", "2026-01-05", "2026-01-06"])
    assert calendar_asof(idx, pd.Timestamp("2026-01-04")) == pd.Timestamp("2026-01-02")


def test_rs_blend_exact_weights():
    r = {3: 0.10, 6: 0.20, 9: 0.30, 12: 0.40}
    assert rs_blend(r) == 0.20


def test_rs_score_min_percentile_and_tie():
    blend = pd.Series([0.10, 0.10, 0.20], index=["A", "B", "C"])
    got = rs_score(blend)
    assert got["A"] == got["B"] == 66.0
    assert got["C"] == 99.0


def test_rs_returns_use_calendar_month_asof():
    dates = pd.date_range("2025-01-01", "2026-01-01", freq="7D")
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


def test_near_52w_high_boundary():
    assert near_52w_high(97, 100)
    assert not near_52w_high(96.99, 100)


def test_52w_requires_200_sessions():
    idx = pd.date_range("2025-01-01", periods=199, freq="D")
    high = pd.Series(100.0, index=idx)
    try:
        high_52w(high, idx[-1])
    except ValueError:
        pass
    else:
        raise AssertionError("52W high must require 200 valid sessions")


def test_volume_ratio_excludes_latest_volume_from_baseline():
    idx = pd.date_range("2026-01-01", periods=51, freq="D")
    volume = pd.Series([100.0] * 50 + [1000.0], index=idx)
    assert np.isclose(volume_ratio(volume, idx[-1]), 10.0)


def test_ud_includes_latest_completed_session():
    idx = pd.date_range("2026-01-01", periods=21, freq="D")
    close = pd.Series([100.0] + [101.0 if i % 2 else 99.0 for i in range(1, 21)], index=idx)
    volume = pd.Series(100.0, index=idx)
    got = up_down_ratio(close, volume, idx[-1])
    assert np.isclose(got, 10.0 / 10.0)


def test_ud_zero_down_volume_is_infinite():
    idx = pd.date_range("2026-01-01", periods=21, freq="D")
    close = pd.Series(np.arange(21, dtype=float), index=idx)
    volume = pd.Series(100.0, index=idx)
    assert np.isinf(up_down_ratio(close, volume, idx[-1]))


def test_breakout_is_distinct_from_confirmation():
    assert breakout("Stage 2 — Advancing", 99, 100, 2.0)
    assert not breakout_confirmed("Stage 2 — Advancing", 99, 100, 2.0, 1.2)
    assert breakout_confirmed("Stage 2 — Advancing", 99, 100, 2.0, 1.31)
