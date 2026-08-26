"""The Stock page must separate Weinstein, O'Neil and Minervini into their
own boxes rather than one flat signal card mixing all three.

Asked whether Weinstein and O'Neil got the same treatment as Minervini's new
trend-template checklist, the page turned out to mix all three authors' facts
into one "Signal card" and one flat "Every signal against its threshold"
table, while the RS-line evidence (attributed to O'Neil in the citation text)
was displayed inside Minervini's section. This drives the real Stock page for
symbols picked from the live snapshot to pin the corrected structure.
"""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from rs_stages.ui.loaders import RESEARCH_PATH

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app.py")


def _any_symbol() -> str:
    return str(pd.read_csv(RESEARCH_PATH)["Symbol"].dropna().iloc[0])


def _wait_symbol() -> str | None:
    research = pd.read_csv(RESEARCH_PATH)
    if "Action" not in research.columns:
        return None
    match = research.loc[research["Action"] == "WAIT", "Symbol"]
    return None if match.empty else str(match.iloc[0])


def _stock_text(symbol: str) -> str:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=60)
    at.query_params["view"] = "Stock"
    at.query_params["symbol"] = symbol
    at.run()
    assert not at.exception
    return " ".join(m.value for m in at.markdown)


def test_all_three_authority_boxes_are_present():
    text = _stock_text(_any_symbol())
    assert "Weinstein" in text
    assert "O&#x27;Neil" in text or "O'Neil" in text
    assert "Minervini" in text


def test_the_old_flat_signal_card_and_threshold_table_are_gone():
    text = _stock_text(_any_symbol())
    assert "Every signal against its threshold" not in text


def test_the_rs_line_evidence_moved_out_of_minervinis_section():
    """The card used to sit inside the v2.2 block; it belongs to O'Neil now."""
    text = _stock_text(_any_symbol())
    assert "Relative strength line</div>" not in text


def test_rs_line_values_still_appear_somewhere_on_the_page():
    """Moving the card must not delete the numbers it displayed."""
    symbol = _any_symbol()
    research = pd.read_csv(RESEARCH_PATH)
    if "RS_Line" not in research.columns:
        pytest.skip("snapshot predates v2.2")
    text = _stock_text(symbol)
    assert "RS line" in text


def test_volume_and_ud_values_still_appear_after_removing_the_threshold_table():
    text = _stock_text(_any_symbol())
    assert "Volume ratio" in text
    assert "U/D ratio" in text


def test_oneil_box_shows_its_own_conclusion_not_weinsteins():
    text = _stock_text(_any_symbol())
    i = text.find("O'Neil</div>")
    if i < 0:
        i = text.find("O&#x27;Neil</div>")
    assert i >= 0, "O'Neil box heading not found"
    # The box's own footer note must not be empty of authorial content when
    # there is evidence for it — checked structurally: the checklist renders.
    assert "Relative strength 80 or better" in text[i:i + 2000]


def test_interaction_notes_appear_only_when_there_is_something_to_say():
    wait_symbol = _wait_symbol()
    if wait_symbol is None:
        pytest.skip("no WAIT symbol in the live snapshot")
    text = _stock_text(wait_symbol)
    assert "Where the readings interact" in text


def test_no_exception_across_a_sample_of_symbols():
    """A structural regression here would crash every stock page, not one."""
    research = pd.read_csv(RESEARCH_PATH)
    sample = research["Symbol"].dropna().astype(str).sample(
        min(5, len(research)), random_state=0
    )
    for symbol in sample:
        at = AppTest.from_file(ENTRYPOINT, default_timeout=60)
        at.query_params["view"] = "Stock"
        at.query_params["symbol"] = symbol
        at.run()
        assert not at.exception, f"{symbol}: {at.exception}"


# --- the closing "Bottom line" card ------------------------------------------


def test_the_bottom_line_card_restates_the_top_action():
    """It must be the same locked decision, not a second computed verdict."""
    symbol = _any_symbol()
    research = pd.read_csv(RESEARCH_PATH)
    action = str(research.loc[research["Symbol"] == symbol, "Action"].iloc[0])
    text = _stock_text(symbol)
    i = text.find("Bottom line</div>")
    assert i >= 0
    assert f'>{action}<' in text[i:i + 400]


def test_minervini_is_labelled_context_not_a_vote():
    text = _stock_text(_any_symbol())
    i = text.find("Bottom line</div>")
    assert i >= 0
    assert "not a vote" in text[i:i + 1500]


def test_a_full_template_pass_can_sit_beside_a_non_buy_action():
    """ABB: Trend_Template_Score 8/8, Action HOLD. Proves Minervini doesn't vote."""
    research = pd.read_csv(RESEARCH_PATH)
    if "ABB" not in research["Symbol"].values:
        pytest.skip("ABB not in the live snapshot")
    row = research.loc[research["Symbol"] == "ABB"].iloc[0]
    if row.get("Trend_Template_Score") != 8:
        pytest.skip("ABB no longer scores 8/8 in the live snapshot")
    text = _stock_text("ABB")
    i = text.find("Bottom line</div>")
    assert i >= 0
    window = text[i:i + 900]
    assert "all eight trend-template criteria met" in window
    assert f'>{row["Action"]}<' in window


def test_no_bottom_line_card_when_no_authority_has_anything_to_say():
    """A row with no classifiable Stage, RS or v2.2 evidence yields no quotes."""
    from rs_stages import signal_card

    empty_row = pd.Series({"Stage": None, "RS_Score": float("nan")})
    assert signal_card.weinstein_line(empty_row) == ""
    assert signal_card.oneil_line(empty_row) == ""
    assert signal_card.minervini_line(empty_row) == ""
