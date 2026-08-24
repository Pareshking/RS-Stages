import sys
import types

import pandas as pd
import pytest

from rs_stages.data import (
    build_decision_snapshot,
    download_yfinance_histories,
    download_yfinance_history,
    latest_completed_session,
    load_nse_constituents_csv,
    normalize_session_index,
    validate_market_columns,
    yfinance_history_kwargs,
    yfinance_symbol,
)


def test_latest_completed_session_excludes_future_session():
    idx = pd.DatetimeIndex(["2026-08-20", "2026-08-21", "2026-08-24"])
    assert latest_completed_session(idx, pd.Timestamp("2026-08-22")) == pd.Timestamp("2026-08-21")


def test_latest_completed_session_excludes_decision_session_even_if_provider_has_it():
    idx = pd.DatetimeIndex(["2026-08-20", "2026-08-21", "2026-08-24"])
    assert latest_completed_session(idx, pd.Timestamp("2026-08-24")) == pd.Timestamp("2026-08-21")


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


def test_snapshot_excludes_decision_session_when_present():
    idx = pd.DatetimeIndex(["2026-08-20", "2026-08-21", "2026-08-24"])
    data = pd.DataFrame({"Close": [100, 101, 999]}, index=idx)
    snap = build_decision_snapshot(data, pd.Timestamp("2026-08-24"))
    assert snap.latest_completed_session == pd.Timestamp("2026-08-21")
    assert list(snap.data["Close"]) == [100, 101]


def test_validate_market_columns():
    validate_market_columns(pd.DataFrame(columns=["Close", "High", "Volume"]))
    with pytest.raises(ValueError):
        validate_market_columns(pd.DataFrame(columns=["Close", "High"]))


def test_yfinance_adjustment_policy_is_locked():
    assert yfinance_history_kwargs() == {"auto_adjust": True}


def test_yfinance_symbol_maps_nse_csv_symbol_only_for_provider():
    assert yfinance_symbol("RELIANCE") == "RELIANCE.NS"
    assert yfinance_symbol("RELIANCE.NS") == "RELIANCE.NS"


def test_download_yfinance_history_uses_locked_policy_and_preserves_ohlcv(monkeypatch):
    calls = {}
    idx = pd.DatetimeIndex(["2026-08-20", "2026-08-21"])
    source = pd.DataFrame(
        {"Close": [110.0, 112.0], "High": [115.0, 118.0], "Volume": [1000, 1200]},
        index=idx,
    )

    fake_yf = types.SimpleNamespace()

    def fake_download(ticker, **kwargs):
        calls["ticker"] = ticker
        calls["kwargs"] = kwargs
        return source.copy()

    fake_yf.download = fake_download
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    got = download_yfinance_history("ABC", "2026-08-01", "2026-08-24")

    assert calls["ticker"] == "ABC.NS"
    assert calls["kwargs"]["auto_adjust"] is True
    assert calls["kwargs"]["actions"] is False
    assert calls["kwargs"]["progress"] is False
    pd.testing.assert_series_equal(got["Close"], source["Close"])
    pd.testing.assert_series_equal(got["High"], source["High"])
    pd.testing.assert_series_equal(got["Volume"], source["Volume"])


def test_download_yfinance_history_collapses_symbol_level_multiindex(monkeypatch):
    ticker = "ABC.NS"
    idx = pd.DatetimeIndex(["2026-08-20", "2026-08-21"])
    columns = pd.MultiIndex.from_tuples(
        [("Close", ticker), ("High", ticker), ("Volume", ticker)]
    )
    source = pd.DataFrame([[110.0, 115.0, 1000], [112.0, 118.0, 1200]], index=idx, columns=columns)
    fake_yf = types.SimpleNamespace(download=lambda *args, **kwargs: source.copy())
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    got = download_yfinance_history("ABC", "2026-08-01", "2026-08-24")
    assert list(got.columns) == ["Close", "High", "Volume"]
    assert got.loc[pd.Timestamp("2026-08-21"), "Volume"] == 1200


def test_download_yfinance_history_rejects_missing_required_column(monkeypatch):
    idx = pd.DatetimeIndex(["2026-08-20"])
    source = pd.DataFrame({"Close": [110.0], "High": [115.0]}, index=idx)
    fake_yf = types.SimpleNamespace(download=lambda *args, **kwargs: source.copy())
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    with pytest.raises(ValueError, match="Missing required market columns"):
        download_yfinance_history("ABC", "2026-08-01", "2026-08-24")


def test_bulk_yfinance_acquisition_uses_bounded_batch_and_preserves_each_ticker(monkeypatch):
    calls = []
    idx = pd.DatetimeIndex(["2026-08-20", "2026-08-21"])
    tickers = ["ABC.NS", "XYZ.NS"]
    columns = pd.MultiIndex.from_product([tickers, ["Close", "High", "Volume"]])
    source = pd.DataFrame(
        [
            [110.0, 115.0, 1000, 210.0, 215.0, 2000],
            [112.0, 118.0, 1200, 212.0, 218.0, 2200],
        ],
        index=idx,
        columns=columns,
    )

    def fake_download(**kwargs):
        calls.append(kwargs)
        return source.copy()

    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(download=fake_download))
    got = download_yfinance_histories(["ABC", "XYZ"], "2026-08-01", "2026-08-24", batch_size=100)

    assert len(calls) == 1
    assert calls[0]["tickers"] == tickers
    assert calls[0]["auto_adjust"] is True
    assert calls[0]["actions"] is False
    assert calls[0]["threads"] is True
    assert calls[0]["group_by"] == "ticker"
    assert set(got) == {"ABC", "XYZ"}
    assert got["ABC"].loc[pd.Timestamp("2026-08-21"), "Volume"] == 1200
    assert got["XYZ"].loc[pd.Timestamp("2026-08-21"), "Volume"] == 2200


def test_bulk_yfinance_acquisition_fails_on_partial_batch(monkeypatch):
    idx = pd.DatetimeIndex(["2026-08-20"])
    columns = pd.MultiIndex.from_product([["ABC.NS"], ["Close", "High", "Volume"]])
    source = pd.DataFrame([[110.0, 115.0, 1000]], index=idx, columns=columns)
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(download=lambda **kwargs: source.copy()))

    with pytest.raises(RuntimeError, match="Bulk market-data acquisition failed"):
        download_yfinance_histories(["ABC", "XYZ"], "2026-08-01", "2026-08-24")


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


def test_nse_csv_ignores_symbols_starting_with_dummy(tmp_path):
    path = tmp_path / "nse.csv"
    pd.DataFrame(
        {"Symbol": ["ABC", "DUMMYFOO", "DUMMYBAR", "XYZ"], "Industry": ["A", "X", "Y", "B"]}
    ).to_csv(path, index=False)
    got = load_nse_constituents_csv(path)
    assert list(got["Symbol"]) == ["ABC", "XYZ"]
    assert list(got["Industry"]) == ["A", "B"]
