import pandas as pd
import pytest

from rs_stages.data import (
    build_decision_snapshot,
    latest_completed_session,
    load_nse_constituents_csv,
    normalize_session_index,
    validate_market_columns,
    yfinance_history_kwargs,
)


def test_latest_completed_session_excludes_future_session():
    idx = pd.DatetimeIndex(["2026-08-20", "2026-08-21", "2026-08-24"])
    assert latest_completed_session(idx, pd.Timestamp("2026-08-22")) == pd.Timestamp("2026-08-21")


def test_latest_completed_session_allows_same_completed_date():
    idx = pd.DatetimeIndex(["2026-08-20", "2026-08-21"])
    assert latest_completed_session(idx, pd.Timestamp("2026-08-21")) == pd.Timestamp("2026-08-21")


def test_normalize_rejects_duplicate_sessions():
    idx = pd.DatetimeIndex(["2026-08-21", "2026-08-21"])
    with pytest.raises(ValueError):
        normalize_session_index(pd.DataFrame({"Close": [1, 2]}, index=idx))


def test_normalize_sorts_and_removes_time_component():
    idx = pd.DatetimeIndex(["2026-08-21 15:30", "2026-08-20 15:30"])
    out = normalize_session_index(pd.DataFrame({"Close": [2, 1]}, index=idx))
    assert list(out.index) == [pd.Timestamp("2026-08-20"), pd.Timestamp("2026-08-21")]


def test_snapshot_contains_only_completed_information():
    idx = pd.date_range("2026-08-20", periods=4, freq="D")
    data = pd.DataFrame({"Close": [100, 101, 102, 999]}, index=idx)
    snap = build_decision_snapshot(data, pd.Timestamp("2026-08-23"))
    assert snap.latest_completed_session == pd.Timestamp("2026-08-22")
    assert list(snap.data["Close"]) == [100, 101, 102]


def test_validate_market_columns():
    validate_market_columns(pd.DataFrame(columns=["Close", "High", "Volume"]))
    with pytest.raises(ValueError):
        validate_market_columns(pd.DataFrame(columns=["Close", "High"]))


def test_yfinance_adjustment_policy_is_locked():
    assert yfinance_history_kwargs() == {"auto_adjust": True}


def test_nse_csv_ingestion_preserves_symbols_and_industry(tmp_path):
    path = tmp_path / "nse.csv"
    pd.DataFrame({"Symbol": ["ABC", "XYZ"], "Industry": ["A", "B"]}).to_csv(path, index=False)
    got = load_nse_constituents_csv(path)
    assert list(got["Symbol"]) == ["ABC", "XYZ"]
    assert list(got["Industry"]) == ["A", "B"]


def test_nse_csv_rejects_duplicate_symbol(tmp_path):
    path = tmp_path / "nse.csv"
    pd.DataFrame({"Symbol": ["ABC", "ABC"], "Industry": ["A", "A"]}).to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_nse_constituents_csv(path)
