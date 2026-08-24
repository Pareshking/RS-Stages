import numpy as np
import pandas as pd

from rs_stages.data import DecisionSnapshot
from rs_stages.screener import (
    TREND_COLUMNS,
    TREND_HEALTH_CONDITIONS,
    analyze_universe,
    analyze_universe_with_trend,
)


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
    # 15 business sessions: deliberately below the locked 20-session minimum.
    result = analyze_universe({"AAA": _snapshot(100.0, start="2025-12-15", end="2026-01-02")})
    assert np.isnan(result.loc["AAA", "AvgValue20"])
    assert not bool(result.loc["AAA", "Liquid_UI_Filter"])


def _ohlcv_snapshot(seed: float, start="2024-01-01", end="2026-01-02") -> DecisionSnapshot:
    """Snapshot including Low, as the production yfinance path always supplies."""
    idx = pd.bdate_range(start, end)
    close = pd.Series(seed + np.arange(len(idx), dtype=float), index=idx)
    frame = pd.DataFrame(
        {
            "Close": close,
            "High": close + 2.0,
            "Low": close - 3.0,
            "Volume": pd.Series(1_000_000.0, index=idx),
        }
    )
    return DecisionSnapshot(pd.Timestamp("2026-01-05"), pd.Timestamp(end), frame)


def test_close_is_the_latest_completed_session_not_the_decision_session():
    snap = _ohlcv_snapshot(100.0)
    result = analyze_universe({"AAA": snap})
    expected = float(snap.data["Close"].loc[pd.Timestamp("2026-01-02")])
    assert result.loc["AAA", "Close"] == expected
    assert result.loc["AAA", "Date"] == pd.Timestamp("2026-01-02")


def test_ma_10w_is_present_and_shorter_window_leads_on_a_rising_series():
    result = analyze_universe({"AAA": _ohlcv_snapshot(100.0)})
    row = result.loc["AAA"]
    assert np.isfinite(row["MA_10W"])
    # Strictly rising closes: the 10-week average must sit above the 30-week one.
    assert row["MA_10W"] > row["MA_30W"]
    assert bool(row["MA10W_Above_MA30W"])
    assert bool(row["Above_MA_10W"])


def test_low_52w_is_explicit_insufficiency_when_provider_frame_has_no_low():
    without_low = analyze_universe({"AAA": _snapshot(100.0)})
    assert np.isnan(without_low.loc["AAA", "Low_52W"])
    with_low = analyze_universe({"AAA": _ohlcv_snapshot(100.0)})
    assert np.isfinite(with_low.loc["AAA", "Low_52W"])
    assert with_low.loc["AAA", "Low_52W"] < with_low.loc["AAA", "High_52W"]


def test_ext_pct_matches_the_locked_extension_definition():
    result = analyze_universe({"AAA": _ohlcv_snapshot(100.0)})
    row = result.loc["AAA"]
    expected = (row["Close"] / row["MA_30W"] - 1.0) * 100.0
    assert np.isclose(row["Ext_Pct"], expected, rtol=0, atol=1e-12)
    # Away from the 20% boundary the displayed number and the locked boolean agree.
    assert bool(row["Extended_20Pct"]) == bool(row["Close"] > 1.20 * row["MA_30W"])


def test_pct_from_52w_high_is_zero_or_negative():
    result = analyze_universe({"AAA": _ohlcv_snapshot(100.0)})
    assert result.loc["AAA", "Pct_From_52W_High"] <= 0.0


def test_trend_health_equals_the_count_of_its_five_conditions():
    result = analyze_universe({"AAA": _ohlcv_snapshot(100.0), "BBB": _ohlcv_snapshot(50.0)})
    for symbol in ("AAA", "BBB"):
        row = result.loc[symbol]
        expected = sum(bool(row[field]) for field, _ in TREND_HEALTH_CONDITIONS)
        assert row["Trend_Health"] == expected
        assert 0 <= row["Trend_Health"] <= 5


def test_trend_collection_does_not_change_any_row_value():
    snapshots = {"AAA": _ohlcv_snapshot(100.0), "BBB": _ohlcv_snapshot(50.0)}
    plain = analyze_universe(snapshots)
    with_trend, trends = analyze_universe_with_trend(snapshots, trend_sessions=120)
    pd.testing.assert_frame_equal(plain, with_trend)
    assert set(trends) == {"AAA", "BBB"}
    for symbol, frame in trends.items():
        assert list(frame.columns) == list(TREND_COLUMNS)
        assert len(frame) == 120
        assert frame.index.max() == pd.Timestamp("2026-01-02")
        # The last trend Close must be the same observation the row reports.
        assert frame["Close"].iloc[-1] == plain.loc[symbol, "Close"]
        assert np.isclose(frame["MA_30W"].iloc[-1], plain.loc[symbol, "MA_30W"], rtol=0, atol=1e-12)
        assert np.isclose(frame["MA_10W"].iloc[-1], plain.loc[symbol, "MA_10W"], rtol=0, atol=1e-12)
