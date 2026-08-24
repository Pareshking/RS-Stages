"""The evidence block must colour states by meaning and never invent one."""
import math

from rs_stages.ui.components import STATE_TONES, evidence_card, evidence_grid, state_pill
from rs_stages.ui.theme import NEGATIVE, POSITIVE


def test_a_favourable_yes_and_a_warning_yes_are_not_the_same_colour():
    """A confirmed breakout and a distribution warning are both 'Yes'."""
    confirmed = state_pill(True, "good")
    warning = state_pill(True, "warn")
    assert POSITIVE in confirmed
    assert POSITIVE not in warning
    assert confirmed != warning


def test_absence_of_a_condition_is_neutral_not_alarming():
    absent = state_pill(False, "warn")
    colour, _ = STATE_TONES["neutral"]
    assert colour in absent
    assert "No" in absent


def test_heavy_distribution_reads_as_the_strongest_warning():
    assert NEGATIVE in state_pill(True, "bad")


def test_an_unavailable_condition_renders_a_dash_not_a_no():
    """Missing evidence must never be shown as a negative finding."""
    for value in (None, float("nan")):
        pill = state_pill(value)
        assert "—" in pill
        assert ">No<" not in pill


def test_custom_labels_are_escaped():
    assert "&lt;b&gt;" in state_pill(True, "good", yes="<b>")


def test_evidence_card_pairs_every_value_with_its_definition():
    html = evidence_card("Leadership", [("RS score", "98", "Percentile rank, 1-99.")])
    assert "Leadership" in html
    assert "RS score" in html
    assert "98" in html
    assert "Percentile rank, 1-99." in html


def test_evidence_card_escapes_labels_and_notes_but_keeps_value_markup():
    html = evidence_card("T", [("<lbl>", '<span class="ws-state">Yes</span>', "<note>")])
    assert "&lt;lbl&gt;" in html and "&lt;note&gt;" in html
    # The value is a rendered component, so its markup must survive.
    assert '<span class="ws-state">Yes</span>' in html


def test_evidence_grid_wraps_every_card():
    grid = evidence_grid([evidence_card("A", []), evidence_card("B", [])])
    assert grid.count("ws-card-title") == 2
    assert grid.startswith('<div class="ws-ev-grid">')
