"""End-to-end integrity of the artifacts the audit publishes for the UI.

The UI is a presentation layer: it may only read what the audit wrote. These
tests assert that the published artifacts agree with each other and with the
snapshot they were derived from, so a chart and a table can never disagree
about the same session.
"""
import numpy as np
import pandas as pd
import pytest

from rs_stages.actions import with_actions
from rs_stages.data import build_decision_snapshot
from rs_stages.market import breadth_history_from_trends, breadth_snapshot
from rs_stages.movers import transitions
from rs_stages.quant import ma_10w_series, ma_30w_series
from rs_stages.screener import analyze_universe, analyze_universe_with_trend

DECISION = pd.Timestamp("2026-08-24")


def _history(seed: int, periods: int = 620) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=pd.Timestamp("2026-08-21"), periods=periods)
    close = pd.Series(200.0 + rng.normal(0.35, 3.0, periods).cumsum(), index=idx).clip(lower=5.0)
    return pd.DataFrame(
        {
            "Close": close,
            "High": close * 1.012,
            "Low": close * 0.988,
            "Volume": pd.Series(rng.uniform(4e5, 3e6, periods), index=idx),
        }
    )


@pytest.fixture(scope="module")
def artifacts():
    histories = {f"SYM{i}": _history(seed=i) for i in range(6)}
    snapshots = {s: build_decision_snapshot(h, DECISION) for s, h in histories.items()}
    previous = {
        s: build_decision_snapshot(histories[s], snap.latest_completed_session)
        for s, snap in snapshots.items()
    }
    current, trends = analyze_universe_with_trend(snapshots, trend_sessions=420)
    return {
        "current": with_actions(current),
        "previous": with_actions(analyze_universe(previous)),
        "trends": trends,
        "snapshots": snapshots,
    }


def test_previous_snapshot_is_one_completed_session_behind(artifacts):
    current, previous = artifacts["current"], artifacts["previous"]
    for symbol in current.index:
        assert previous.loc[symbol, "Date"] < current.loc[symbol, "Date"]
    # And exactly one session behind, not an arbitrary earlier date.
    history_index = artifacts["snapshots"]["SYM0"].data.index
    position = history_index.get_loc(current.loc["SYM0", "Date"])
    assert previous.loc["SYM0", "Date"] == history_index[position - 1]


def test_previous_snapshot_never_sees_the_current_session(artifacts):
    """The whole point of the diff is that the earlier side is genuinely earlier."""
    for symbol, snap in artifacts["snapshots"].items():
        current_date = artifacts["current"].loc[symbol, "Date"]
        previous_date = artifacts["previous"].loc[symbol, "Date"]
        assert previous_date < current_date <= snap.data.index.max()


def test_price_panel_round_trips_through_parquet_without_losing_alignment(artifacts, tmp_path):
    trends = artifacts["trends"]
    panel = pd.concat(
        [
            frame[["Close"]].assign(Symbol=symbol).rename_axis("Date").reset_index()
            for symbol, frame in trends.items()
        ],
        ignore_index=True,
    )
    panel["Close"] = panel["Close"].astype("float32")
    panel["Symbol"] = panel["Symbol"].astype("category")
    path = tmp_path / "price_panel.parquet"
    panel[["Date", "Symbol", "Close"]].sort_values(["Symbol", "Date"]).to_parquet(path, index=False)

    reloaded = pd.read_parquet(path)
    assert set(reloaded["Symbol"].astype(str)) == set(trends)
    for symbol in trends:
        stored = reloaded[reloaded["Symbol"].astype(str) == symbol].set_index("Date")["Close"]
        assert stored.index.max() == artifacts["current"].loc[symbol, "Date"]
        # float32 storage: the panel is a drawing input, so single precision is
        # acceptable, but it must still round-trip to the snapshot's close.
        assert np.isclose(
            float(stored.iloc[-1]), float(artifacts["current"].loc[symbol, "Close"]), rtol=1e-6, atol=0
        )


def test_moving_averages_recomputed_from_the_panel_match_the_snapshot(artifacts):
    """The UI redraws lines from Close using the locked functions, not stored copies."""
    for symbol, frame in artifacts["trends"].items():
        close = frame["Close"].astype("float32").astype(float)
        row = artifacts["current"].loc[symbol]
        # The panel is a truncated tail, so the 30-week line it can reproduce is
        # only as good as the retained history; assert on the shorter line and on
        # the ordering that the chart actually displays.
        recomputed_10w = ma_10w_series(close).iloc[-1]
        assert np.isclose(recomputed_10w, row["MA_10W"], rtol=1e-5, atol=0)
        recomputed_30w = ma_30w_series(close).iloc[-1]
        assert np.isclose(recomputed_30w, row["MA_30W"], rtol=1e-5, atol=0)


def test_breadth_history_last_row_equals_the_snapshot_breadth(artifacts):
    history = breadth_history_from_trends(artifacts["trends"], sessions=120)
    snapshot = breadth_snapshot(artifacts["current"].reset_index())
    last = history.iloc[-1]
    assert int(last["Above_MA_30W"]) == snapshot["above_ma_30w"]
    assert int(last["Above_MA_10W"]) == snapshot["above_ma_10w"]
    assert np.isclose(last["Pct_Above_MA_30W"], snapshot["pct_above_ma_30w"])


def test_breadth_history_is_monotonic_in_date_and_bounded(artifacts):
    history = breadth_history_from_trends(artifacts["trends"], sessions=120)
    assert history["Date"].is_monotonic_increasing
    assert history["Date"].is_unique
    assert (history["Pct_Above_MA_30W"].between(0.0, 100.0)).all()
    assert (history["Above_MA_30W"] <= history["Symbols"]).all()


def test_transitions_between_the_two_published_snapshots_are_well_formed(artifacts):
    groups = transitions(
        artifacts["current"].reset_index(), artifacts["previous"].reset_index()
    )
    known = set(artifacts["current"].index.astype(str))
    for label, payload in groups.items():
        rows = payload["rows"]
        assert not rows.empty, f"empty group {label} should have been omitted"
        assert set(rows["Symbol"]).issubset(known)
        assert rows["Symbol"].is_unique
        assert payload["description"]


def test_action_is_stored_and_reproducible_from_the_stored_fields(artifacts):
    """Recomputing Action from the published columns must return the same label."""
    stored = artifacts["current"]
    recomputed = with_actions(stored.drop(columns=["Action", "Action_Reason"]))
    assert (recomputed["Action"] == stored["Action"]).all()


def test_timing_warnings_are_present_in_the_published_snapshot(artifacts):
    """The guide's extension and 50DMA conditions must reach the action layer."""
    stored = artifacts["current"]
    for column in ("Extended_20Pct", "Below_50DMA", "SMA_50", "Ext_Pct", "MA_10W", "Close"):
        assert column in stored.columns
    assert stored["Extended_20Pct"].dtype == bool
    assert stored["Below_50DMA"].dtype == bool
