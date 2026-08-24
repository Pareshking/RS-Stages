from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from rs_stages.data import download_yfinance_history
from rs_stages.quant import ma_30w_series

st.set_page_config(
    page_title="RS-Stages — Quantitative Research",
    page_icon="RS",
    layout="wide",
    initial_sidebar_state="collapsed",
)

RESEARCH_PATH = Path("data/latest_research.csv")
UNIVERSE_PATH = Path("data/ind_niftytotalmarket_list.csv")

# -----------------------------------------------------------------------------
# Visual system: deliberately closer to a modern research product than stock
# Streamlit. White canvas, compact type, restrained borders, dense information.
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
:root { color-scheme: light; }
.stApp { background:#ffffff; color:#111827; }
.block-container { max-width:1500px; padding:1.15rem 2.1rem 3.5rem; }
[data-testid="stHeader"] { background:#fff; }
[data-testid="stSidebar"] { display:none; }
[data-testid="stToolbar"] { visibility:hidden; height:0; }
[data-testid="stDecoration"] { display:none; }

.rs-top { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:.2rem 0 .7rem; }
.rs-logo { display:flex; align-items:center; gap:.55rem; }
.rs-logo-mark { width:30px; height:30px; border:1.5px solid #111827; border-radius:8px; display:grid; place-items:center; font-size:.72rem; font-weight:800; letter-spacing:-.04em; }
.rs-logo-name { font-size:1rem; font-weight:760; letter-spacing:-.025em; }
.rs-meta { color:#7b8492; font-size:.72rem; }
.rs-eyebrow { color:#7a8491; font-size:.62rem; font-weight:750; letter-spacing:.16em; text-transform:uppercase; margin-top:1.35rem; }
.rs-hero { color:#101828; font-size:clamp(2rem,4vw,3.35rem); font-weight:780; letter-spacing:-.065em; line-height:.98; margin:.3rem 0 .65rem; max-width:900px; }
.rs-lead { color:#667085; font-size:.92rem; line-height:1.62; max-width:820px; margin:0 0 1.1rem; }
.rs-section { color:#111827; font-size:1.03rem; font-weight:730; letter-spacing:-.025em; margin:1.55rem 0 .5rem; }
.rs-small { color:#7a8491; font-size:.72rem; line-height:1.5; }
.rs-rule { height:1px; background:#eaecf0; margin:.9rem 0 1rem; }
.rs-chip { display:inline-flex; align-items:center; gap:.35rem; border:1px solid #e4e7ec; border-radius:999px; padding:.27rem .62rem; color:#475467; background:#fff; font-size:.68rem; font-weight:650; }
.rs-chip-green { color:#17663d; border-color:#cfe8d9; background:#f5fbf7; }
.rs-chip-amber { color:#806a17; border-color:#eee5bd; background:#fffdf4; }
.rs-chip-red { color:#8b3030; border-color:#f0d1d1; background:#fff7f7; }

.metric-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:.65rem 0 1.1rem; }
.metric-card { border:1px solid #e6e9ee; border-radius:12px; padding:13px 15px 12px; background:#fff; min-height:78px; }
.metric-label { color:#7b8492; font-size:.62rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }
.metric-value { color:#101828; font-size:1.45rem; line-height:1.1; font-weight:760; letter-spacing:-.045em; margin-top:6px; }
.metric-sub { color:#98a2b3; font-size:.65rem; margin-top:4px; }

.action { display:inline-flex; align-items:center; justify-content:center; min-width:62px; padding:.23rem .52rem; border-radius:999px; border:1px solid; font-size:.66rem; font-weight:800; letter-spacing:.02em; }
.buy { color:#17663d; background:#f3fbf6; border-color:#cce8d7; }
.hold { color:#315d7f; background:#f4f8fc; border-color:#d9e6f0; }
.wait { color:#806a17; background:#fffdf4; border-color:#eee5bd; }
.reduce { color:#8a4a17; background:#fff7ef; border-color:#f0dcc7; }
.sell { color:#8b3030; background:#fff5f5; border-color:#efd1d1; }

.info-panel { border:1px solid #e6e9ee; border-radius:12px; padding:15px 17px; background:#fff; }
.info-title { font-size:.86rem; font-weight:720; margin-bottom:.35rem; }
.info-text { color:#667085; font-size:.75rem; line-height:1.55; }

.stTabs [data-baseweb="tab-list"] { gap:1.25rem; border-bottom:1px solid #e7e9ee; }
.stTabs [data-baseweb="tab"] { height:2.7rem; padding:0 .02rem; color:#667085; font-size:.83rem; font-weight:620; }
.stTabs [aria-selected="true"] { color:#101828; }
.stTabs [data-baseweb="tab-highlight"] { background:#101828; height:2px; }

[data-testid="stDataFrame"] { border:1px solid #e6e9ee; border-radius:10px; overflow:hidden; }
[data-testid="stSelectbox"] label, [data-testid="stTextInput"] label, [data-testid="stNumberInput"] label { color:#667085; font-size:.7rem; font-weight:600; }
div[data-baseweb="select"] > div { min-height:40px; border-color:#e1e5ea; border-radius:8px; background:#fff; }
[data-testid="stTextInput"] input { border-color:#e1e5ea; border-radius:8px; }
[data-testid="stCheckbox"] label { color:#667085; font-size:.74rem; }
button[kind="secondary"] { border-color:#e1e5ea; }

.stock-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; margin:.45rem 0 1rem; }
.stock-symbol { color:#101828; font-size:1.65rem; font-weight:780; letter-spacing:-.045em; }
.stock-company { color:#667085; font-size:.78rem; margin-top:.2rem; }
.stock-industry { color:#98a2b3; font-size:.7rem; margin-top:.2rem; }

.detail-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); border:1px solid #e6e9ee; border-radius:11px; overflow:hidden; }
.detail-item { padding:10px 13px; border-bottom:1px solid #eef0f3; }
.detail-item:nth-child(odd) { border-right:1px solid #eef0f3; }
.detail-label { color:#7b8492; font-size:.67rem; }
.detail-value { color:#1d2939; font-size:.8rem; font-weight:650; margin-top:3px; }

.footer-note { color:#98a2b3; font-size:.66rem; line-height:1.55; margin-top:2rem; }

@media (max-width: 850px) {
  .block-container { padding:.9rem .85rem 3rem; }
  .rs-top { margin-bottom:.3rem; }
  .rs-meta { display:none; }
  .rs-eyebrow { margin-top:.9rem; }
  .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
  .metric-card { min-height:72px; padding:11px 12px; }
  .metric-value { font-size:1.25rem; }
  .stTabs [data-baseweb="tab-list"] { gap:.85rem; overflow-x:auto; scrollbar-width:none; }
  .stTabs [data-baseweb="tab"] { font-size:.76rem; }
  .stock-head { display:block; }
  .detail-grid { grid-template-columns:1fr; }
  .detail-item:nth-child(odd) { border-right:0; }
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_research() -> pd.DataFrame:
    if not RESEARCH_PATH.exists():
        raise FileNotFoundError("Validated research snapshot is not published.")
    frame = pd.read_csv(RESEARCH_PATH)
    required = {"Symbol", "Date", "RS_Score", "Stage", "Industry"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Research snapshot missing columns: {sorted(missing)}")
    frame["Symbol"] = frame["Symbol"].astype(str).str.strip()
    return frame.set_index("Symbol")


@st.cache_data(ttl=3600, show_spinner=False)
def load_stock_history(symbol: str, end_date: str) -> pd.DataFrame:
    return download_yfinance_history(
        symbol,
        start=pd.Timestamp(end_date) - pd.Timedelta(days=650),
        end=pd.Timestamp(end_date) + pd.Timedelta(days=1),
    )


def stage_short(value: object) -> str:
    text = str(value) if isinstance(value, str) else "Unknown"
    return (
        text.replace("Stage 1 — Basing", "Stage 1")
        .replace("Stage 2 — Advancing", "Stage 2")
        .replace("Stage 3 — Topping", "Stage 3")
        .replace("Stage 4 — Declining", "Stage 4")
    )


def action_for(row: pd.Series) -> str:
    stage = stage_short(row.get("Stage"))
    try:
        rs = float(row.get("RS_Score"))
    except (TypeError, ValueError):
        rs = np.nan
    breakout_confirmed = bool(row.get("Breakout_Confirmed", False))
    if stage == "Stage 4":
        return "SELL"
    if stage == "Stage 3":
        return "REDUCE"
    if stage == "Stage 2" and np.isfinite(rs) and rs >= 85 and breakout_confirmed:
        return "BUY"
    if stage == "Stage 2" and np.isfinite(rs) and rs >= 70:
        return "HOLD"
    return "WAIT"


def action_reason(row: pd.Series, action: str) -> str:
    stage = stage_short(row.get("Stage"))
    rs = row.get("RS_Score")
    rs_text = "RS unavailable" if pd.isna(rs) else f"RS {float(rs):.0f}"
    if action == "BUY":
        return f"{stage} + {rs_text} + confirmed breakout: Volume Ratio > 1.5× and U/D > 1.3."
    if action == "HOLD":
        return f"{stage} + {rs_text}; leadership is present, but the confirmed-breakout condition is absent."
    if action == "REDUCE":
        return f"{stage}; topping structure warrants defensive review rather than a fresh entry."
    if action == "SELL":
        return f"{stage}; price/trend structure is in the declining regime."
    return f"{stage} / {rs_text}; wait for stronger Stage/RS confirmation."


def with_actions(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Action"] = out.apply(action_for, axis=1)
    return out


def fmt_num(value: object, decimals: int = 2) -> str:
    try:
        if pd.isna(value):
            return "—"
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(value: object, decimals: int = 1) -> str:
    try:
        if pd.isna(value):
            return "—"
        return f"{float(value) * 100:+.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_pct_plain(value: object, decimals: int = 2) -> str:
    try:
        if pd.isna(value):
            return "—"
        return f"{float(value):+.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_inr(value: object) -> str:
    try:
        if pd.isna(value):
            return "—"
        x = float(value)
        if abs(x) >= 1e7:
            return f"₹{x / 1e7:,.1f} Cr"
        if abs(x) >= 1e5:
            return f"₹{x / 1e5:,.1f} L"
        return f"₹{x:,.0f}"
    except (TypeError, ValueError):
        return "—"


def action_html(action: str) -> str:
    cls = {"BUY": "buy", "HOLD": "hold", "WAIT": "wait", "REDUCE": "reduce", "SELL": "sell"}.get(action, "wait")
    return f'<span class="action {cls}">{html.escape(action)}</span>'


def metric_grid(items: list[tuple[str, str, str]]) -> None:
    cards = []
    for label, value, sub in items:
        cards.append(
            f'<div class="metric-card"><div class="metric-label">{html.escape(label)}</div>'
            f'<div class="metric-value">{html.escape(value)}</div><div class="metric-sub">{html.escape(sub)}</div></div>'
        )
    st.markdown('<div class="metric-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_table(frame: pd.DataFrame, height: int = 520) -> None:
    st.dataframe(frame, use_container_width=True, hide_index=True, height=height)


def chart_html(history: pd.DataFrame, symbol: str) -> str:
    frame = history.copy().sort_index()
    ma = ma_30w_series(frame["Close"])
    frame = frame.tail(420)
    ma = ma.reindex(frame.index)
    candles = []
    ma_data = []
    for idx, row in frame.iterrows():
        vals = [row.get("Open"), row.get("High"), row.get("Low"), row.get("Close")]
        if all(pd.notna(v) for v in vals):
            candles.append({"time": idx.strftime("%Y-%m-%d"), "open": float(vals[0]), "high": float(vals[1]), "low": float(vals[2]), "close": float(vals[3])})
        mv = ma.loc[idx] if idx in ma.index else np.nan
        if pd.notna(mv):
            ma_data.append({"time": idx.strftime("%Y-%m-%d"), "value": float(mv)})
    payload = json.dumps({"candles": candles, "ma": ma_data})
    title = html.escape(symbol)
    return f"""
<div id="rs-chart" style="height:510px;width:100%;border:1px solid #e6e9ee;border-radius:12px;overflow:hidden;background:#fff"></div>
<div style="font:11px system-ui;color:#98a2b3;margin:7px 2px 0">{title} · daily candles · 30-calendar-week MA · TradingView Lightweight Charts</div>
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
<script>
const payload = {payload};
const el = document.getElementById('rs-chart');
const chart = LightweightCharts.createChart(el, {{
  autoSize:true,
  layout: {{ background: {{ type:'solid', color:'#ffffff' }}, textColor:'#667085' }},
  grid: {{ vertLines: {{ color:'#f2f4f7' }}, horzLines: {{ color:'#f2f4f7' }} }},
  rightPriceScale: {{ borderColor:'#eaecf0' }},
  timeScale: {{ borderColor:'#eaecf0', timeVisible:false }},
  crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
}});
const candles = chart.addSeries(LightweightCharts.CandlestickSeries, {{
  upColor:'#159570', downColor:'#e5484d', borderVisible:false, wickUpColor:'#159570', wickDownColor:'#e5484d'
}});
candles.setData(payload.candles);
const ma = chart.addSeries(LightweightCharts.LineSeries, {{ color:'#1f2937', lineWidth:2, priceLineVisible:false, lastValueVisible:false }});
ma.setData(payload.ma);
chart.timeScale().fitContent();
</script>
"""


# -----------------------------------------------------------------------------
# Load the validated production snapshot. No uploads, date entry or manual data
# files are part of the user workflow.
# -----------------------------------------------------------------------------
try:
    result = with_actions(load_research())
except Exception as exc:
    st.error("Validated research snapshot unavailable")
    st.caption(str(exc))
    st.info("The application reads the repository's validated production snapshot. No manual file upload or date entry is required.")
    st.stop()

universe = pd.read_csv(UNIVERSE_PATH) if UNIVERSE_PATH.exists() else pd.DataFrame()
latest = pd.to_datetime(result["Date"], errors="coerce").max()
stage = result["Stage"].map(stage_short)
valid_rs = result["RS_Score"].notna()

# Header
st.markdown(
    '<div class="rs-top"><div class="rs-logo"><div class="rs-logo-mark">RS</div><div class="rs-logo-name">RS-Stages</div></div>'
    f'<div class="rs-meta">Nifty Total Market · validated snapshot · {latest.date().isoformat() if pd.notna(latest) else "—"}</div></div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="rs-eyebrow">NIFTY TOTAL MARKET · QUANTITATIVE RESEARCH PLATFORM</div>', unsafe_allow_html=True)
st.markdown('<div class="rs-hero">Find leadership. Understand the stage.</div>', unsafe_allow_html=True)
st.markdown('<div class="rs-lead">A glass-box research dashboard for relative strength, 30-week market stages, industry breadth, breakouts and transparent research actions. Every important number is traceable to the validated snapshot.</div>', unsafe_allow_html=True)

# Navigation deliberately follows the benchmark's research flow while retaining
# the requested dashboard as the first view.
dashboard, screener, industries, movers, stock, methodology = st.tabs(
    ["Dashboard", "Screener", "Industries", "Movers", "Stock", "Methodology"]
)

with dashboard:
    metric_grid([
        ("Universe", f"{len(result):,}", "official Nifty Total Market"),
        ("Valid RS", f"{int(valid_rs.sum()):,}", "eligible for cross-sectional rank"),
        ("Stage 2", f"{int((stage == 'Stage 2').sum()):,}", "advancing"),
        ("Breakout", f"{int(result['Breakout'].sum()):,}", "setup conditions met"),
        ("Confirmed", f"{int(result['Breakout_Confirmed'].sum()):,}", "breakout + U/D > 1.3"),
        ("Industries", f"{result['Industry'].nunique():,}", "exact NSE CSV field"),
        ("Liquid", f"{int(result['Liquid_UI_Filter'].fillna(False).sum()):,}", "optional ₹5Cr filter"),
        ("Decision date", latest.strftime("%d %b %Y") if pd.notna(latest) else "—", "latest completed session"),
    ])

    left, right = st.columns([1.0, 1.7], gap="large")
    with left:
        st.markdown('<div class="rs-section">Stage breadth</div>', unsafe_allow_html=True)
        counts = stage.value_counts().reindex(["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Unknown"], fill_value=0)
        stage_table = pd.DataFrame({"Stage": counts.index, "Stocks": counts.values})
        render_table(stage_table, 260)
        above = int(stage.isin(["Stage 2", "Stage 3"]).sum())
        st.markdown(f'<div class="rs-small">Above the 30W MA: {above:,} / {len(result):,} ({above / len(result) * 100:.1f}%).</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="rs-section">Leadership board</div>', unsafe_allow_html=True)
        leaders = result.loc[valid_rs].sort_values(["RS_Score", "RS_Blend"], ascending=False).head(15).copy()
        leaders_out = pd.DataFrame({
            "Symbol": leaders.index,
            "Company": leaders["Company Name"].fillna("—"),
            "Industry": leaders["Industry"],
            "RS": leaders["RS_Score"].round(0).astype(int),
            "Stage": leaders["Stage"].map(stage_short),
            "3M": leaders["R3M"].map(fmt_pct),
            "52W": leaders["Near_52W_High"].map(lambda x: "Yes" if bool(x) else "No"),
            "Action": leaders["Action"],
        })
        render_table(leaders_out, 390)

    st.markdown('<div class="rs-section">Research action board</div>', unsafe_allow_html=True)
    action_counts = result["Action"].value_counts().reindex(["BUY", "HOLD", "WAIT", "REDUCE", "SELL"], fill_value=0)
    metric_grid([(a, f"{int(action_counts[a]):,}", "transparent project overlay") for a in action_counts.index])

    st.markdown('<div class="rs-section">What deserves inspection now</div>', unsafe_allow_html=True)
    candidates = result[(result["Action"] == "BUY") & valid_rs].sort_values("RS_Score", ascending=False).head(8)
    if len(candidates):
        cols = st.columns(min(4, len(candidates)))
        for col, (symbol, row) in zip(cols, candidates.iterrows()):
            with col:
                st.markdown(f"**{html.escape(symbol)}**  ", unsafe_allow_html=True)
                st.caption(f"RS {float(row['RS_Score']):.0f} · {row['Industry']}")
    else:
        st.info("No names currently satisfy the BUY overlay.")

with screener:
    st.markdown('<div class="rs-section">Relative-strength screener</div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-small">Ranked across the full mathematical universe first. Industry, stage, action and liquidity are UI filters only; they do not recompute RS.</div>', unsafe_allow_html=True)
    f1, f2, f3, f4, f5 = st.columns([1.25, 1.0, 1.0, 1.0, 1.25])
    industry_options = ["All"] + sorted(result["Industry"].dropna().astype(str).unique())
    selected_industry = f1.selectbox("Industry", industry_options)
    selected_stage = f2.selectbox("Stage", ["All", "Stage 1", "Stage 2", "Stage 3", "Stage 4"])
    selected_action = f3.selectbox("Action", ["All", "BUY", "HOLD", "WAIT", "REDUCE", "SELL"])
    min_rs = f4.number_input("Minimum RS", min_value=1, max_value=99, value=1, step=1)
    liquid_only = f5.checkbox("Liquid only")
    search = st.text_input("Search symbol or company", placeholder="e.g. BEL, DIXON, TRENT")

    filtered = result.copy()
    if selected_industry != "All":
        filtered = filtered[filtered["Industry"].astype(str) == selected_industry]
    if selected_stage != "All":
        filtered = filtered[filtered["Stage"].map(stage_short) == selected_stage]
    if selected_action != "All":
        filtered = filtered[filtered["Action"] == selected_action]
    filtered = filtered[filtered["RS_Score"].fillna(0) >= min_rs]
    if liquid_only:
        filtered = filtered[filtered["Liquid_UI_Filter"].fillna(False)]
    if search.strip():
        q = search.strip().upper()
        mask = filtered.index.to_series().str.upper().str.contains(q, na=False) | filtered["Company Name"].astype(str).str.upper().str.contains(q, na=False)
        filtered = filtered[mask]
    filtered = filtered.sort_values(["RS_Score", "RS_Blend"], ascending=False)

    st.markdown(f'<div class="rs-small" style="margin:.65rem 0">{len(filtered):,} stocks shown · sorted by RS</div>', unsafe_allow_html=True)
    screen = pd.DataFrame({
        "Symbol": filtered.index,
        "Company": filtered["Company Name"].fillna("—"),
        "Industry": filtered["Industry"],
        "RS": filtered["RS_Score"].round(0),
        "Stage": filtered["Stage"].map(stage_short),
        "R3M": filtered["R3M"],
        "R6M": filtered["R6M"],
        "R9M": filtered["R9M"],
        "R12M": filtered["R12M"],
        "52W": filtered["Near_52W_High"].map(lambda x: "Yes" if bool(x) else "No"),
        "Vol ×": filtered["Volume_Ratio"],
        "U/D": filtered["U_D"],
        "Avg Value": filtered["AvgValue20"],
        "Action": filtered["Action"],
    })
    screen["R3M"] = screen["R3M"].map(lambda x: fmt_pct(x))
    screen["R6M"] = screen["R6M"].map(lambda x: fmt_pct(x))
    screen["R9M"] = screen["R9M"].map(lambda x: fmt_pct(x))
    screen["R12M"] = screen["R12M"].map(lambda x: fmt_pct(x))
    screen["Vol ×"] = screen["Vol ×"].map(lambda x: fmt_num(x, 2) + "×")
    screen["U/D"] = screen["U/D"].map(lambda x: "∞" if np.isinf(x) else fmt_num(x, 2))
    screen["Avg Value"] = screen["Avg Value"].map(fmt_inr)
    screen["RS"] = screen["RS"].map(lambda x: "—" if pd.isna(x) else f"{int(x)}")
    render_table(screen.head(250), 650)
    st.caption("Showing up to 250 rows in the interactive table. Filters operate on the complete snapshot.")

with industries:
    st.markdown('<div class="rs-section">Industry leadership</div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-small">Industries are the exact NSE CSV Industry field. No WealthStar-style sector remapping or consolidation is applied.</div>', unsafe_allow_html=True)
    ind = result.copy()
    ind["StageShort"] = ind["Stage"].map(stage_short)
    industry_board = ind.groupby("Industry", dropna=False).agg(
        Stocks=("RS_Score", "size"),
        Median_RS=("RS_Score", "median"),
        Stage_2=("StageShort", lambda s: int((s == "Stage 2").sum())),
        Breakouts=("Breakout_Confirmed", "sum"),
        R3M=("R3M", "median"),
    ).sort_values(["Median_RS", "Stage_2"], ascending=False)
    industry_board["Stage 2 %"] = industry_board["Stage_2"] / industry_board["Stocks"] * 100
    industry_board = industry_board.reset_index().rename(columns={"Industry": "Industry"})
    industry_view = pd.DataFrame({
        "Industry": industry_board["Industry"],
        "Stocks": industry_board["Stocks"].astype(int),
        "Median RS": industry_board["Median_RS"].round(0).astype(int),
        "Stage 2": industry_board["Stage_2"].astype(int),
        "Stage 2 %": industry_board["Stage 2 %"].map(lambda x: f"{x:.1f}%"),
        "Confirmed": industry_board["Breakouts"].astype(int),
        "Median 3M": industry_board["R3M"].map(fmt_pct),
    })
    render_table(industry_view, 650)

with movers:
    st.markdown('<div class="rs-section">Market movers & setups</div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-small">The validated snapshot contains period returns and structural flags, not an invented intraday feed. Movers below are therefore ranked by available quantitative evidence.</div>', unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown('<div class="rs-section">3M leaders</div>', unsafe_allow_html=True)
        top3 = result.dropna(subset=["R3M"]).sort_values("R3M", ascending=False).head(20)
        view = pd.DataFrame({"Symbol": top3.index, "RS": top3["RS_Score"].round(0).astype("Int64"), "3M": top3["R3M"].map(fmt_pct), "Stage": top3["Stage"].map(stage_short), "Action": top3["Action"]})
        render_table(view, 470)
    with b:
        st.markdown('<div class="rs-section">3M laggards</div>', unsafe_allow_html=True)
        low3 = result.dropna(subset=["R3M"]).sort_values("R3M", ascending=True).head(20)
        view = pd.DataFrame({"Symbol": low3.index, "RS": low3["RS_Score"].round(0).astype("Int64"), "3M": low3["R3M"].map(fmt_pct), "Stage": low3["Stage"].map(stage_short), "Action": low3["Action"]})
        render_table(view, 470)
    st.markdown('<div class="rs-section">Confirmed breakouts</div>', unsafe_allow_html=True)
    br = result[result["Breakout_Confirmed"].fillna(False)].sort_values(["RS_Score", "Volume_Ratio"], ascending=False).head(40)
    if br.empty:
        st.info("No confirmed breakouts in the validated snapshot.")
    else:
        view = pd.DataFrame({"Symbol": br.index, "Company": br["Company Name"], "RS": br["RS_Score"].round(0).astype(int), "Stage": br["Stage"].map(stage_short), "Vol ×": br["Volume_Ratio"].map(lambda x: fmt_num(x) + "×"), "U/D": br["U_D"].map(lambda x: "∞" if np.isinf(x) else fmt_num(x)), "Action": br["Action"]})
        render_table(view, 520)

with stock:
    st.markdown('<div class="rs-section">Stock research</div>', unsafe_allow_html=True)
    symbols = sorted(result.index.tolist())
    selected_symbol = st.selectbox("Search symbol", symbols, index=0 if symbols else None, key="stock_symbol")
    row = result.loc[selected_symbol]
    action = row["Action"]
    st.markdown(
        f'<div class="stock-head"><div><div class="stock-symbol">{html.escape(selected_symbol)}</div>'
        f'<div class="stock-company">{html.escape(str(row.get("Company Name", "—")))}</div>'
        f'<div class="stock-industry">{html.escape(str(row.get("Industry", "—")))}</div></div>'
        f'<div>{action_html(action)}<div class="rs-small" style="margin-top:5px;text-align:right">{html.escape(action_reason(row, action))}</div></div></div>',
        unsafe_allow_html=True,
    )
    metric_grid([
        ("RS", "—" if pd.isna(row["RS_Score"]) else f"{float(row['RS_Score']):.0f}", "cross-sectional 1–99 scale"),
        ("Stage", stage_short(row["Stage"]), "30-calendar-week MA + slope"),
        ("3M return", fmt_pct(row["R3M"]), "calendar-month return"),
        ("12M return", fmt_pct(row["R12M"]), "calendar-month return"),
        ("30W MA", fmt_inr(row["MA_30W"]), "adjusted Close basis"),
        ("MA slope", fmt_pct_plain(row["MA_30W_Slope_10S_Pct"]), "10-session slope"),
        ("Volume", "∞" if np.isinf(float(row["Volume_Ratio"])) else fmt_num(row["Volume_Ratio"]) + "×", "vs prior 50-session average"),
        ("U/D", "∞" if np.isinf(float(row["U_D"])) else fmt_num(row["U_D"]), "20-session up/down volume"),
    ])

    end_date = pd.Timestamp(row["Date"]).strftime("%Y-%m-%d")
    try:
        with st.spinner(f"Loading {selected_symbol} price history…"):
            history = load_stock_history(selected_symbol, end_date)
        st.markdown('<div class="rs-section">Price & 30W structure</div>', unsafe_allow_html=True)
        components.html(chart_html(history, selected_symbol), height=545, scrolling=False)
    except Exception as exc:
        st.warning(f"Chart data unavailable for {selected_symbol}: {exc}")

    checklist = pd.DataFrame({
        "Check": ["Stage", "52W proximity", "Volume confirmation", "U/D confirmation", "Liquidity", "Breakout", "Confirmed breakout"],
        "Value": [
            stage_short(row["Stage"]),
            "Yes" if bool(row["Near_52W_High"]) else "No",
            "Yes" if float(row["Volume_Ratio"]) > 1.5 else "No",
            "Yes" if float(row["U_D"]) > 1.3 else "No",
            "Yes" if bool(row["Liquid_UI_Filter"]) else "No",
            "Yes" if bool(row["Breakout"]) else "No",
            "Yes" if bool(row["Breakout_Confirmed"]) else "No",
        ],
    })
    st.markdown('<div class="rs-section">Research checklist</div>', unsafe_allow_html=True)
    render_table(checklist, 300)

    detail_cols = [
        ("R3M", fmt_pct(row["R3M"])), ("R6M", fmt_pct(row["R6M"])), ("R9M", fmt_pct(row["R9M"])), ("R12M", fmt_pct(row["R12M"])),
        ("30W MA", fmt_inr(row["MA_30W"])), ("30W MA slope (10S)", fmt_pct_plain(row["MA_30W_Slope_10S_Pct"])),
        ("52W High", fmt_inr(row["High_52W"])), ("Near 52W High", "True" if bool(row["Near_52W_High"]) else "False"),
        ("Avg Value 20", fmt_inr(row["AvgValue20"])), ("Breakout", "True" if bool(row["Breakout"]) else "False"),
        ("Breakout Confirmed", "True" if bool(row["Breakout_Confirmed"]) else "False"), ("U/D", "∞" if np.isinf(float(row["U_D"])) else fmt_num(row["U_D"])),
    ]
    st.markdown('<div class="rs-section">Calculation detail</div>', unsafe_allow_html=True)
    st.markdown('<div class="detail-grid">' + "".join(f'<div class="detail-item"><div class="detail-label">{html.escape(k)}</div><div class="detail-value">{html.escape(v)}</div></div>' for k, v in detail_cols) + '</div>', unsafe_allow_html=True)

with methodology:
    st.markdown('<div class="rs-section">Methodology & information boundary</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-panel"><div class="info-title">Locked quantitative engine</div><div class="info-text">The repository specification is authoritative. The application does not reinterpret or modernize the locked formulas. Decisions use only the latest completed NSE session before the upcoming decision session.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-section">Relative strength</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-panel"><div class="info-text"><b>Returns:</b> 3/6/9/12 calendar months using the last NSE session on or before each calendar reference date.<br><b>Blend:</b> 0.40×R3M + 0.20×R6M + 0.20×R9M + 0.20×R12M.<br><b>Score:</b> rank(Blend, pct=True, method="min") × 98 + 1, rounded to the intended 1–99 scale.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-section">Stages</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-panel"><div class="info-text"><b>30W MA:</b> simple average of all valid NSE sessions inside the preceding 30 calendar weeks.<br><b>Slope:</b> (MA(T) / MA(T−10 sessions) − 1) × 100.<br><b>Stage 1:</b> Close ≤ MA and slope &gt; 0. <b>Stage 2:</b> Close &gt; MA and slope &gt; 0. <b>Stage 3:</b> Close &gt; MA and slope ≤ 0. <b>Stage 4:</b> Close ≤ MA and slope ≤ 0.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-section">Breakouts & volume</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-panel"><div class="info-text"><b>52W high:</b> preceding 52 calendar weeks, requiring at least 200 valid sessions. <b>Breakout:</b> Stage 2 + within 3% of 52W high + Volume Ratio &gt; 1.5×. <b>Confirmed:</b> Breakout + U/D &gt; 1.3. Volume baseline is the prior 50 completed sessions; U/D uses the latest 20 completed sessions with no artificial denominator.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-section">Liquidity & action</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-panel"><div class="info-text"><b>Liquidity</b> is a UI-only filter: mean(Close × raw Volume) over the latest 20 completed sessions &gt; ₹5 crore. <b>Action</b> is a transparent project overlay: BUY = Stage 2 + RS ≥ 85 + confirmed breakout; HOLD = Stage 2 + RS ≥ 70 without BUY; REDUCE = Stage 3; SELL = Stage 4; WAIT = everything else. These thresholds are project decisions, not claims about an undisclosed book formula.</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-section">Data source</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-panel"><div class="info-text">Production universe: official Nifty Total Market constituent CSV. Industry: exact NSE CSV Industry field. Market history: yfinance with auto-adjusted price fields and raw volume. Missing history produces insufficiency rather than fabricated values.</div></div>', unsafe_allow_html=True)

st.markdown('<div class="footer-note">For quantitative research and decision support. Verify underlying data, methodology and the information boundary before taking any real-world investment action. TradingView Lightweight Charts is used only as the client-side charting library; it does not supply the market data.</div>', unsafe_allow_html=True)
