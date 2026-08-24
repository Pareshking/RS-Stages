import pandas as pd
import pytest

from rs_stages.pipeline import acquire_and_build_universe_snapshots, acquire_universe_histories, build_universe_snapshots


def _history(start="2026-01-01", periods=5):
    idx = pd.date_range(start, periods=periods, freq="D")
    return pd.DataFrame(
        {"Close": range(100, 100 + periods), "High": range(100, 100 + periods), "Volume": [1000] * periods},
        index=idx,
    )


def test_pipeline_preserves_nse_universe_and_pre_market_boundary(tmp_path):
    csv = tmp_path / "nse.csv"
    pd.DataFrame({"Symbol": ["AAA", "BBB"], "Industry": ["Industry A", "Industry B"]}).to_csv(csv, index=False)
    histories = {"AAA": _history(), "BBB": _history()}
    result = build_universe_snapshots(csv, histories, pd.Timestamp("2026-01-05"))
    assert result.constituents["Symbol"].tolist() == ["AAA", "BBB"]
    assert result.constituents["Industry"].tolist() == ["Industry A", "Industry B"]
    assert result.snapshots["AAA"].latest_completed_session == pd.Timestamp("2026-01-04")
    assert pd.Timestamp("2026-01-05") not in result.snapshots["AAA"].data.index


def test_pipeline_rejects_missing_symbol_history(tmp_path):
    csv = tmp_path / "nse.csv"
    pd.DataFrame({"Symbol": ["AAA", "BBB"], "Industry": ["A", "B"]}).to_csv(csv, index=False)
    with pytest.raises(ValueError, match="Missing market history"):
        build_universe_snapshots(csv, {"AAA": _history()}, pd.Timestamp("2026-01-05"))


def test_acquire_universe_histories_downloads_every_nse_symbol(monkeypatch, tmp_path):
    csv = tmp_path / "nse.csv"
    pd.DataFrame({"Symbol": ["AAA", "BBB"], "Industry": ["A", "B"]}).to_csv(csv, index=False)
    calls = []
    fake_data = {"AAA": _history(), "BBB": _history()}

    def fake_download(symbol, start, end):
        calls.append((symbol, start, end))
        return fake_data[symbol]

    monkeypatch.setattr("rs_stages.pipeline.download_yfinance_history", fake_download)
    got = acquire_universe_histories(csv, "2025-01-01", "2026-01-06")
    assert list(got) == ["AAA", "BBB"]
    assert calls == [("AAA", "2025-01-01", "2026-01-06"), ("BBB", "2025-01-01", "2026-01-06")]


def test_acquire_universe_histories_fails_closed_on_any_symbol(monkeypatch, tmp_path):
    csv = tmp_path / "nse.csv"
    pd.DataFrame({"Symbol": ["AAA", "BBB"], "Industry": ["A", "B"]}).to_csv(csv, index=False)

    def fake_download(symbol, start, end):
        if symbol == "BBB":
            raise ValueError("provider failure")
        return _history()

    monkeypatch.setattr("rs_stages.pipeline.download_yfinance_history", fake_download)
    with pytest.raises(RuntimeError, match="Market-data acquisition failed"):
        acquire_universe_histories(csv, "2025-01-01", "2026-01-06")


def test_acquire_and_build_applies_pre_market_boundary(monkeypatch, tmp_path):
    csv = tmp_path / "nse.csv"
    pd.DataFrame({"Symbol": ["AAA"], "Industry": ["A"]}).to_csv(csv, index=False)
    data = _history(periods=5)
    monkeypatch.setattr("rs_stages.pipeline.download_yfinance_history", lambda *args, **kwargs: data)
    result = acquire_and_build_universe_snapshots(csv, "2025-01-01", "2026-01-06", pd.Timestamp("2026-01-05"))
    assert result.snapshots["AAA"].latest_completed_session == pd.Timestamp("2026-01-04")
    assert pd.Timestamp("2026-01-05") not in result.snapshots["AAA"].data.index


def test_acquisition_never_requests_dummy_symbols(monkeypatch, tmp_path):
    csv = tmp_path / "nse.csv"
    pd.DataFrame(
        {"Symbol": ["ABC", "DUMMYINXGN", "DUMMYTRVN", "XYZ"], "Industry": ["A", "reserved", "reserved", "B"]}
    ).to_csv(csv, index=False)
    requested = []

    def fake_download(symbol, start, end):
        requested.append(symbol)
        return _history()

    monkeypatch.setattr("rs_stages.pipeline.download_yfinance_history", fake_download)
    histories = acquire_universe_histories(csv, "2026-08-01", "2026-08-24")
    assert requested == ["ABC", "XYZ"]
    assert set(histories) == {"ABC", "XYZ"}
