"""Breadth aggregation must be a plain count of locked fields, with no invention."""
import numpy as np
import pandas as pd
import pytest

from rs_stages.market import (
    breadth_history_from_trends,
    breadth_snapshot,
    industry_leadership,
    regime_label,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Symbol": ["A", "B", "C", "D", "E"],
            "Stage": [
                "Stage 2 — Advancing",
                "Stage 2 — Advancing",
                "Stage 3 — Topping",
                "Stage 4 — Declining",
                "Stage 1 — Basing",
            ],
            "Above_MA_30W": [True, True, True, False, False],
            "Above_MA_10W": [True, True, False, False, True],
            "Near_52W_High": [True, False, False, False, False],
            "Breakout": [True, False, False, False, False],
            "Breakout_Confirmed": [True, False, False, False, False],
            "Distribution": [False, False, True, True, False],
            "RS_Score": [95.0, 82.0, 55.0, 12.0, np.nan],
            "R3M": [0.30, 0.20, 0.05, -0.25, 0.01],
            "Industry": ["IT", "IT", "Banks", "Banks", "Banks"],
        }
    )


def test_breadth_counts_are_exactly_the_locked_boolean_sums():
    got = breadth_snapshot(_frame())
    assert got["symbols"] == 5
    assert got["above_ma_30w"] == 3
    assert got["above_ma_10w"] == 3
    assert np.isclose(got["pct_above_ma_30w"], 60.0)
    assert got["near_52w_high"] == 1
    assert got["breakout_confirmed"] == 1
    assert got["distribution"] == 2
    assert got["stages"] == {"Stage 1": 1, "Stage 2": 2, "Stage 3": 1, "Stage 4": 1}
    # RS is a percentile rank; a missing rank is not a zero rank.
    assert got["valid_rs"] == 4
    assert got["rs_leaders"] == 2


def test_breadth_reports_missing_10w_field_rather_than_counting_zero():
    frame = _frame().drop(columns=["Above_MA_10W"])
    got = breadth_snapshot(frame)
    assert got["has_ma_10w"] is False
    assert got["above_ma_10w"] == 0


@pytest.mark.parametrize(
    "pct,expected",
    [(85.0, "Broad"), (60.0, "Broad"), (59.9, "Mixed"), (40.0, "Mixed"), (39.9, "Narrow"), (0.0, "Narrow")],
)
def test_regime_bands_are_closed_at_their_lower_bound(pct, expected):
    assert regime_label(pct)[0] == expected


def test_regime_is_unavailable_rather_than_guessed_when_breadth_is_nan():
    assert regime_label(float("nan"))[0] == "Unavailable"


def _trend(values, ma30, ma10, index) -> pd.DataFrame:
    return pd.DataFrame({"Close": values, "MA_10W": ma10, "MA_30W": ma30}, index=index)


def test_breadth_history_counts_each_session_independently():
    idx = pd.bdate_range("2026-01-01", periods=4)
    trends = {
        # Above the 30-week line on every session.
        "A": _trend([10, 11, 12, 13], [9, 9, 9, 9], [9, 9, 9, 9], idx),
        # Crosses above only on the final session.
        "B": _trend([8, 8, 8, 12], [10, 10, 10, 10], [10, 10, 10, 10], idx),
    }
    history = breadth_history_from_trends(trends, sessions=4)
    assert list(history["Date"]) == list(idx)
    assert list(history["Above_MA_30W"]) == [1, 1, 1, 2]
    assert list(history["Symbols"]) == [2, 2, 2, 2]
    assert np.isclose(history["Pct_Above_MA_30W"].iloc[-1], 100.0)
    assert np.isclose(history["Pct_Above_MA_30W"].iloc[0], 50.0)


def test_breadth_history_excludes_unmeasurable_symbols_from_the_denominator():
    idx = pd.bdate_range("2026-01-01", periods=3)
    trends = {
        "A": _trend([10, 11, 12], [9, 9, 9], [9, 9, 9], idx),
        # No valid 30-week average until the last session.
        "B": _trend([8, 8, 20], [np.nan, np.nan, 10], [np.nan, np.nan, 10], idx),
    }
    history = breadth_history_from_trends(trends, sessions=3)
    assert list(history["Symbols"]) == [1, 1, 2]
    assert np.isclose(history["Pct_Above_MA_30W"].iloc[0], 100.0)
    assert np.isclose(history["Pct_Above_MA_30W"].iloc[-1], 100.0)


def test_breadth_history_is_empty_without_trends():
    assert breadth_history_from_trends({}).empty


def test_industry_leadership_uses_median_rs_and_participation_share():
    got = industry_leadership(_frame()).set_index("Industry")
    assert got.loc["IT", "Stocks"] == 2
    assert np.isclose(got.loc["IT", "Median_RS"], 88.5)
    assert np.isclose(got.loc["IT", "Participation_Pct"], 100.0)
    # Banks: one of three above its own 30-week line.
    assert np.isclose(got.loc["Banks", "Participation_Pct"], 100.0 / 3.0)
    assert got.loc["Banks", "Stage2"] == 0
    # A missing RS must not drag the median toward zero.
    assert np.isclose(got.loc["Banks", "Median_RS"], 33.5)


def test_participation_is_read_from_stage_when_the_explicit_field_is_absent():
    """Stage 2 and Stage 3 are, by the locked definition, exactly 'above the line'."""
    frame = _frame().drop(columns=["Above_MA_30W"])
    got = breadth_snapshot(frame)
    assert got["above_ma_30w"] == 3  # two Stage 2 plus one Stage 3
    assert np.isclose(got["pct_above_ma_30w"], 60.0)
    assert got["above_ma_30w_source"] == "stage"
    assert got["regime"] == "Broad"


def test_participation_never_reports_zero_because_a_column_is_missing():
    """A pre-v2.1 snapshot must not be rendered as a market with no participation."""
    with_field = breadth_snapshot(_frame())
    without_field = breadth_snapshot(_frame().drop(columns=["Above_MA_30W"]))
    assert with_field["above_ma_30w"] == without_field["above_ma_30w"]
    assert with_field["regime"] == without_field["regime"]


def test_unclassifiable_stocks_leave_the_participation_denominator():
    frame = _frame()
    frame.loc[frame["Symbol"] == "E", "Stage"] = None
    got = breadth_snapshot(frame)
    assert got["symbols"] == 5
    assert got["classified"] == 4
    # Three of the four classifiable stocks are above their own 30-week line.
    assert np.isclose(got["pct_above_ma_30w"], 75.0)


def test_ten_week_participation_is_unavailable_not_zero_percent():
    got = breadth_snapshot(_frame().drop(columns=["Above_MA_10W"]))
    assert got["has_ma_10w"] is False
    assert np.isnan(got["pct_above_ma_10w"])


def test_industry_participation_uses_stage_when_the_field_is_absent():
    got = industry_leadership(_frame().drop(columns=["Above_MA_30W"])).set_index("Industry")
    assert np.isclose(got.loc["IT", "Participation_Pct"], 100.0)
    assert np.isclose(got.loc["Banks", "Participation_Pct"], 100.0 / 3.0)
