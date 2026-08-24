"""Design tokens, semantic colour mapping and human number formatting.

The visual system — token names, scale, component geometry and motion — is
adopted from the WealthStar reference terminal, whose information density and
row/shelf layout are the design source for this project. Everything the tokens
are *applied to* is ours: NSE industries, the locked Stage vocabulary, the
nine-label guide Action framework and the RS bands in `docs/LOCKED_SPEC.md`.

No function here reads market data or performs a quantitative calculation.
"""
from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

# --- semantic colours -------------------------------------------------------
# One colour per locked Stage, reused everywhere that Stage appears so a dot in
# a table row and a heading on the stock page always mean the same thing.
STAGE_COLORS = {
    "Stage 1": "#2D6CDF",
    "Stage 2": "#07976B",
    "Stage 3": "#C98A1E",
    "Stage 4": "#E0524D",
}
STAGE_NAMES = {
    "Stage 1": "Basing",
    "Stage 2": "Advancing",
    "Stage 3": "Topping",
    "Stage 4": "Declining",
}

#: Action colour and chip background, following docs/UI_SPEC.md's visual
#: language: green buy, blue hold, amber wait/watch, orange reduce, red exit.
ACTION_STYLES = {
    "BUY★": ("#07976B", "var(--up-bg)"),
    "BUY": ("#07976B", "var(--up-bg)"),
    "HOLD": ("#2D6CDF", "var(--blue-bg)"),
    "WAIT": ("#B5781A", "var(--amber-bg)"),
    "WATCH★": ("#B5781A", "var(--amber-bg)"),
    "WATCH": ("#B5781A", "var(--amber-bg)"),
    "REDUCE": ("#C2562F", "var(--slip-bg)"),
    "SELL": ("#E0524D", "var(--down-bg)"),
    "AVOID": ("#E0524D", "var(--down-bg)"),
}

POSITIVE = "#07976B"
NEGATIVE = "#E0524D"
CAUTION = "#B5781A"
NEUTRAL = "#2D6CDF"

#: RS bands are the locked v2 interpretation, not the retired 85/70 thresholds.
RS_BANDS = ((80, "Leadership", POSITIVE), (50, "Adequate", NEUTRAL), (0, "Lagging", "#9aa1ac"))


def stage_key(value: Any) -> str:
    """Reduce a locked Stage label to its bare 'Stage N' key."""
    text = str(value) if value is not None else ""
    return text.split(" — ", 1)[0].strip()


def stage_color(value: Any) -> str:
    return STAGE_COLORS.get(stage_key(value), "#9aa1ac")


def stage_display(value: Any) -> str:
    """Render a Stage as 'Stage 2 · Advancing', keeping our locked wording."""
    key = stage_key(value)
    name = STAGE_NAMES.get(key)
    if not name:
        return "Unavailable"
    return f"{key} · {name}"


def action_style(action: Any) -> tuple[str, str]:
    return ACTION_STYLES.get(str(action), ("#6b7280", "var(--track)"))


def rs_band(rs: Any) -> tuple[str, str]:
    """Return the (band name, colour) for an RS score."""
    value = to_float(rs)
    if not math.isfinite(value):
        return "Unavailable", "#9aa1ac"
    for threshold, name, color in RS_BANDS:
        if value >= threshold:
            return name, color
    return "Unavailable", "#9aa1ac"


# --- number formatting ------------------------------------------------------
# Locked spec: RS as an integer, percentages as percentages, ratios with x,
# rupee values in Cr/L notation. Missing values render as an em dash and are
# never silently shown as zero.
DASH = "—"


def to_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result


def fmt_number(value: Any, digits: int = 2) -> str:
    value = to_float(value)
    if not math.isfinite(value):
        return DASH
    return f"{value:,.{digits}f}"


def fmt_pct(value: Any, digits: int = 1, signed: bool = True) -> str:
    """Format a value already expressed in percentage points."""
    value = to_float(value)
    if not math.isfinite(value):
        return DASH
    return f"{value:+.{digits}f}%" if signed else f"{value:.{digits}f}%"


def fmt_return(value: Any, digits: int = 1) -> str:
    """Format a decimal return (0.12) as a percentage (+12.0%)."""
    value = to_float(value)
    if not math.isfinite(value):
        return DASH
    return f"{value * 100.0:+.{digits}f}%"


def fmt_ratio(value: Any, digits: int = 2) -> str:
    value = to_float(value)
    if math.isnan(value):
        return DASH
    if math.isinf(value):
        return "∞"
    return f"{value:.{digits}f}×"


def fmt_rs(value: Any) -> str:
    value = to_float(value)
    if not math.isfinite(value):
        return DASH
    return f"{value:.0f}"


def fmt_price(value: Any) -> str:
    value = to_float(value)
    if not math.isfinite(value):
        return DASH
    return f"₹{value:,.2f}"


def fmt_inr(value: Any) -> str:
    """Format a rupee amount in Indian Cr/L notation."""
    value = to_float(value)
    if not math.isfinite(value):
        return DASH
    magnitude = abs(value)
    if magnitude >= 1e7:
        return f"₹{value / 1e7:,.2f} Cr"
    if magnitude >= 1e5:
        return f"₹{value / 1e5:,.2f} L"
    return f"₹{value:,.0f}"


def fmt_date(value: Any) -> str:
    stamp = pd.to_datetime(value, errors="coerce")
    return DASH if pd.isna(stamp) else stamp.strftime("%d %b %Y")


def signed_color(value: Any) -> str:
    value = to_float(value)
    if not math.isfinite(value) or value == 0:
        return "var(--sub)"
    return POSITIVE if value > 0 else NEGATIVE


def initials(symbol: Any) -> str:
    """Two-letter tile label, matching the reference row's leading avatar."""
    text = "".join(ch for ch in str(symbol) if ch.isalnum()).upper()
    return text[:2] if text else "??"


# --- stylesheet -------------------------------------------------------------
# Token names and values follow the reference terminal so the components below
# can be lifted across without translation. The canvas stays light, per
# docs/LOCKED_SPEC.md section 14.
CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --ease:cubic-bezier(.22,1,.36,1);
  --page:#f4f5f7;--paper:#fbfcfd;--card:#fff;
  --ink:#1a1d21;--sub:#6b7280;--faint:#9aa1ac;
  --rule:#eef0f3;--rule-strong:#e4e7eb;--edge:#e2e5ea;--track:#eaecef;--row-hover:#fafbfc;
  --up-bg:#dcf5ea;--down-bg:#fbe7e5;--blue-bg:#e6eefb;--amber-bg:#fbefd6;--teal-bg:#d6f0f1;--slip-bg:#fbe3d8;--bar-bg:#e8edf6;
}
html,body,[class*="css"],.stApp,button,input,select,textarea{
  font-family:'Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif !important;
  -webkit-font-smoothing:antialiased;
}
.stApp{background:var(--page);color:var(--ink)}
.block-container{max-width:1100px;padding:0 20px 56px}
[data-testid="stSidebar"],[data-testid="stToolbar"],header[data-testid="stHeader"],[data-testid="stDecoration"]{display:none}
.num{font-feature-settings:"tnum";font-variant-numeric:tabular-nums}
/* Streamlit styles markdown links with its primary colour and an underline;
   every link here is a navigation surface inside a component, not body copy. */
[data-testid="stMarkdownContainer"] a,[data-testid="stMarkdownContainer"] a:hover,
[data-testid="stMarkdownContainer"] a:visited{color:inherit !important;text-decoration:none !important}
.ws-brand,.ws-sym-cell,.ws-pill-link,.ws-iname a,.ws-shelf{text-decoration:none !important}

/* --- header ------------------------------------------------------------- */
.ws-header{margin:0 -20px 0;background:var(--card);border-bottom:1px solid var(--rule)}
.ws-header-inner{max-width:1100px;margin:0 auto;padding:13px 20px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.ws-brand{display:flex;align-items:center;gap:9px;text-decoration:none;color:var(--ink)}
.ws-mark{width:30px;height:30px;border-radius:9px;background:var(--ink);color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;letter-spacing:-.02em}
.ws-wordmark{font-weight:800;font-size:18px;letter-spacing:-.5px;line-height:1}
.ws-tagline{font-size:10.5px;color:var(--faint);font-weight:600;margin-top:2px}
.ws-stamp{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--sub);font-weight:600}
.ws-dot{width:8px;height:8px;border-radius:8px;display:inline-block;flex-shrink:0}

/* --- page furniture ----------------------------------------------------- */
.ws-page-title{font-size:22px;font-weight:800;letter-spacing:-.5px;margin:0}
.ws-page-sub{font-size:12.5px;color:var(--sub);margin-top:3px;line-height:1.5;max-width:760px}
.ws-eyebrow{font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:var(--faint);font-weight:700;margin-bottom:10px}
.ws-card{background:var(--card);border:1px solid var(--rule);border-radius:14px;padding:16px 18px;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.ws-card + .ws-card{margin-top:14px}
.ws-card-title{font-size:12.5px;font-weight:700;color:var(--ink);margin-bottom:12px}
.ws-note{font-size:11.5px;color:var(--faint);line-height:1.6}
.ws-foot{font-size:11.5px;color:var(--faint);line-height:1.7;border-top:1px solid var(--rule);margin-top:28px;padding-top:14px}
.ws-foot b{color:var(--sub)}
.ws-missing{background:var(--card);border:1px dashed var(--rule-strong);border-radius:14px;padding:16px 18px;font-size:12.5px;color:var(--sub);line-height:1.6}
.ws-missing b{color:var(--ink)}

/* --- lift/motion, as the reference uses on rows and cards ---------------- */
.lift{transition:transform .18s var(--ease),box-shadow .2s var(--ease),border-color .2s var(--ease)}
.lift:hover{transform:translateY(-3px);box-shadow:0 10px 30px rgba(0,0,0,.13);border-color:var(--rule-strong)}
.pop{transition:transform .14s var(--ease),box-shadow .18s var(--ease),border-color .18s var(--ease)}
.pop:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.14);border-color:var(--rule-strong)}
@keyframes growX{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.bar-grow{transform-origin:left center;animation:growX .8s var(--ease) .05s both}
@keyframes rf{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.rfade{animation:rf .45s var(--ease) both}
@media (prefers-reduced-motion:reduce){.lift:hover,.pop:hover{transform:none}.bar-grow,.rfade{animation:none}}

/* --- dense table -------------------------------------------------------- */
.ws-table-wrap{background:var(--card);border:1px solid var(--rule);border-radius:14px;overflow:hidden;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.ws-scroll{overflow-x:auto}
table.ws-table{width:100%;border-collapse:collapse;min-width:680px}
table.ws-table thead tr{background:var(--paper);border-bottom:1px solid var(--rule)}
table.ws-table th{text-align:left;padding:12px 13px;font-size:11.5px;font-weight:600;color:var(--sub);white-space:nowrap}
table.ws-table th.right,table.ws-table td.right{text-align:right}
table.ws-table th.active{color:var(--ink)}
table.ws-table tbody tr{border-bottom:1px solid var(--rule);transition:background .18s var(--ease)}
table.ws-table tbody tr:last-child{border-bottom:0}
table.ws-table tbody tr:hover{background:var(--row-hover)}
table.ws-table td{padding:12px 13px;font-size:13px;vertical-align:middle}
.ws-sym-cell{display:flex;align-items:center;gap:11px;text-decoration:none;color:var(--ink)}
.ws-tile{width:30px;height:30px;border-radius:9px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;letter-spacing:-.3px}
.ws-sym{font-weight:700;font-size:13.5px;line-height:1.2}
.ws-sym-sub{font-size:10.5px;color:var(--faint);line-height:1.2}
.ws-rs{font-weight:700;font-size:14.5px}
.ws-rs-bar{display:block;height:3px;max-width:60px;border-radius:3px;margin-top:4px;opacity:.55}
.ws-chip{font-size:12px;font-weight:700;padding:3px 10px;border-radius:7px;white-space:nowrap;display:inline-block}
.ws-stage{display:flex;align-items:center;gap:7px;font-size:13px;white-space:nowrap}
.ws-range{display:flex;align-items:center;gap:6px;width:96px}
.ws-range-track{position:relative;flex:1;height:3px;border-radius:3px;background:var(--track)}
.ws-range-dot{position:absolute;top:50%;width:7px;height:7px;border-radius:7px;background:var(--ink);transform:translate(-50%,-50%)}
.ws-range-cap{font-size:9.5px;color:var(--faint)}
@media (max-width:640px){.col-hide-sm{display:none !important}}

/* --- shelves, chips, stat cards ----------------------------------------- */
.ws-chips{display:flex;flex-wrap:wrap;gap:8px}
.ws-pill-link{display:inline-flex;align-items:baseline;gap:7px;text-decoration:none;color:var(--ink);background:var(--page);border:1px solid var(--rule);border-radius:9px;padding:7px 11px}
.ws-pill-link .sym{font-size:12.5px;font-weight:700}
.ws-pill-link .meta{font-size:11px;color:var(--faint)}
.ws-shelf{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;padding:11px 0;border-top:1px solid var(--rule)}
.ws-shelf:first-of-type{border-top:none}
.ws-shelf-label{font-size:12.5px;font-weight:700;flex:0 0 auto;min-width:150px}
.ws-shelf-count{font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:20px;flex:0 0 auto}
.ws-stat-row{display:flex;gap:12px;flex-wrap:wrap}
.ws-stat{background:var(--card);border:1px solid var(--rule);border-radius:14px;padding:15px 16px;flex:1 1 170px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.ws-stat-label{display:flex;align-items:center;gap:5px;font-size:12px;color:var(--sub);font-weight:600;margin-bottom:8px}
.ws-stat-value{font-size:30px;font-weight:800;letter-spacing:-1px;line-height:1}
.ws-stat-value small{font-size:16px;font-weight:700}
.ws-stat-note{font-size:12px;color:var(--sub);margin-top:6px}
.ws-legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--sub)}
.ws-legend span.item{display:flex;align-items:center;gap:6px}
.ws-legend b{color:var(--ink)}
.ws-segbar{display:flex;height:9px;border-radius:6px;overflow:hidden;gap:2px;margin-top:11px}
.ws-segbar div{opacity:.9;border-radius:3px}

/* --- industry / sector row ---------------------------------------------- */
.ws-irow{display:flex;align-items:center;gap:12px;padding:12px 4px;border-top:1px solid var(--rule)}
.ws-irow-head{display:flex;align-items:center;gap:12px;padding:8px 4px 6px;font-size:11.5px;color:var(--faint);font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.ws-irank{width:24px;text-align:right;color:var(--faint);font-weight:700;font-size:14px;flex-shrink:0}
.ws-iname{flex:0 1 200px;min-width:0}
.ws-iname a{font-weight:700;font-size:14px;color:var(--ink);text-decoration:none;display:block;line-height:1.25}
.ws-iname .sub{font-size:11.5px;color:var(--faint)}
.ws-irs{flex:1 1 auto;min-width:90px;display:flex;align-items:center;gap:9px}
.ws-irs-track{flex:1;height:8px;background:var(--bar-bg);border-radius:6px;overflow:hidden}
.ws-irs-fill{height:100%;border-radius:6px}
.ws-irs-value{font-weight:800;font-size:15px;width:34px;text-align:right}
.ws-inum{width:72px;text-align:right;font-size:12.5px;flex-shrink:0}
@media (max-width:640px){.ws-iname{flex:1 1 auto}.ws-irs{flex:0 0 auto;min-width:0}}

/* --- signal card (guide Option B) ---------------------------------------- */
.ws-sigline{display:flex;align-items:baseline;justify-content:space-between;gap:14px;padding:8px 0;border-bottom:1px solid var(--rule)}
.ws-sigline:last-child{border-bottom:0}
.ws-sigline-label{font-size:12.5px;color:var(--sub);font-weight:600}
.ws-sigline-value{font-size:13.5px;font-weight:700;text-align:right}
.ws-signote{border:1px solid;border-radius:10px;padding:10px 13px;margin-top:9px;display:flex;gap:9px;align-items:baseline;flex-wrap:wrap}
.ws-signote-title{font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;flex-shrink:0}
.ws-signote-body{font-size:12.5px;color:var(--ink);line-height:1.55;flex:1 1 220px;min-width:0}
.ws-thr{display:grid;grid-template-columns:1.6fr 0.8fr 1.5fr 44px;gap:12px;align-items:center;padding:11px 4px;border-top:1px solid var(--rule)}
.ws-thr-head{border-top:none;font-size:11.5px;color:var(--faint);font-weight:600;text-transform:uppercase;letter-spacing:.4px;padding:8px 4px 6px}
.ws-thr-signal{font-size:13px;font-weight:600;min-width:0}
.ws-thr-note{font-size:10.5px;color:var(--faint);font-weight:400;line-height:1.4;margin-top:2px}
.ws-thr-value{font-size:13.5px;font-weight:700}
.ws-thr-rule{font-size:11.5px;color:var(--sub)}
.ws-thr-status{text-align:right}
@media (max-width:760px){.ws-thr{grid-template-columns:1.4fr 0.9fr 36px}.ws-thr-rule{display:none}.ws-thr-head .ws-thr-rule{display:none}}

/* --- evidence cards ------------------------------------------------------ */
.ws-ev{display:flex;align-items:baseline;justify-content:space-between;gap:14px;padding:9px 0;border-bottom:1px solid var(--rule)}
.ws-ev:last-child{border-bottom:0;padding-bottom:0}
.ws-ev-label{font-size:12.5px;color:var(--ink);min-width:0}
.ws-ev-note{font-size:10.5px;color:var(--faint);line-height:1.45;margin-top:2px}
.ws-ev-value{font-size:13.5px;font-weight:700;text-align:right;white-space:nowrap;flex-shrink:0}
.ws-state{display:inline-block;font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:20px;white-space:nowrap}
.ws-ev-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media (max-width:760px){.ws-ev-grid{grid-template-columns:1fr}.ws-ev{gap:10px}}

/* --- checklist / evidence ----------------------------------------------- */
.ws-check{display:flex;align-items:center;gap:9px;padding:7px 0;border-bottom:1px solid var(--rule);font-size:13px}
.ws-check:last-child{border-bottom:0}
.ws-check-mark{width:18px;height:18px;border-radius:9px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700}
.ws-kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px}
.ws-kv-label{font-size:11px;color:var(--faint);margin-bottom:4px}
.ws-kv-value{font-size:16px;font-weight:700;line-height:1.1}
.ws-kv-note{font-size:10.5px;color:var(--faint);margin-top:2px}
.ws-metric{text-align:right}
.ws-metric .label{font-size:11px;color:var(--faint);margin-bottom:3px}
.ws-metric .value{font-size:26px;font-weight:800;line-height:1}
.ws-metric .value.small{font-size:18px}
.ws-ribbon{display:flex;align-items:center;gap:8px;border-radius:10px;padding:9px 14px;font-size:13px}
.ws-dgrid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:640px){.ws-dgrid{grid-template-columns:1fr}}

/* --- streamlit widget restyling ----------------------------------------- */
div[data-testid="stSegmentedControl"] button{font-size:13px !important;font-weight:600 !important;border-radius:999px !important;padding:5px 15px !important}
div[data-testid="stSegmentedControl"]>div{background:var(--card);border:1px solid var(--rule);border-radius:999px;padding:3px;gap:2px}
[data-testid="stNumberInput"] input{background:var(--card);border-radius:22px;font-size:13px}
[data-baseweb="select"]>div{background:var(--card);border-color:var(--edge);border-radius:22px;min-height:38px;font-size:13px}
[data-testid="stTextInput"] input{background:var(--card);border-color:var(--edge);border-radius:22px;font-size:13px}
[data-testid="stSlider"]{padding-top:2px}
div[data-testid="stMetric"]{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px 14px}
label[data-testid="stWidgetLabel"] p{font-size:12.5px !important;font-weight:600 !important;color:var(--sub) !important}
button[data-testid="stBaseButton-secondary"]{border-radius:22px;border-color:var(--edge);font-size:13px;font-weight:600}
</style>
"""

def stylesheet() -> str:
    """Return the stylesheet as a single, uninterrupted HTML block.

    CommonMark terminates an HTML block at the first blank line, so a stylesheet
    with blank lines between its sections would be split and the remainder
    rendered as visible page text. The source keeps the blank lines for
    readability; they are removed here, at injection time.
    """
    return collapse_blank_lines(CSS)


def collapse_blank_lines(markup: str) -> str:
    """Remove blank lines so a multi-line fragment stays one HTML block."""
    return re.sub(r"\n\s*\n+", "\n", markup).strip()


FOOTER = (
    '<div class="ws-foot"><b>Research and decision-support software — not investment advice, '
    "and not a recommendation to buy or sell.</b> Relative strength and Stage are descriptive "
    "measures of completed price behaviour, not predictions of future returns. Every figure is "
    "derived from the validated repository snapshot for the stated decision date. Verify the "
    "underlying data, methodology and current market conditions before acting.</div>"
)
