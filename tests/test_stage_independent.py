import numpy as np
import pandas as pd

from rs_stages.quant import classify_stage, ma_30w, ma_slope_pct


def _reference_ma(close: pd.Series, end: pd.Timestamp) -> float:
    t = close.index[close.index <= end][-1]
    start = t - pd.Timedelta(weeks=30)
    window = close.loc[(close.index >= start) & (close.index <= t)]
    return float(window.mean())


def test_30w_ma_matches_independent_calendar_window():
    idx = pd.date_range("2025-01-01", "2026-08-01", freq="5D")
    close = pd.Series(np.sin(np.arange(len(idx)) / 9.0) * 20 + 100, index=idx)
    end = idx[-1]
    expected = _reference_ma(close, end)
    assert np.isclose(ma_30w(close, end), expected, rtol=0, atol=1e-12)


def test_stage_slope_uses_ten_observations_back_independently():
    idx = pd.date_range("2026-01-01", periods=20, freq="D")
    ma = pd.Series(np.linspace(90.0, 109.0, len(idx)), index=idx)
    end = idx[-1]
    expected = (ma.iloc[-1] / ma.iloc[-11] - 1.0) * 100.0
    assert np.isclose(ma_slope_pct(ma, end, sessions=10), expected, rtol=0, atol=1e-12)


def test_stage_boundaries_match_locked_boolean_definition():
    cases = [
        (101.0, 100.0, 0.01, "Stage 2 — Advancing"),
        (101.0, 100.0, 0.0, "Stage 3 — Topping"),
        (99.0, 100.0, 0.0, "Stage 4 — Declining"),
        (99.0, 100.0, 0.01, "Stage 1 — Basing"),
    ]
    for close, ma, slope, expected in cases:
        assert classify_stage(close, ma, slope) == expected
