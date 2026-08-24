import numpy as np
import pandas as pd

from rs_stages.data import DecisionSnapshot
from rs_stages.screener import analyze_universe


def _snapshot(seed: float, start="2024-01-01", end="2026-01-02") -> DecisionSnapshot:
    idx = pd.bdate_range(start, end)
    close = pd.Series(seed + np.arange(len(idx), dtype=float), index=idx)
    high = close + 2.0
    volume = pd.Series(1_000_000.0, index=idx)
    frame = pd.DataFrame({"Close": close, "High": high, "Volume": volume})
    return DecisionSnapshot(pd.Timestamp("2026-01-05"), pd.Timestamp(end), frame)


def test_analyze_universe_produces_locked_fields_without_future_session():
    result = analyze_universe({"AAA": _snapshot(100.0), "BBB": _snapshot(50.0)})
    assert set(["RS_Blend", "RS_Score", "MA_30W", "MA_30W_Slope_10S_Pct", "High_52W", "Volume_Ratio", "U_D", "Breakout", "Breakout_Confirmed"]).issubset(result.columns)
    assert result.loc["AAA", "Date"] == pd.Timestamp("2026-01-02")
    assert result.loc["AAA", "Volume_Ratio"] == 1.0
    assert result.loc["AAA", "U_D"] == np.inf


def test_liquidity_is_ui_filter_not_rs_universe_filter():
    result = analyze_universe({"AAA": _snapshot(100.0), "BBB": _snapshot(50.0)})
    assert len(result) == 2
    assert result["RS_Score"].notna().all()
    assert result["Liquid_UI_Filter"].all()


def test_liquidity_requires_20_valid_completed_sessions():
    result = analyze_universe({"AAA": _snapshot(100.0, start="2025-12-01", end="2026-01-02")})
    assert np.isnan(result.loc["AAA", "AvgValue20"])
    assert not bool(result.loc["AAA", "Liquid_UI_Filter"])
