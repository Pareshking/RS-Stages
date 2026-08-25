"""Documented thresholds must equal the constants the code actually uses.

Five v2.2 formulas were published with wrong numbers because they were written
from the spec and from memory rather than read out of quant.py. The published
RS-divergence rule said "price below its high" where the code requires price 5%
below it, and Stage1_Readiness was documented as four criteria on a 0-4 scale
where the code counts five on 0-5 — so a published 4 read as full marks when it
was one short.

Prose can drift from code silently. A number cannot, once it is pinned here.
"""

import re
from pathlib import Path

import pytest

from rs_stages import quant

FORMULAS = Path(__file__).resolve().parents[1] / "docs" / "FORMULAS.md"


@pytest.fixture(scope="module")
def text() -> str:
    return FORMULAS.read_text()


@pytest.mark.parametrize(
    "constant, expected",
    [
        ("RS_LINE_HIGH_TOLERANCE", 0.005),
        ("RS_LINE_PRICE_GAP_PCT", -5.0),
        ("VCP_CONTRACTION_RATIO_MAX", 0.60),
        ("VCP_VOLUME_DRYUP_MAX", 0.80),
        ("VCP_MAX_BASE_DEPTH_PCT", 35.0),
        ("VCP_MIN_CONTRACTIONS", 2),
        ("STAGE1_SLOPE_MIN", -0.10),
        ("STAGE1_RS_MIN", 50.0),
        ("STAGE1_CONTRACTION_MAX", 0.70),
        ("STAGE1_DRYUP_MAX", 0.90),
        ("TREND_TEMPLATE_LOW_MULTIPLE", 1.30),
        ("TREND_TEMPLATE_HIGH_FRACTION", 0.75),
        ("TREND_TEMPLATE_MIN_RS", 70.0),
        ("VOLUME_DRYUP_RECENT", 10),
        ("VOLUME_DRYUP_BASELINE", 50),
        ("VCP_BASE_SESSIONS", 50),
        ("ATR_SESSIONS", 14),
    ],
)
def test_the_constant_still_holds_the_value_the_docs_describe(constant, expected):
    """If this fails, the code changed and FORMULAS.md now describes the past."""
    assert getattr(quant, constant) == expected


def test_the_rs_divergence_gap_is_documented_with_its_real_value(text):
    """The specific error that shipped: the doc said < 0, the code says <= -5."""
    assert "Pct_From_52W_High <= -5.0" in text
    assert "Pct_From_52W_High < 0" not in text


def test_the_rs_divergence_gap_is_marked_as_ours(text):
    """A project-chosen threshold must never read as the source's."""
    assert "The -5.0 gap is ours" in text


def test_stage1_readiness_is_documented_on_its_real_scale(text):
    assert "[0, 5]" in text
    assert "count in [0, 4]" not in text


def test_stage1_readiness_documents_all_five_criteria(text):
    section = text.split("### Stage 1 readiness")[1].split("###")[0]
    for criterion in ["Slope_30W", "RS_Score", "Contraction_Ratio", "Volume_Dryup", "MA_10W"]:
        assert criterion in section, f"{criterion} missing from the documented count"


def test_volume_dryup_windows_are_documented_as_disjoint(text):
    """recent is 10 sessions; the baseline is the 50 BEFORE them, not around them."""
    assert "BEFORE those 10" in text
    assert "last 10 sessions) / mean(Volume, last 50)" not in text


def test_the_pivot_records_that_it_is_the_base_high_not_the_final_contraction(text):
    assert "highest High over the trailing 50 sessions" in text
    assert "highest High within the final contraction" not in text


def test_every_provisional_threshold_is_still_flagged(text):
    assert text.count("provisional") >= 3
