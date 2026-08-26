"""The Stock page must itemize the Minervini trend template, not just score it.

The v2.2 block showed a single collapsed "N of 8" line for the trend template
while the pre-existing Weinstein trend-health block showed all five conditions
individually with pass/fail marks. Asked directly to check, the template had
no per-criterion breakdown anywhere on the page — this drives the real app
against a symbol picked from the live snapshot for both a full pass and a
partial pass, so it fails if the checklist regresses to a summary number again.
"""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from rs_stages.screener import TREND_TEMPLATE_CONDITIONS
from rs_stages.ui.loaders import RESEARCH_PATH

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app.py")


def _pick_symbol(min_score: int, max_score: int) -> str | None:
    research = pd.read_csv(RESEARCH_PATH)
    if "Trend_Template_Score" not in research.columns:
        return None
    score = pd.to_numeric(research["Trend_Template_Score"], errors="coerce")
    match = research.loc[score.between(min_score, max_score), "Symbol"]
    return None if match.empty else str(match.iloc[0])


def _stock_text(symbol: str) -> str:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=60)
    at.query_params["view"] = "Stock"
    at.query_params["symbol"] = symbol
    at.run()
    assert not at.exception
    return " ".join(m.value for m in at.markdown)


def test_a_full_pass_shows_all_eight_conditions_checked():
    symbol = _pick_symbol(8, 8)
    if symbol is None:
        pytest.skip("no symbol passing all eight criteria in the live snapshot")
    text = _stock_text(symbol)
    i = text.find("Minervini trend-template checklist")
    assert i >= 0, "checklist card is missing from the Stock page"
    for _, label in TREND_TEMPLATE_CONDITIONS:
        assert label in text[i:i + 3000]
    assert "8/8" in text[i:i + 200]


def test_a_partial_pass_shows_a_mix_of_pass_and_fail_marks():
    symbol = _pick_symbol(1, 7)
    if symbol is None:
        pytest.skip("no partial-pass symbol in the live snapshot")
    text = _stock_text(symbol)
    i = text.find("Minervini trend-template checklist")
    assert i >= 0
    window = text[i:i + 3000]
    assert "✓" in window and "✕" in window


def test_the_disclaimer_names_exactly_three_thresholds_as_provisional():
    """The footer note must not blanket-label all eight as provisional."""
    symbol = _pick_symbol(0, 8)
    if symbol is None:
        pytest.skip("no symbol with a trend-template score in the live snapshot")
    text = _stock_text(symbol)
    assert "Three of the trend template's eight thresholds are" in text
    assert "The trend-template thresholds are provisional" not in text
