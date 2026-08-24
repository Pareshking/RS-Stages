"""Chart components built on TradingView Lightweight Charts.

The library is vendored (see ``vendor/README.md``) and inlined into the
component, so a chart renders in deployments with restricted outbound network
access and cannot silently disappear because a third-party host is unreachable.
If the vendored file is absent the component falls back to the CDN, and if that
also fails it renders an explicit notice rather than an empty box.

The library draws; it never calculates. Every series passed in was produced by
the locked quant functions.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Sequence

VENDOR_SCRIPT = Path(__file__).with_name("vendor") / "lightweight-charts.standalone.production.js"
CDN_URL = "https://unpkg.com/lightweight-charts@5.2.0/dist/lightweight-charts.standalone.production.js"

#: Shared chart chrome, matching the terminal's tokens.
LAYOUT = {
    "background": {"type": "solid", "color": "#ffffff"},
    "textColor": "#6b7280",
    "fontFamily": "Plus Jakarta Sans,system-ui,-apple-system,sans-serif",
    "fontSize": 11,
}
GRID = {"vertLines": {"color": "#f6f7f9"}, "horzLines": {"color": "#f6f7f9"}}
SCALE_BORDER = "#eef0f3"


@lru_cache(maxsize=1)
def library_source() -> str | None:
    """Return the vendored library source, or None if it is not present."""
    try:
        return VENDOR_SCRIPT.read_text(encoding="utf-8")
    except OSError:
        return None


def _loader() -> str:
    source = library_source()
    if source is not None:
        return f"<script>{source}</script>"
    return f'<script src="{CDN_URL}"></script>'


def _series_js(series: Sequence[dict]) -> str:
    """Build the addSeries calls for a list of series descriptors."""
    calls = []
    for index, spec in enumerate(series):
        options = {
            "color": spec.get("color", "#1a1d21"),
            "lineWidth": spec.get("width", 2),
            "priceLineVisible": False,
            "lastValueVisible": spec.get("last_value", False),
        }
        if spec.get("dashed"):
            options["lineStyle"] = 2
        calls.append(
            f"chart.addSeries(LightweightCharts.LineSeries,{json.dumps(options)})"
            f".setData(d[{index}]);"
        )
    return "".join(calls)


def line_chart(
    series: Sequence[dict],
    element_id: str,
    height: int = 320,
    unavailable: str = "The charting library is unavailable in this environment.",
) -> str:
    """Render one or more line series into a bordered chart panel.

    Each entry in ``series`` is ``{"data": [{"time","value"}, …], "color", …}``.
    Series with no points are skipped rather than drawn as an empty line.
    """
    drawable = [spec for spec in series if spec.get("data")]
    payload = json.dumps([spec["data"] for spec in drawable])
    notice = json.dumps(unavailable)
    return f"""
<div id="{element_id}" style="height:{height}px;background:#fff;border:1px solid #eef0f3;border-radius:14px"></div>
{_loader()}
<script>
(function() {{
  var el = document.getElementById({json.dumps(element_id)});
  if (!el) return;
  if (!window.LightweightCharts) {{
    el.innerHTML = '<div style="padding:16px;font:13px Plus Jakarta Sans,system-ui,sans-serif;'
      + 'color:#6b7280">' + {notice} + '</div>';
    return;
  }}
  var d = {payload};
  var chart = LightweightCharts.createChart(el, {{
    autoSize: true,
    layout: {json.dumps(LAYOUT)},
    grid: {json.dumps(GRID)},
    rightPriceScale: {{borderColor: {json.dumps(SCALE_BORDER)}}},
    timeScale: {{borderColor: {json.dumps(SCALE_BORDER)}, rightOffset: 3}},
    crosshair: {{mode: LightweightCharts.CrosshairMode.Normal}}
  }});
  {_series_js(drawable)}
  chart.timeScale().fitContent();
  window.addEventListener('resize', function() {{ chart.timeScale().fitContent(); }});
}})();
</script>"""
