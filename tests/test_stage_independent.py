import numpy as np
import pandas as pd
import pytest

from rs_stages.quant import classify_stage, ma_30w, ma_slope_pct


def _reference_ma(close: pd.Series, end: pd.Timestamp) -> float:
    t = close.index[close.index <= end][-1]
    start = t - pd.Timedelta(weeks=30)
    window = close.loc[(close.index >= start) & (close.index <= t)]
    return float(window.mean())


def _reference_stage(close: float, ma: float, slope: float) -> str:
    if not all(np.isfinite(float(value)) for value in (close, ma, slope)):
        raise ValueError("missing stage input")
    above = close > ma
    rising = slope > 0.0
    if above and rising:
        return "Stage 2 — Advancing"
    if above and not rising:
        return "Stage 3 — Topping"
    if not above and not rising:
        return "Stage 4 — Declining"
    return "Stage 1 — Basing"


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


def test_stage_truth_table_including_strict_boundaries():
    cases = [
        (101.0, 100.0, 0.01),
        (101.0, 100.0, 0.0),
        (99.0, 100.0, 0.0),
        (99.0, 100.0, 0.01),
        (100.0, 100.0, 1.0),
        (100.0, 100.0, 0.0),
        (100.0, 100.0, -1.0),
        (101.0, 101.0, 1.0),
        (101.0, 101.0, 0.0),
        (99.0, 99.0, -1.0),
        (99.0, 99.0, 0.0),
    ]
    for close, ma, slope in cases:
        assert classify_stage(close, ma, slope) == _reference_stage(close, ma, slope)


@pytest.mark.parametrize(
    "close,ma,slope",
    [
        (np.nan, 100.0, 1.0),
        (100.0, np.nan, 1.0),
        (100.0, 100.0, np.nan),
        (np.inf, 100.0, 1.0),
        (100.0, -np.inf, 1.0),
    ],
)
def test_stage_rejects_missing_or_nonfinite_inputs(close, ma, slope):
    with pytest.raises(ValueError, match="finite"):
        classify_stage(close, ma, slope)
