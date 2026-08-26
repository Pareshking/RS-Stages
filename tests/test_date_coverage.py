"""A snapshot's 'Date' can legitimately differ across symbols.

Date is set per symbol from that symbol's own latest completed session
(screener.py), not a shared clock, because the price provider updates its
feed asynchronously — larger, more liquid names first. On the run of 26 Aug
2026, 445 of 750 symbols already carried 25 Aug while 305 still carried 24
Aug, split cleanly along liquidity (median 20-session traded value roughly
3x higher in the leading group). The header's decision_date is the max of
that column, so before this fix the site announced a single validated date
that only 59% of the universe actually reflected. These tests pin the
disclosure that replaced the silent .max().
"""

import pandas as pd
import pytest

from rs_stages.ui.loaders import DateCoverage, Snapshot


def _snapshot(dates: list[str]) -> Snapshot:
    research = pd.DataFrame({
        "Symbol": [f"SYM{i}" for i in range(len(dates))],
        "Date": dates,
    })
    return Snapshot(research=research, universe=pd.DataFrame({"Symbol": []}))


def test_a_uniform_snapshot_is_not_split():
    coverage = _snapshot(["2026-08-25"] * 750).date_coverage
    assert not coverage.is_split
    assert coverage.lagging_count == 0
    assert coverage.current_count == 750
    assert coverage.latest == pd.Timestamp("2026-08-25")


def test_the_reported_split_matches_the_run_that_found_it():
    coverage = _snapshot(["2026-08-25"] * 445 + ["2026-08-24"] * 305).date_coverage
    assert coverage.is_split
    assert coverage.latest == pd.Timestamp("2026-08-25")
    assert coverage.current_count == 445
    assert coverage.lagging_count == 305
    assert coverage.lagging_pct == pytest.approx(305 / 750 * 100)


def test_latest_is_always_the_newest_date_present_regardless_of_row_order():
    """decision_date already takes .max(); coverage must agree with it."""
    coverage = _snapshot(["2026-08-24", "2026-08-26", "2026-08-25"]).date_coverage
    assert coverage.latest == pd.Timestamp("2026-08-26")


def test_three_way_split_counts_every_group():
    coverage = _snapshot(["2026-08-25"] * 3 + ["2026-08-24"] * 2 + ["2026-08-21"]).date_coverage
    assert coverage.is_split
    assert coverage.current_count == 3
    assert coverage.lagging_count == 3  # every non-latest date, summed


def test_an_empty_or_all_missing_research_frame_reports_no_coverage():
    coverage = Snapshot(
        research=pd.DataFrame({"Symbol": [], "Date": []}),
        universe=pd.DataFrame({"Symbol": []}),
    ).date_coverage
    assert coverage.latest is None
    assert coverage.counts == {}
    assert not coverage.is_split


def test_decision_date_and_coverage_latest_never_disagree():
    """Two properties describing the same column must not drift apart."""
    snap = _snapshot(["2026-08-25"] * 445 + ["2026-08-24"] * 305)
    assert snap.decision_date == snap.date_coverage.latest
