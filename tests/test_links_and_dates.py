"""Query-parameter links and the decision-date rollover.

Both of these failed silently in production: an industry with an ampersand
produced a link the browser truncated, and a run after the close discarded the
session that had just completed.
"""
import pandas as pd
import pytest

from rs_stages.ui.components import query_href, stock_href
from scripts.real_data_audit import default_decision_date


# --- links -------------------------------------------------------------------

def test_an_ampersand_in_a_value_does_not_split_the_query():
    """'Metals & Mining' must not arrive as 'Metals ' plus a stray parameter."""
    href = query_href(view="Industries", industry="Metals & Mining")
    assert "%26" in href
    # The raw separator must appear exactly once: between view and industry.
    assert href.count("&amp;") == 1
    assert "industry=Metals%20%26%20Mining" in href


@pytest.mark.parametrize("value", [
    "Metals & Mining",
    "Oil Gas & Consumable Fuels",
    "Media Entertainment & Publication",
    "Fast Moving Consumer Goods",
])
def test_industry_values_round_trip_through_the_url(value):
    from urllib.parse import parse_qs, unquote
    import html as html_mod

    href = html_mod.unescape(query_href(view="Industries", industry=value))
    parsed = parse_qs(href.lstrip("?"))
    assert parsed["industry"] == [value]
    assert parsed["view"] == ["Industries"]


def test_symbols_with_awkward_characters_are_encoded():
    assert "%26" in stock_href("A&B")
    assert "%2F" in stock_href("A/B")


def test_none_values_are_omitted_rather_than_written_as_none():
    assert "industry" not in query_href(view="Industries", industry=None)


# --- decision date -----------------------------------------------------------

def _ist(y, m, d, hour):
    return pd.Timestamp(year=y, month=m, day=d, hour=hour, tz="Asia/Kolkata")


def test_after_the_close_the_decision_is_for_the_next_session():
    """The scheduled 23:30 IST run must use the close that just happened."""
    assert default_decision_date(_ist(2026, 8, 24, 23)) == pd.Timestamp("2026-08-25")


def test_before_the_close_today_is_still_in_progress():
    """An incomplete session must never enter a calculation."""
    assert default_decision_date(_ist(2026, 8, 24, 9)) == pd.Timestamp("2026-08-24")


@pytest.mark.parametrize("hour,expected_day", [
    (15, 24),   # market still open
    (16, 25),   # close has passed
    (18, 25),   # the scheduled run, in UTC terms
    (23, 25),
    (0, 24),    # just after midnight, today is not yet traded
])
def test_the_rollover_happens_at_the_close_not_at_midnight(hour, expected_day):
    got = default_decision_date(_ist(2026, 8, 24, hour))
    assert got == pd.Timestamp(f"2026-08-{expected_day:02d}")


def test_the_decision_date_is_never_timezone_aware():
    """The rest of the pipeline compares against tz-naive session stamps."""
    assert default_decision_date(_ist(2026, 8, 24, 23)).tz is None
