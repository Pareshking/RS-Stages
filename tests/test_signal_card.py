"""The Signal Card must reproduce the guide's worked examples exactly.

Section 7 of the NSE Signal Interpretation Guide states five worked examples
with their expected readings. Those are the acceptance criteria: if the card
disagrees with the guide's own example, the card is wrong.
"""
import pandas as pd
import pytest

from rs_stages.signal_card import (
    caution_note,
    conflict_note,
    extension_band,
    rs_percentile_text,
    signal_rows,
    source_line,
    volume_state,
    wait_note,
)


def _row(**kw):
    base = dict(
        Stage="Stage 2 — Advancing", RS_Score=99.0, Volume_Ratio=14.4, U_D=16.5,
        Ext_Pct=89.0, MA_30W_Slope_10S_Pct=0.8, Near_52W_High=True,
        Extended_20Pct=True, Below_50DMA=False,
    )
    base.update(kw)
    return pd.Series(base)


# --- the guide's worked examples --------------------------------------------

def test_welcorp_reads_as_the_guide_states():
    """WELCORP: Stage 2, RS 99 top 1%, vol 14.4x, U/D 16.5, extension +89%."""
    row = _row()
    assert rs_percentile_text(row["RS_Score"]) == "RS 99 — top 1%"
    assert volume_state(row) == "strong accumulation"
    assert extension_band(89.0)[0] == "very extended"
    # The guide's caution: valid signal, poor entry, size small or wait.
    caution = caution_note(row)
    assert "very far above" in caution and "size very small" in caution


def test_atherenerg_is_top_2_percent():
    assert rs_percentile_text(98.0) == "RS 98 — top 2%"


def test_hfcl_volume_fails_the_breakout_threshold_but_ud_confirms():
    """HFCL: vol 0.52x is not met; U/D 2.01 is accumulating."""
    rows = {r.signal: r for r in signal_rows(_row(Volume_Ratio=0.52, U_D=2.01, Ext_Pct=66.0))}
    assert rows["Volume ratio"].status == "unmet"
    assert rows["U/D ratio"].status == "met"
    assert extension_band(66.0)[0] == "extended"


def test_hscl_heavy_distribution_conflicts_with_stage_2():
    """HSCL: Stage 2 price, RS 86, U/D 0.34 — volume contradicts the stage."""
    row = _row(RS_Score=86.0, Volume_Ratio=1.66, U_D=0.34, Ext_Pct=12.0)
    assert volume_state(row) == "heavy distribution"
    note = conflict_note(row)
    assert "contradicts" in note and "Stage 3 may be forming" in note
    rows = {r.signal: r for r in signal_rows(row)}
    assert rows["U/D ratio"].status == "caution"
    # +12% is the guide's "normal range".
    assert extension_band(12.0)[0] == "normal range"


def test_reliance_stage_4_with_rs_99_is_the_conflict_case():
    """RELIANCE: Stage 4 + RS 99 — 'least bad, not good'. Stage overrides RS."""
    row = _row(Stage="Stage 4 — Declining", RS_Score=99.0, Ext_Pct=-2.6,
               MA_30W_Slope_10S_Pct=-0.845)
    note = conflict_note(row)
    assert "least bad, not good" in note
    assert "Stage overrides RS" in note
    assert "never hold Stage 4" in source_line(row)
    rows = {r.signal: r for r in signal_rows(row)}
    assert rows["Stage"].status == "unmet"
    assert rows["30-week slope"].status == "unmet"


# --- the case that prompted this work ---------------------------------------

def test_a_hairline_crossing_is_called_out_not_dressed_up():
    """JSWCEMENT crossed its line by 0.06% while lagging at RS 37."""
    row = _row(Stage="Stage 2 — Advancing", RS_Score=37.0, U_D=1.0,
               Volume_Ratio=0.9, Ext_Pct=0.0578, Extended_20Pct=False)
    band, tone = extension_band(row["Ext_Pct"])
    assert band == "at the line"
    assert tone == "warn"
    assert "sitting on the 30-week line" in caution_note(row)
    note = conflict_note(row)
    assert "by a hair" in note
    assert "lags most of the universe" in note
    assert rs_percentile_text(37.0) == "RS 37 — lagging"


def test_a_wait_states_the_exact_gap():
    row = _row(RS_Score=75.0, Ext_Pct=5.0, Extended_20Pct=False)
    note = wait_note(row, "WAIT")
    assert "needs 80" in note and "short by 5" in note


def test_a_wait_names_every_missing_condition():
    row = _row(Stage="Stage 1 — Basing", RS_Score=60.0, Ext_Pct=25.0,
               Extended_20Pct=True, Below_50DMA=True)
    note = wait_note(row, "WAIT")
    assert "Stage 1" in note and "needs 80" in note
    assert "extended beyond 20%" in note and "below the 50-session average" in note


def test_no_wait_note_when_the_action_is_not_waiting():
    assert wait_note(_row(), "BUY★") == ""


def test_no_conflict_note_when_the_signals_agree():
    assert conflict_note(_row()) == ""


# --- robustness --------------------------------------------------------------

@pytest.mark.parametrize("field", ["RS_Score", "Volume_Ratio", "U_D", "Ext_Pct",
                                   "MA_30W_Slope_10S_Pct"])
def test_a_missing_input_never_becomes_a_met_condition(field):
    rows = {r.signal: r for r in signal_rows(_row(**{field: float("nan")}))}
    assert all(r.status != "met" or r.value != "—" for r in rows.values())


def test_unavailable_values_render_as_a_dash_not_a_zero():
    rows = {r.signal: r for r in signal_rows(_row(RS_Score=float("nan")))}
    assert rows["Relative strength"].value == "—"
    assert rs_percentile_text(float("nan")) == "RS unavailable"


def test_infinite_ud_is_shown_as_infinity_not_a_crash():
    rows = {r.signal: r for r in signal_rows(_row(U_D=float("inf")))}
    assert rows["U/D ratio"].value == "∞"


def test_every_source_the_spec_claims_is_actually_cited():
    """§1 lists three authorities; the Stock page must be able to cite all three.

    Weinstein and O'Neil were cited from the start. v2.2 added Minervini to the
    authority hierarchy and 25 fields derived from him, but the per-stock source
    line never mentioned him — a stock could show contraction evidence while
    attributing the reading to two authors who never described it.
    """
    row = {
        "Stage": "Stage 1 — Basing",
        "RS_Score": 62.0,
        "VCP_Setup": True,
        "Trend_Template_Pass": True,
        "RS_Line_NH_Before_Price": True,
    }
    line = source_line(row)
    assert "Weinstein" in line
    assert "O'Neil" in line
    assert "Minervini" in line
    # The template's thresholds are transcribed, and the card must say so.
    assert "provisional" in line


def test_a_pre_v22_row_cites_only_what_it_carries():
    """Attribution follows the evidence, never the other way round."""
    row = {
        "Stage": "Stage 2 — Advancing",
        "RS_Score": 88.0,
        "Breakout_Confirmed": True,
    }
    line = source_line(row)
    assert "Weinstein" in line and "O'Neil" in line
    assert "Minervini" not in line, "must not claim a reading the snapshot lacks"


def test_contraction_evidence_alone_does_not_claim_the_template():
    """The two Minervini citations are separate claims and must stay separate."""
    row = {"Stage": "Stage 1 — Basing", "RS_Score": 55.0, "VCP_Setup": True}
    line = source_line(row)
    assert "contracting range" in line
    assert "trend-template" not in line
