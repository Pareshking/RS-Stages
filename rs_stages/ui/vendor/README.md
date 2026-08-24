# Vendored third-party assets

## `lightweight-charts.standalone.production.js`

TradingView Lightweight Charts v5.2.0, standalone production build.
Licensed under Apache License 2.0 — https://www.apache.org/licenses/LICENSE-2.0
Source: https://unpkg.com/lightweight-charts@5.2.0/dist/lightweight-charts.standalone.production.js

It is vendored rather than loaded from a CDN so charts render in deployments
with restricted outbound network access, and so a chart cannot silently
disappear because a third-party host is unreachable. The file is unmodified;
its license header is preserved in the file itself.

`rs_stages/ui/charts.py` inlines this file into the chart component. If it is
ever removed, the component falls back to the CDN and, failing that, renders an
explicit notice rather than an empty box.
