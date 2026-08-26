"""The header and Dashboard must never claim one date for a split universe.

decision_date is the max of a per-symbol column, so a header reading
'Validated snapshot 25 Aug 2026' used to imply every symbol was current as
of that date even when a large fraction was one session behind. This drives
the real app against whatever data/latest_research.csv currently holds,
computing the expected split independently from the same file, so the test
stays correct as the published snapshot changes rather than freezing today's
counts.
"""

from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from rs_stages.ui.loaders import RESEARCH_PATH

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app.py")


def _expected_coverage() -> tuple[bool, int, int]:
    """(is_split, current_count, lagging_count), computed straight from disk."""
    research = pd.read_csv(RESEARCH_PATH)
    dates = pd.to_datetime(research["Date"], errors="coerce").dropna().dt.normalize()
    if dates.empty:
        return False, 0, 0
    latest = dates.max()
    current = int((dates == latest).sum())
    return len(dates.unique()) > 1, current, len(dates) - current


def _app(view: str) -> AppTest:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=60)
    at.query_params["view"] = view
    at.run()
    assert not at.exception
    return at


def _rendered_text(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_header_and_dashboard_agree_with_the_file_on_disk():
    is_split, current, lagging = _expected_coverage()
    text = _rendered_text(_app("Dashboard"))
    disclosed = "Not every stock is on today's close" in text

    assert disclosed == is_split
    if is_split:
        assert f"{current:,}" in text
        assert f"{lagging:,}" in text


def test_a_uniform_snapshot_never_shows_the_lag_banner():
    """Guards the other direction: no false alarm when every symbol agrees."""
    is_split, _, _ = _expected_coverage()
    if is_split:
        return  # today's data is split; the positive case is covered elsewhere
    text = _rendered_text(_app("Dashboard"))
    assert "Not every stock is on today's close" not in text
    assert "provider lag" not in text.lower()
