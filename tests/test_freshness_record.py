"""The audit must record how much of the universe it actually caught.

The publish schedule has moved twice on an argument about a third party's
publishing curve (D-2.2.12, D-2.2.14) with no measurement either time. This
records the split on every run so the third move is made from evidence, and
says so loudly in the log when the ranking is comparing two sessions.

The split is never a reason to withhold: publishing a disclosed split beats
leaving the site on an older snapshot carrying the same split.
"""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.real_data_audit import (
    FRESHNESS_HISTORY,
    MAX_LAGGING_SHARE_PCT,
    record_freshness,
)


def _result(current: int, lagging: int) -> pd.DataFrame:
    dates = ["2026-08-28"] * current + ["2026-08-27"] * lagging
    return pd.DataFrame({"Symbol": [f"S{i}" for i in range(len(dates))], "Date": dates})


def test_a_split_run_reports_its_share_and_records_a_row(tmp_path, capsys):
    share = record_freshness(_result(current=261, lagging=489), tmp_path)
    assert share == pytest.approx(65.2, abs=0.1)

    out = capsys.readouterr().out
    assert "Date split across the universe" in out
    assert "489 of 750" in out

    history = pd.read_csv(tmp_path / FRESHNESS_HISTORY)
    assert len(history) == 1
    row = history.iloc[0]
    assert row["Symbols"] == 750
    assert row["Current"] == 261
    assert row["Lagging"] == 489
    assert row["Decision_Date"] == "2026-08-28"


def test_an_excessive_split_raises_a_visible_warning(tmp_path, capsys):
    """Above the threshold the run log has to say so, not only the website."""
    record_freshness(_result(current=261, lagging=489), tmp_path)
    assert "::warning title=" in capsys.readouterr().out


def test_a_split_inside_the_threshold_stays_quiet(tmp_path, capsys):
    lagging = 30  # 4% of 750, well inside the threshold
    record_freshness(_result(current=720, lagging=lagging), tmp_path)
    output = capsys.readouterr().out
    assert "Date split across the universe" in output
    assert "::warning" not in output
    assert lagging / 750 * 100 < MAX_LAGGING_SHARE_PCT


def test_a_whole_universe_on_one_session_says_so(tmp_path, capsys):
    share = record_freshness(_result(current=750, lagging=0), tmp_path)
    assert share == 0.0
    assert "no provider lag" in capsys.readouterr().out


def test_history_accumulates_rather_than_being_overwritten(tmp_path):
    record_freshness(_result(current=261, lagging=489), tmp_path)
    record_freshness(_result(current=700, lagging=50), tmp_path)
    history = pd.read_csv(tmp_path / FRESHNESS_HISTORY)
    assert len(history) == 2
    assert list(history["Lagging"]) == [489, 50]


def test_a_history_of_the_wrong_shape_costs_the_run_nothing(tmp_path, capsys):
    """The snapshot is the deliverable; the record is bookkeeping beside it.

    A CSV parser returns a frame for plenty of files that are not this file, so
    a read that merely succeeds is not evidence the history is this history.
    """
    (tmp_path / FRESHNESS_HISTORY).write_text("Symbol,Close\nRELIANCE,1234\n")
    record_freshness(_result(current=261, lagging=489), tmp_path)
    assert "starting a new one" in capsys.readouterr().out
    history = pd.read_csv(tmp_path / FRESHNESS_HISTORY)
    assert len(history) == 1
    assert list(history.columns) == [
        "Run_UTC", "Decision_Date", "Symbols", "Current", "Lagging", "Lagging_Pct",
    ]


def test_an_unwritable_history_costs_the_run_nothing(tmp_path, capsys):
    """Recording runs after the artifacts are written and before they are
    committed, so a failure here would fail a run whose snapshot was correct."""
    (tmp_path / FRESHNESS_HISTORY).mkdir()  # a directory where the file should be
    share = record_freshness(_result(current=261, lagging=489), tmp_path)
    assert share == pytest.approx(65.2, abs=0.1)
    output = capsys.readouterr().out
    assert "the run is unaffected" in output
    # The reading it exists to describe is still reported.
    assert "Lagging share: 65.2%" in output


def test_an_empty_result_does_not_raise(tmp_path):
    assert record_freshness(pd.DataFrame({"Symbol": [], "Date": []}), tmp_path) == 0.0
