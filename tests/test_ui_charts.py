"""The chart component must be self-contained and must never fake a series."""
import json
import re

from rs_stages.ui import charts


def _generated(html: str) -> str:
    """Strip the vendored library so assertions inspect only our own script.

    The library's own minified source contains substrings like ``addSeries`` and
    ``lineStyle``, so asserting against the whole document would pass or fail for
    the wrong reason.
    """
    source = charts.library_source()
    return html.replace(source, "[VENDORED]") if source else html


def _series(n: int, start: str = "2026-01-01") -> list[dict]:
    import pandas as pd

    idx = pd.bdate_range(start, periods=n)
    return [{"time": d.strftime("%Y-%m-%d"), "value": float(i)} for i, d in enumerate(idx)]


def test_library_is_vendored_not_fetched_at_view_time():
    source = charts.library_source()
    assert source is not None, "the charting library must be vendored in the repository"
    assert "LightweightCharts" in source
    # Apache-2.0 attribution must survive vendoring.
    assert "Apache License 2.0" in source[:600]


def test_chart_inlines_the_library_and_makes_no_external_request():
    html = charts.line_chart([{"data": _series(30)}], element_id="t1")
    assert charts.CDN_URL not in _generated(html)
    assert "<script>" in html
    # Nothing before the first script tag reaches out to a remote host either.
    assert "https://" not in html.split("<script>")[0]


def test_empty_series_are_skipped_rather_than_drawn():
    html = charts.line_chart(
        [{"data": _series(10), "color": "#111111"}, {"data": [], "color": "#222222"}],
        element_id="t2",
    )
    generated = _generated(html)
    assert generated.count("addSeries") == 1
    assert "#111111" in generated
    assert "#222222" not in generated


def test_a_chart_with_no_data_at_all_renders_no_series():
    generated = _generated(charts.line_chart([{"data": []}], element_id="t3"))
    assert "addSeries" not in generated
    assert "var d = [];" in generated


def test_missing_library_falls_back_to_the_cdn(monkeypatch):
    monkeypatch.setattr(charts, "library_source", lambda: None)
    html = charts.line_chart([{"data": _series(5)}], element_id="t4")
    assert charts.CDN_URL in html


def test_unavailable_notice_is_present_and_escaped_as_json():
    html = charts.line_chart(
        [{"data": _series(5)}], element_id="t5", unavailable='He said "no chart"'
    )
    assert json.dumps('He said "no chart"') in html


def test_element_id_and_payload_are_json_encoded_not_interpolated_raw():
    """Values reaching the script must go through json.dumps, not f-string concat."""
    html = charts.line_chart([{"data": _series(3)}], element_id="my-chart")
    assert json.dumps("my-chart") in html
    payload = re.search(r"var d = (\[.*?\]);", html, re.S)
    assert payload, "series payload must be present"
    parsed = json.loads(payload.group(1))
    assert len(parsed) == 1 and len(parsed[0]) == 3


def test_dashed_series_requests_a_dashed_line_style():
    plain = _generated(charts.line_chart([{"data": _series(4)}], element_id="t6"))
    dashed = _generated(charts.line_chart([{"data": _series(4), "dashed": True}], element_id="t7"))
    assert "lineStyle" not in plain
    assert '"lineStyle": 2' in dashed
