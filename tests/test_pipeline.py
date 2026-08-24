import pandas as pd
import pytest

from rs_stages.pipeline import build_universe_snapshots


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
