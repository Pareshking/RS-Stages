"""Transitions must be genuine set differences, never inferred state."""
import numpy as np
import pandas as pd

from rs_stages.movers import rs_movers, stage_changes, summary, transitions


def _snapshot(stage, breakout, above10, action, rs) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Symbol": ["A", "B", "C"],
            "Stage": stage,
            "Breakout": breakout,
            "Above_MA_10W": above10,
            "Action": action,
            "RS_Score": rs,
            "Ext_Pct": [5.0, 10.0, -2.0],
            "Industry": ["IT", "Banks", "Pharma"],
        }
    )


PREVIOUS = _snapshot(
    ["Stage 1 — Basing", "Stage 2 — Advancing", "Stage 2 — Advancing"],
    [False, False, True],
    [False, True, True],
    ["WATCH", "HOLD", "BUY"],
    [40.0, 85.0, 90.0],
)

CURRENT = _snapshot(
    ["Stage 2 — Advancing", "Stage 3 — Topping", "Stage 2 — Advancing"],
    [True, False, True],
    [True, False, True],
    ["BUY", "REDUCE", "BUY"],
    [62.0, 80.0, 91.0],
)


def test_stage_changes_report_both_endpoints():
    got = stage_changes(CURRENT, PREVIOUS).set_index("Symbol")
    assert set(got.index) == {"A", "B"}
    assert got.loc["A", "Stage_From"] == "Stage 1"
    assert got.loc["A", "Stage_To"] == "Stage 2"
    assert got.loc["B", "Stage_From"] == "Stage 2"
    assert got.loc["B", "Stage_To"] == "Stage 3"


def test_transition_groups_contain_only_symbols_that_actually_changed():
    groups = transitions(CURRENT, PREVIOUS)
    assert list(groups["Entered Stage 2 — Advancing"]["rows"]["Symbol"]) == ["A"]
    assert list(groups["Left Stage 2 — Advancing"]["rows"]["Symbol"]) == ["B"]
    assert list(groups["New breakout setup"]["rows"]["Symbol"]) == ["A"]
    assert list(groups["Reclaimed the 10-week line"]["rows"]["Symbol"]) == ["A"]
    assert list(groups["Lost the 10-week line"]["rows"]["Symbol"]) == ["B"]
    # C changed nothing and must not appear anywhere.
    for payload in groups.values():
        assert "C" not in set(payload["rows"]["Symbol"])


def test_empty_groups_are_omitted_rather_than_rendered_empty():
    groups = transitions(PREVIOUS, PREVIOUS)
    assert groups == {}
    assert summary(PREVIOUS, PREVIOUS) == {}


def test_a_field_missing_from_either_snapshot_produces_no_transition():
    """A field's arrival in the pipeline must not be reported as a market change."""
    previous = PREVIOUS.drop(columns=["Above_MA_10W"])
    groups = transitions(CURRENT, previous)
    assert "Reclaimed the 10-week line" not in groups
    assert "Lost the 10-week line" not in groups
    # Fields present on both sides still diff normally.
    assert "New breakout setup" in groups


def test_symbols_absent_from_either_snapshot_are_ignored():
    current = pd.concat(
        [CURRENT, _snapshot(["Stage 2 — Advancing"] * 3, [True] * 3, [True] * 3, ["BUY"] * 3, [70.0] * 3).head(1).assign(Symbol="NEW")],
        ignore_index=True,
    )
    groups = transitions(current, PREVIOUS)
    for payload in groups.values():
        assert "NEW" not in set(payload["rows"]["Symbol"])


def test_action_changes_carry_both_labels():
    rows = transitions(CURRENT, PREVIOUS)["Action changed"]["rows"].set_index("Symbol")
    assert set(rows.index) == {"A", "B"}
    assert rows.loc["A", "Action_From"] == "WATCH"
    assert rows.loc["A", "Action_To"] == "BUY"
    assert rows.loc["B", "Action_From"] == "HOLD"
    assert rows.loc["B", "Action_To"] == "REDUCE"


def test_rs_movers_rank_by_absolute_change_and_report_the_signed_delta():
    got = rs_movers(CURRENT, PREVIOUS, count=3).set_index("Symbol")
    assert np.isclose(got.loc["A", "RS_Change"], 22.0)
    assert np.isclose(got.loc["B", "RS_Change"], -5.0)
    assert np.isclose(got.loc["C", "RS_Change"], 1.0)
    assert np.isclose(got.loc["A", "RS_Previous"], 40.0)
    # Largest absolute mover is retained when the list is truncated.
    assert "A" in set(rs_movers(CURRENT, PREVIOUS, count=1)["Symbol"])


def test_rs_movers_ignore_symbols_without_a_rank_on_both_dates():
    previous = PREVIOUS.copy()
    previous.loc[previous["Symbol"] == "A", "RS_Score"] = np.nan
    got = rs_movers(CURRENT, previous, count=5)
    assert "A" not in set(got["Symbol"])
