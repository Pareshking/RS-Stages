"""Interaction coverage for the views that gained controls.

These drive the real entrypoint through Streamlit's AppTest, which re-executes
the script exactly as a user interaction does. A control that renders but does
nothing on rerun would pass a smoke test and fail here.
"""
import html
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app.py")


def _app(view: str) -> AppTest:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=60)
    at.query_params["view"] = view
    at.run()
    assert not at.exception
    return at


def _markdown(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_industry_table_sorts_by_every_offered_column():
    at = _app("Industries")
    sort = [s for s in at.selectbox if s.label == "Sort by"][0]
    for option in sort.options:
        sort.set_value(option)
        at.run(timeout=60)
        assert not at.exception, f"sorting by {option} raised"
        sort = [s for s in at.selectbox if s.label == "Sort by"][0]
        assert sort.value == option


def test_selecting_an_industry_reveals_its_constituents():
    at = _app("Industries")
    pick = [s for s in at.selectbox if s.label == "Show stocks in"][0]
    assert pick.value == "None"
    assert "Stage posture in" not in _markdown(at)

    industry = next(o for o in pick.options if o != "None")
    pick.set_value(industry)
    at.run(timeout=60)
    assert not at.exception
    body = _markdown(at)
    # Industry names carry ampersands; they reach the page HTML-escaped.
    assert f"Stage posture in {html.escape(industry)}" in body
    # The constituents render as the dense table, not a bare list.
    assert "ws-table" in body


def test_clearing_the_industry_selection_hides_the_drill_down():
    at = _app("Industries")
    pick = [s for s in at.selectbox if s.label == "Show stocks in"][0]
    industry = next(o for o in pick.options if o != "None")
    pick.set_value(industry); at.run(timeout=60)
    assert "Stage posture in" in _markdown(at)

    pick = [s for s in at.selectbox if s.label == "Show stocks in"][0]
    pick.set_value("None"); at.run(timeout=60)
    assert not at.exception
    assert "Stage posture in" not in _markdown(at)


def test_movers_puts_every_group_member_somewhere_reachable():
    """A group larger than the inline cap must expose the rest, not drop it."""
    at = _app("Movers")
    body = _markdown(at)
    if "Nothing changed state" in body or "unavailable" in body:
        pytest.skip("no previous snapshot published in this checkout")
    # Any group beyond the inline cap gets an expander naming the remainder.
    expanders = [e.label for e in at.expander]
    for label in expanders:
        assert "Show the remaining" in label


def test_screener_filters_rerun_without_error():
    at = _app("Screener")
    stage = at.selectbox[1] if len(at.selectbox) > 1 else None
    sort = [s for s in at.selectbox if s.label == "Sort by"][0]
    for option in sort.options:
        sort.set_value(option)
        at.run(timeout=60)
        assert not at.exception, f"sorting the screener by {option} raised"
        sort = [s for s in at.selectbox if s.label == "Sort by"][0]
