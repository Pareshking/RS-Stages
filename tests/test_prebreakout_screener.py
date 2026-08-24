"""v2.2 fields as published by the screener.

The quant primitives are tested against independent reimplementations in
tests/test_prebreakout_v22.py. What matters here is different: that the new
fields reach the snapshot, that each degrades on its own rather than taking the
row down with it, and above all that adding them moved nothing that was already
locked.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rs_stages.data import build_decision_snapshot
from rs_stages.screener import analyze_universe

DECISION = pd.Timestamp("2026-08-24")

V22_COLUMNS = [
    "SMA_150", "SMA_200", "SMA_200_Rising",
    "ATR_Pct", "VCP_Contractions", "Contraction_Ratio", "Volume_DryUp",
    "VCP_Setup", "VCP_Pivot", "Pct_To_Pivot",
    "RS_Line", "RS_Line_High_52W", "RS_Line_At_High", "RS_Line_NH_Before_Price",
    "TT1_Above_150_200", "TT2_150_Above_200", "TT3_200_Rising",
    "TT4_50_Above_150_200", "TT5_Above_50", "TT6_Above_52W_Low",
    "TT7_Near_52W_High", "TT8_RS",
    "Trend_Template_Score", "Trend_Template_Pass", "Stage1_Readiness",
]

#: Every field the v2.1 snapshot published. None of these may move.
V21_COLUMNS = [
    "Close", "R3M", "R6M", "R9M", "R12M", "RS_Blend", "MA_30W",
    "MA_30W_Slope_10S_Pct", "Stage", "MA_10W", "High_52W", "Near_52W_High",
    "Low_52W", "Volume_Ratio", "U_D", "AvgValue20", "SMA_50", "Below_50DMA",
    "Ext_Pct", "Extended_20Pct", "Pct_From_52W_High", "Above_MA_30W",
    "Above_MA_10W", "MA10W_Above_MA30W", "MA_30W_Rising", "Distribution",
    "Heavy_Distribution", "Breakout", "Breakout_Confirmed", "RS_Score",
    "Liquid_UI_Filter", "RS_Not_Lagging", "Trend_Health",
]


def _history(seed: int, periods: int = 620) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=pd.Timestamp("2026-08-21"), periods=periods)
    close = pd.Series(200.0 + rng.normal(0.35, 3.0, periods).cumsum(), index=idx).clip(lower=5.0)
    return pd.DataFrame(
        {
            "Close": close,
            "High": close * 1.012,
            "Low": close * 0.988,
            "Volume": pd.Series(rng.uniform(4e5, 3e6, periods), index=idx),
        }
    )


@pytest.fixture(scope="module")
def histories() -> dict[str, pd.DataFrame]:
    return {f"SYM{i}": _history(seed=i) for i in range(6)}


@pytest.fixture(scope="module")
def snapshots(histories) -> dict:
    return {s: build_decision_snapshot(h, DECISION) for s, h in histories.items()}


@pytest.fixture(scope="module")
def benchmark(histories) -> pd.Series:
    """A stand-in index on the same calendar, as ^CRSLDX would be."""
    frame = histories["SYM0"]
    rng = np.random.default_rng(99)
    return pd.Series(
        20000.0 + rng.normal(2.0, 60.0, len(frame)).cumsum(), index=frame.index
    ).clip(lower=1000.0)


def test_every_v22_field_reaches_the_snapshot(snapshots, benchmark):
    result = analyze_universe(snapshots, benchmark=benchmark)
    missing = [c for c in V22_COLUMNS if c not in result.columns]
    assert not missing, f"v2.2 fields absent from the snapshot: {missing}"


def test_adding_v22_moved_nothing_that_was_locked(snapshots, benchmark):
    """The whole point of an additive revision.

    Threading a benchmark through the screener must not perturb a single locked
    value. Compared with and without, because the benchmark is the one genuinely
    new input to the calculation path.
    """
    without = analyze_universe(snapshots)
    with_bench = analyze_universe(snapshots, benchmark=benchmark)
    for column in V21_COLUMNS:
        assert column in without.columns, f"{column} vanished"
        left, right = without[column], with_bench[column]
        if pd.api.types.is_numeric_dtype(left) and not pd.api.types.is_bool_dtype(left):
            assert np.allclose(
                left.astype(float), right.astype(float), rtol=0, atol=0, equal_nan=True
            ), f"{column} changed when the benchmark was supplied"
        else:
            assert left.equals(right), f"{column} changed when the benchmark was supplied"


def test_without_a_benchmark_the_rs_line_is_unavailable_not_zero(snapshots):
    """A stock has no relative strength against nothing; it must not read as 0."""
    result = analyze_universe(snapshots)
    assert result["RS_Line"].isna().all()
    assert result["RS_Line_High_52W"].isna().all()
    assert not result["RS_Line_At_High"].any()
    assert not result["RS_Line_NH_Before_Price"].any()
    # And the rest of v2.2 is unaffected by the benchmark's absence.
    assert result["Contraction_Ratio"].notna().any()
    assert result["Trend_Template_Score"].between(0, 8).all()


def test_the_rs_line_is_computed_when_a_benchmark_is_supplied(snapshots, benchmark):
    result = analyze_universe(snapshots, benchmark=benchmark)
    assert result["RS_Line"].notna().all()
    assert result["RS_Line_High_52W"].notna().all()
    # The line can never exceed its own trailing maximum.
    assert (result["RS_Line"] <= result["RS_Line_High_52W"] * 1.0000001).all()


def test_the_divergence_implies_both_of_its_parts(snapshots, benchmark):
    """§4.1 — it is an ordering of two published facts, not a third fact."""
    result = analyze_universe(snapshots, benchmark=benchmark)
    for _, row in result.iterrows():
        if bool(row["RS_Line_NH_Before_Price"]):
            assert bool(row["RS_Line_At_High"])
            assert row["Pct_From_52W_High"] <= -5.0


def test_trend_template_score_equals_its_own_criteria(snapshots, benchmark):
    """The count must be derived from the booleans, not tracked separately."""
    result = analyze_universe(snapshots, benchmark=benchmark)
    criteria = [c for c in V22_COLUMNS if c.startswith("TT")]
    assert len(criteria) == 8
    recomputed = sum(result[c].astype(bool).astype(int) for c in criteria)
    assert (recomputed == result["Trend_Template_Score"]).all()
    assert (result["Trend_Template_Pass"] == (result["Trend_Template_Score"] == 8)).all()


def test_readiness_is_defined_for_stage_1_and_unavailable_elsewhere(snapshots, benchmark):
    """§11.1 — zero would read as 'a bad base' for a stock that has no base."""
    result = analyze_universe(snapshots, benchmark=benchmark)
    stage_1 = result["Stage"].map(lambda v: str(v).startswith("Stage 1"))
    assert result.loc[~stage_1, "Stage1_Readiness"].isna().all()
    scored = result.loc[stage_1, "Stage1_Readiness"].dropna()
    assert scored.between(0, 5).all()


def test_a_frame_without_low_loses_only_what_depends_on_low(histories):
    """§9.1 keeps Low optional; contraction and ATR need it, the template does not."""
    stripped = {
        s: build_decision_snapshot(h.drop(columns=["Low"]), DECISION)
        for s, h in histories.items()
    }
    result = analyze_universe(stripped)
    assert result["ATR_Pct"].isna().all()
    assert result["Contraction_Ratio"].isna().all()
    assert not result["VCP_Setup"].any()
    # Pivot needs only High, and the template needs neither.
    assert result["VCP_Pivot"].notna().any()
    assert result["Trend_Template_Score"].between(0, 8).all()
    assert result["SMA_200"].notna().any()


def test_short_history_publishes_insufficiency_rather_than_numbers(histories):
    """A symbol with 60 sessions cannot have a 200-session average."""
    short = {
        s: build_decision_snapshot(h.tail(60), DECISION) for s, h in histories.items()
    }
    result = analyze_universe(short)
    assert result["SMA_200"].isna().all()
    assert not result["SMA_200_Rising"].any()
    assert not result["TT1_Above_150_200"].any()
    assert not result["Trend_Template_Pass"].any()


def test_a_provider_row_without_a_close_is_not_the_information_boundary(histories):
    """§3 — an empty row is not a completed session.

    Yahoo publishes a dated row before its values are final. Adopting that row
    as the boundary shifts every calendar window one session late, so the
    30-week average, its slope, Stage and every v2.2 field disagree with any
    recalculation that dropped the empty row first. This is what failed the
    first scheduled audit run.
    """
    frame = histories["SYM0"].copy()
    frame.loc[frame.index[-1], ["Close", "High", "Low", "Volume"]] = np.nan
    snapshot = build_decision_snapshot(frame, DECISION)

    # The boundary steps back to the last session carrying a Close.
    assert snapshot.latest_completed_session == frame.index[-2]
    assert pd.notna(snapshot.data["Close"].loc[snapshot.latest_completed_session])

    # And the published row is computable rather than NaN.
    result = analyze_universe({"SYM0": snapshot})
    assert pd.notna(result.loc["SYM0", "MA_30W"])
    assert result.loc["SYM0", "Stage"] is not None
    assert str(result.loc["SYM0", "Stage"]).startswith("Stage")


def test_interior_empty_rows_do_not_move_the_boundary(histories):
    """Only the boundary is chosen this way; interior history is untouched."""
    frame = histories["SYM1"].copy()
    frame.loc[frame.index[-40], ["Close", "High", "Low", "Volume"]] = np.nan
    snapshot = build_decision_snapshot(frame, DECISION)
    assert snapshot.latest_completed_session == frame.index[-1]
    # A window mean skips the NaN, so the average matches one computed from a
    # frame that never carried the row at all.
    without = build_decision_snapshot(frame.dropna(subset=["Close"]), DECISION)
    a = analyze_universe({"S": snapshot}).loc["S", "MA_30W"]
    b = analyze_universe({"S": without}).loc["S", "MA_30W"]
    assert np.isclose(a, b, rtol=0, atol=1e-12)
