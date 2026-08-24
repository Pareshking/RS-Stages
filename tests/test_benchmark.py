"""The benchmark index is reference data and must behave like it."""
import pandas as pd
import pytest

from rs_stages.data import INDEX_TICKERS, yfinance_symbol
from rs_stages.market import breadth_history_from_trends
from rs_stages.ui import charts


def test_index_tickers_are_not_mapped_as_nse_symbols():
    """An index carries no .NS suffix; the constituent mapper must not touch it."""
    for ticker in INDEX_TICKERS.values():
        assert ticker.startswith("^")
        # The universe mapper would corrupt it, which is why indices bypass it.
        assert yfinance_symbol(ticker) != ticker


def test_nifty_500_is_the_configured_benchmark():
    assert INDEX_TICKERS["NIFTY_500"] == "^CRSLDX"


def _trend(n, ma, idx):
    return pd.DataFrame({"Close": [10.0] * n, "MA_10W": [ma] * n, "MA_30W": [ma] * n}, index=idx)


def test_thinly_measurable_sessions_are_dropped_from_breadth():
    """A percentage over a handful of stocks is not breadth."""
    idx = pd.bdate_range("2026-01-01", periods=6)
    warm = [float("nan")] * 4 + [9.0, 9.0]          # measurable only at the end
    trends = {
        "A": _trend(6, 9.0, idx),
        "B": pd.DataFrame({"Close": [10.0] * 6, "MA_10W": warm, "MA_30W": warm}, index=idx),
        "C": pd.DataFrame({"Close": [10.0] * 6, "MA_10W": warm, "MA_30W": warm}, index=idx),
        "D": pd.DataFrame({"Close": [10.0] * 6, "MA_10W": warm, "MA_30W": warm}, index=idx),
    }
    history = breadth_history_from_trends(trends, sessions=6, min_coverage=0.5)
    # Only the last two sessions have at least half the panel measurable.
    assert len(history) == 2
    assert history["Symbols"].min() >= 2


def test_full_coverage_is_never_dropped():
    idx = pd.bdate_range("2026-01-01", periods=4)
    trends = {s: _trend(4, 9.0, idx) for s in ("A", "B")}
    assert len(breadth_history_from_trends(trends, sessions=4, min_coverage=0.5)) == 4


# --- the chart must give the index its own axis ------------------------------

def _series(n):
    idx = pd.bdate_range("2026-01-01", periods=n)
    return [{"time": d.strftime("%Y-%m-%d"), "value": float(i)} for i, d in enumerate(idx)]


def _generated(html: str) -> str:
    source = charts.library_source()
    return html.replace(source, "[VENDORED]") if source else html


def test_a_percentage_and_a_price_level_do_not_share_an_axis():
    html = _generated(charts.line_chart(
        [
            {"data": _series(5), "scale": "left"},
            {"data": _series(5), "scale": "right"},
        ],
        element_id="b",
    ))
    assert '"priceScaleId": "left"' in html
    assert '"priceScaleId": "right"' in html
    # The left axis is only shown when something actually uses it.
    assert "leftPriceScale: {visible: true" in html


def test_the_left_axis_stays_hidden_when_nothing_uses_it():
    html = _generated(charts.line_chart([{"data": _series(5)}], element_id="c"))
    assert "leftPriceScale: {visible: false" in html
    assert "priceScaleId" not in html
