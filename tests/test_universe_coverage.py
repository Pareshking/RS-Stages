"""The audit must survive a bad symbol without publishing a distorted universe.

The run of 25 Aug 2026 aborted with "No completed market session exists before
decision date". Three tickers had timed out against the provider and one came
back with no rows, which raised out of the snapshot comprehension and killed the
whole 750-symbol audit before anything was published.

Two properties are pinned here, and they pull in opposite directions on purpose:
one symbol must not be able to fail the run, and a depleted universe must not be
able to publish quietly.
"""

import numpy as np
import pandas as pd
import pytest

from scripts.real_data_audit import (
    MAX_UNIVERSE_LOSS_PCT,
    build_universe_snapshots,
    enforce_universe_coverage,
)

DECISION = pd.Timestamp("2026-08-25")


def _history(sessions: int = 30, last: str = "2026-08-24") -> pd.DataFrame:
    idx = pd.bdate_range(end=pd.Timestamp(last), periods=sessions)
    return pd.DataFrame(
        {
            "Open": np.linspace(100, 110, sessions),
            "High": np.linspace(101, 111, sessions),
            "Low": np.linspace(99, 109, sessions),
            "Close": np.linspace(100, 110, sessions),
            "Volume": np.full(sessions, 1_000.0),
        },
        index=idx,
    )


def test_a_symbol_with_no_rows_is_excluded_rather_than_fatal():
    """The exact shape of the failure: an empty frame from a failed download."""
    histories = {"GOOD": _history(), "BELRISE": _history().iloc[0:0]}

    snapshots, unavailable = build_universe_snapshots(
        ["GOOD", "BELRISE"], histories, DECISION
    )

    assert set(snapshots) == {"GOOD"}
    assert [name for name, _ in unavailable] == ["BELRISE"]


def test_a_symbol_absent_from_the_download_is_excluded_with_its_reason():
    snapshots, unavailable = build_universe_snapshots(
        ["GOOD", "NEVER_FETCHED"], {"GOOD": _history()}, DECISION
    )

    assert set(snapshots) == {"GOOD"}
    assert unavailable == [("NEVER_FETCHED", "the provider returned no history")]


def test_every_exclusion_carries_a_reason():
    """A silent drop is the failure mode this guard exists to prevent."""
    _, unavailable = build_universe_snapshots(
        ["A", "B"], {"A": _history().iloc[0:0]}, DECISION
    )

    assert len(unavailable) == 2
    assert all(reason.strip() for _, reason in unavailable)


def test_losing_a_stray_symbol_is_tolerated():
    """One delisting in a 750-name universe is 0.13% and must not stop a run."""
    enforce_universe_coverage(missing=1, total=750)


def test_losing_more_than_the_tolerance_refuses_to_publish():
    """RS_Score is cross-sectional: a depleted universe re-ranks the survivors."""
    missing = int(750 * MAX_UNIVERSE_LOSS_PCT / 100) + 1

    with pytest.raises(SystemExit, match="cross-sectional percentile"):
        enforce_universe_coverage(missing=missing, total=750)


def test_the_guard_holds_at_the_boundary():
    at_limit = int(750 * MAX_UNIVERSE_LOSS_PCT / 100)
    enforce_universe_coverage(missing=at_limit, total=750)

    with pytest.raises(SystemExit):
        enforce_universe_coverage(missing=at_limit + 1, total=750)


def test_an_empty_universe_does_not_divide_by_zero():
    enforce_universe_coverage(missing=0, total=0)
