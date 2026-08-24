from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from rs_stages.actions import action_for, action_reason
from rs_stages.data import download_yfinance_history
from rs_stages.quant import ma_30w_series

st.set_page_config(
    page_title="RS-Stages | Quantitative Terminal",
    page_icon="RS",
    layout="wide",
    initial_sidebar_state="collapsed",
)

RESEARCH = Path("data/latest_research.csv")
UNIVERSE = Path("data/ind_niftytotalmarket_list.csv")

st.markdown(
    """
<style>
:root{color-scheme:light}
.stApp{background:#f6f7f9;color:#172033}
.block-container{max-width:1500px;padding:0 22px 44px}
[data-testid="stSidebar"]{display:none}
[data-testid="stToolbar"]{visibility:hidden;height:0}
header[data-testid="stHeader"]{height:0;background:transparent}
[data-testid="stDecoration"]{display:none}

/* compact terminal header */
.rs-header{margin:0 -22px;background:#fff;border-bottom:1px solid #e4e8ed}
.rs-head{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 22px;gap:18px}
.rs-brand{display:flex;align-items:center;gap:11px;min-width:0}
.rs-mark{width:34px;height:34px;border-radius:9px;background:#172033;color:#fff;display:grid;place-items:center;font-size:11px;font-weight:900;letter-spacing:.03em;flex:0 0 auto}
.rs-name{font-size:15px;font-weight:900;letter-spacing:-.03em;color:#172033;line-height:1.05}
.rs-sub{font-size:8px;color:#8a94a1;letter-spacing:.13em;font-weight:800;margin-top:4px}
.rs-status{display:flex;align-items:center;gap:12px;color:#7b8593;font-size:9px;white-space:nowrap}
.rs-status-item{display:inline-flex;align-items:center;gap:6px}
.rs-status-dot{width:7px;height:7px;border-radius:50%;display:inline-block}
.rs-status-dot.green{background:#299a67}.rs-status-dot.amber{background:#c28a32}.rs-status-dot.red{background:#c55353}
.rs-status-live{color:#26744f;font-weight:850}

/* typography */
.rs-kicker{margin-top:24px;color:#818b98;font-size:8px;letter-spacing:.19em;text-transform:uppercase;font-weight:900}
.rs-title{margin:5px 0 5px;color:#111a2c;font-size:31px;line-height:1.04;font-weight:950;letter-spacing:-.055em}
.rs-copy{color:#6d7888;font-size:11px;line-height:1.55;max-width:960px}
.rs-meta{display:flex;gap:7px;flex-wrap:wrap;margin-top:11px}
.rs-pill{font-size:8px;color:#687485;border:1px solid #dfe4e9;background:#fff;border-radius:999px;padding:6px 9px;font-weight:800}

/* dashboard-only summary */
.rs-summary{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:16px 0 21px}
.rs-card{background:#fff;border:1px solid #dde3e8;border-radius:10px;padding:12px 13px;min-width:0;position:relative;overflow:hidden}
.rs-card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#dfe4e9}
.rs-card.green::before{background:#3b9b6b}.rs-card.blue::before{background:#6489ad}.rs-card.amber::before{background:#c39342}.rs-card.red::before{background:#c45a5a}
.rs-card-label{font-size:7px;color:#8993a0;text-transform:uppercase;letter-spacing:.15em;font-weight:900}
.rs-card-value{font-size:21px;color:#172033;font-weight:950;letter-spacing:-.055em;line-height:1.1;margin-top:5px}
.rs-card-note{font-size:7.5px;color:#9ba3ad;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* sections / panels */
.rs-section{font-size:15px;font-weight:950;letter-spacing:-.04em;color:#172033;margin:21px 0 5px}
.rs-note{font-size:9px;line-height:1.5;color:#7c8795;margin-bottom:9px}
.rs-panel{background:#fff;border:1px solid #dde3e8;border-radius:10px;padding:13px}
.rs-panel-title{font-size:9px;color:#667384;text-transform:uppercase;letter-spacing:.13em;font-weight:900;margin-bottom:9px}
.rs-signal{display:inline-flex;align-items:center;gap:6px;font-size:9px;font-weight:900}
.rs-signal-dot{width:7px;height:7px;border-radius:50%;display:inline-block}
.rs-signal-green{color:#24734d}.rs-signal-green .rs-signal-dot{background:#299a67}
.rs-signal-red{color:#a44242}.rs-signal-red .rs-signal-dot{background:#c55353}
.rs-signal-amber{color:#80671f}.rs-signal-amber .rs-signal-dot{background:#c28a32}
.rs-signal-blue{color:#496d91}.rs-signal-blue .rs-signal-dot{background:#668bb0}

/* Streamlit controls */
.stTabs [data-baseweb="tab-list"]{gap:2px;background:#fff;border:1px solid #dce2e8;border-radius:9px;padding:3px;overflow-x:auto}
.stTabs [data-baseweb="tab"]{height:31px;padding:0 12px;border-radius:6px;color:#687485;font-size:10px;font-weight:850;white-space:nowrap}
.stTabs [aria-selected="true"]{background:#172033;color:#fff}
.stTabs [data-baseweb="tab-highlight"]{display:none}
div[data-baseweb="select"]>div{background:#fff;border-color:#dce2e8;border-radius:8px;min-height:36px}
[data-testid="stTextInput"] input{background:#fff;border-color:#dce2e8;border-radius:8px}
[data-testid="stNumberInput"] input{background:#fff}
[data-testid="stDataFrame"]{border:1px solid #dce2e8;border-radius:10px;overflow:hidden;background:#fff}
[data-testid="stMetric"]{background:#fff;border:1px solid #dce2e8;border-radius:9px;padding:9px 11px}
button[kind="primary"]{background:#172033;border-color:#172033;border-radius:7px}

/* table language */
.rs-table-note{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:8px;color:#8a94a1;margin:6px 0 8px}
.rs-foot{font-size:7.5px;line-height:1.55;color:#9aa3ae;border-top:1px solid #dfe4e9;margin-top:25px;padding-top:11px}

@media(max-width:900px){
 .block-container{padding:0 12px 32px}
 .rs-header{margin:0 -12px}
 .rs-head{height:58px;padding:0 12px}
 .rs-mark{width:32px;height:32px}
 .rs-name{font-size:14px}.rs-sub{font-size:7px}
 .rs-status{gap:7px;font-size:8px}.rs-status .hide-mobile{display:none}
 .rs-kicker{margin-top:20px}.rs-title{font-size:29px}.rs-copy{font-size:10.5px}
 .rs-summary{grid-template-columns:repeat(2,1fr);gap:7px}.rs-card{padding:11px}.rs-card-value{font-size:19px}
 .rs-section{font-size:14px}
 .stTabs [data-baseweb="tab"]{padding:0 10px;font-size:9px}
}
</style>
""",
    unsafe_allow_html=True,
)


def fmt(v, digits=1):
    try:
        return "—" if pd.isna(v) else f"{float(v):,.{digits}f}"
    except Exception:
        return "—"


def pct(v, digits=1):
    try:
        return "—" if pd.isna(v) else f"{float(v):+.{digits}f}%"
    except Exception:
        return "—"


def multiple(v):
    try:
        if pd.isna(v):
            return "—"
        x = float(v)
        return "∞" if np.isinf(x) else f"{x:.2f}×"
    except Exception:
        return "—"


def stage_label(v):
    return str(v).split(" — ", 1)[0] if pd.notna(v) else "Unknown"


def action_color(action):
    action = str(action)
    if action in {"BUY", "BUY★"}:
        return "#23764e"
    if action == "HOLD":
        return "#4b6f93"
    if action in {"WAIT", "WATCH", "WATCH★"}:
        return "#80691f"
    if action == "REDUCE":
        return "#9a5525"
    return "#a44343"


@st.cache_data(ttl=1800, show_spinner=False)
def load_snapshot():
    research = pd.read_csv(RESEARCH)
    universe = pd.read_csv(UNIVERSE)
    for frame in (research, universe):
        frame["Symbol"] = frame["Symbol"].astype(str).str.strip()
    cols = ["Symbol"]
    for col in ("Industry", "Company Name"):
        if col in universe.columns:
            cols.append(col)
    data = research.merge(universe[cols].drop_duplicates("Symbol"), on="Symbol", how="left", suffixes=("", "_u"))
    if "Industry_u" in data.columns:
        data["Industry"] = data["Industry"].fillna(data["Industry_u"])
        data.drop(columns=["Industry_u"], inplace=True)
    if "Company Name_u" in data.columns:
        data["Company Name"] = data["Company Name"].fillna(data["Company Name_u"])
        data.drop(columns=["Company Name_u"], inplace=True)
    data["Stage_Label"] = data["Stage"].map(stage_label)
    data["Action"] = data.apply(action_for, axis=1)
    data["Action_Reason"] = data.apply(lambda row: action_reason(row, row["Action"]), axis=1)
    return data, universe


def cards(items):
    out = ['<div class="rs-summary">']
    for label, value, note, tone in items:
        out.append(
            f'<div class="rs-card {tone}"><div class="rs-card-label">{html.escape(label)}</div>'
            f'<div class="rs-card-value">{html.escape(value)}</div><div class="rs-card-note">{html.escape(note)}</div></div>'
        )
    out.append('</div>')
    st.markdown("".join(out), unsafe_allow_html=True)


def display_table(frame, columns, height=390):
    cols = [c for c in columns if c in frame.columns]
    view = frame[cols].copy()
    rename = {
        "Company Name":"Company", "RS_Score":"RS", "Stage_Label":"Stage",
        "Near_52W_High":"52W", "Volume_Ratio":"Vol", "U_D":"U/D",
        "Breakout_Confirmed":"Confirmed", "Breakout":"Breakout",
        "MA_30W_Slope_10S_Pct":"30W slope", "Median_RS":"Median RS",
    }
    view.rename(columns=rename, inplace=True)
    for col in ("R3M", "R6M", "R9M", "R12M", "30W slope"):
        if col in view:
            view[col] = view[col].map(pct)
    for col in ("Vol", "U/D"):
        if col in view:
            view[col] = view[col].map(multiple)
    if "RS" in view:
        view["RS"] = pd.to_numeric(view["RS"], errors="coerce").round().astype("Int64")
    if "Median RS" in view:
        view["Median RS"] = pd.to_numeric(view["Median RS"], errors="coerce").round().astype("Int64")
    for col in ("52W", "Breakout", "Confirmed"):
        if col in view:
            view[col] = view[col].map(lambda x: "●" if bool(x) else "—")
    if "Stage" in view:
        view["Stage"] = view["Stage"].map(lambda x: f"● {x}" if str(x) == "Stage 2" else str(x))
    styler = view.style
    if "RS" in view:
        styler = styler.background_gradient(subset=["RS"], cmap="Blues", vmin=0, vmax=100)
    if "R3M" in view:
        styler = styler.map(lambda v: f"color: {'#23764e' if str(v).startswith('+') else '#a44343' if str(v).startswith('-') else '#6f7b88'}; font-weight:600", subset=["R3M"])
    for col in ("52W", "Breakout", "Confirmed"):
        if col in view:
            styler = styler.map(lambda v: "color:#299a67;font-weight:800" if v == "●" else "color:#aab1ba", subset=[col])
    if "Stage" in view:
        styler = styler.map(lambda v: "color:#23764e;font-weight:800" if "Stage 2" in str(v) else "color:#687485", subset=["Stage"])
    if "Action" in view:
        styler = styler.map(lambda v: f"color:{action_color(v)};font-weight:800", subset=["Action"])
    st.dataframe(styler, hide_index=True, use_container_width=True, height=height)


def signal(label, tone):
    return f'<span class="rs-signal rs-signal-{tone}"><span class="rs-signal-dot"></span>{html.escape(label)}</span>'


def chart(hist, symbol):
    h = hist.sort_index().tail(420).copy()
    if h.empty or "Close" not in h.columns:
        st.error("No usable completed-session history was returned for this symbol.")
        return
    ma = ma_30w_series(h["Close"])
    candles, ma_points = [], []
    for idx, row in h.iterrows():
        if all(pd.notna(row.get(k)) for k in ("Open", "High", "Low", "Close")):
            candles.append({"time": idx.strftime("%Y-%m-%d"), "open": float(row.Open), "high": float(row.High), "low": float(row.Low), "close": float(row.Close)})
        if idx in ma.index and pd.notna(ma.loc[idx]):
            ma_points.append({"time": idx.strftime("%Y-%m-%d"), "value": float(ma.loc[idx])})
    payload = json.dumps({"candles": candles, "ma": ma_points})
    safe = html.escape(symbol)
    components.html(
        f"""
<div style="background:#fff;border:1px solid #dde3e8;border-radius:10px;overflow:hidden"><div id="chart" style="height:410px"></div><div style="height:26px;display:flex;align-items:center;padding:0 10px;border-top:1px solid #edf0f2;color:#8993a0;font-size:8px">{safe} · daily OHLC · 30-calendar-week SMA · completed sessions only</div></div>
<script src="https://unpkg.com/lightweight-charts@5.2.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
const p={payload};
const root=document.getElementById('chart');
const chart=LightweightCharts.createChart(root,{{autoSize:true,layout:{{background:{{type:'solid',color:'#ffffff'}},textColor:'#6f7b8c',fontFamily:'system-ui,-apple-system,Segoe UI,sans-serif',fontSize:10}},grid:{{vertLines:{{color:'#f0f2f4'}},horzLines:{{color:'#f0f2f4'}}}},rightPriceScale:{{borderColor:'#e1e5e9'}},timeScale:{{borderColor:'#e1e5e9',rightOffset:4,barSpacing:7}},crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}}}});
const candles=chart.addSeries(LightweightCharts.CandlestickSeries,{{upColor:'#299a67',downColor:'#c55353',borderVisible:false,wickUpColor:'#299a67',wickDownColor:'#c55353'}});candles.setData(p.candles);
const ma=chart.addSeries(LightweightCharts.LineSeries,{{color:'#5f7f9e',lineWidth:2,lastValueVisible:true,priceLineVisible:false,crosshairMarkerVisible:false}});ma.setData(p.ma);
chart.timeScale().fitContent();
</script>
""",
        height=438,
        scrolling=False,
    )


data, universe = load_snapshot()
last = pd.to_datetime(data["Date"], errors="coerce").max()
valid = int(data["RS_Score"].notna().sum()) if "RS_Score" in data else 0
stage2 = int((data["Stage_Label"] == "Stage 2").sum())
confirmed = int(data["Breakout_Confirmed"].fillna(False).astype(bool).sum()) if "Breakout_Confirmed" in data else 0

st.markdown(
    f'<div class="rs-header"><div class="rs-head"><div class="rs-brand"><div class="rs-mark">RS</div><div><div class="rs-name">RS-Stages</div><div class="rs-sub">NIFTY TOTAL MARKET · QUANTITATIVE PLATFORM</div></div></div><div class="rs-status"><span class="rs-status-item hide-mobile">{last.strftime("%d %b %Y") if pd.notna(last) else "—"}</span><span class="rs-status-item rs-status-live"><span class="rs-status-dot green"></span>VALIDATED SNAPSHOT</span></div></div></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="rs-kicker">Nifty Total Market · decision support</div>'
    '<div class="rs-title">Leadership, stage and action.</div>'
    '<div class="rs-copy">A transparent quantitative terminal for Relative Strength, 30-week stage structure, breakout evidence, industry context and guide-based actions. The mathematics remains separate from the interpretation layer.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="rs-meta"><span class="rs-pill">Decision date · {last.strftime("%d %b %Y") if pd.notna(last) else "—"}</span><span class="rs-pill">{valid:,} valid RS observations</span><span class="rs-pill">Universe · {len(universe):,}</span></div>',
    unsafe_allow_html=True,
)

tabs = st.tabs(["Dashboard", "Screener", "Industries", "Movers", "Stock", "Methodology"])

with tabs[0]:
    cards([
        ("Universe", f"{len(universe):,}", "official Nifty Total Market", ""),
        ("Valid RS", f"{valid:,}", "eligible cross-sectional rank", "blue"),
        ("Stage 2", f"{stage2:,}", "advancing structure", "green"),
        ("Confirmed", f"{confirmed:,}", "breakout + U/D > 1.3", "amber"),
        ("Snapshot", last.strftime("%d %b %Y") if pd.notna(last) else "—", "latest completed NSE session", ""),
    ])
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown('<div class="rs-section">Stage breadth</div><div class="rs-note">Current stage distribution from the validated snapshot.</div>', unsafe_allow_html=True)
        stage_counts = data["Stage_Label"].value_counts().reindex(["Stage 1", "Stage 2", "Stage 3", "Stage 4"]).fillna(0).astype(int)
        display_table(pd.DataFrame({"Stage": stage_counts.index, "Stocks": stage_counts.values}), ["Stage", "Stocks"], 190)
    with c2:
        st.markdown('<div class="rs-section">Action breadth</div><div class="rs-note">Guide-derived interpretation, not a replacement for the underlying calculations.</div>', unsafe_allow_html=True)
        order = ["BUY★", "BUY", "HOLD", "WAIT", "WATCH★", "WATCH", "REDUCE", "SELL", "AVOID"]
        action_counts = data["Action"].value_counts().reindex(order).fillna(0).astype(int)
        display_table(pd.DataFrame({"Action": action_counts.index, "Stocks": action_counts.values}), ["Action", "Stocks"], 260)
    st.markdown('<div class="rs-section">Top leadership</div><div class="rs-note">Highest RS scores, with confirmed setups surfaced separately.</div>', unsafe_allow_html=True)
    top = data.sort_values(["Breakout_Confirmed", "RS_Score"], ascending=[False, False]).head(25)
    display_table(top, ["Symbol", "Company Name", "Industry", "RS_Score", "Stage_Label", "R3M", "R6M", "R9M", "R12M", "Volume_Ratio", "U_D", "Breakout_Confirmed", "Action"], 430)

with tabs[1]:
    st.markdown('<div class="rs-section">Relative-strength screener</div><div class="rs-note">TradingView-style workflow: filters first, compact data table second. Filters change presentation only; the underlying RS calculation and information boundary are unchanged.</div>', unsafe_allow_html=True)
    a, b, c, dcol = st.columns(4)
    industries = ["All"] + sorted(data["Industry"].dropna().astype(str).unique().tolist()) if "Industry" in data else ["All"]
    ind = a.selectbox("Industry", industries)
    stage = b.selectbox("Stage", ["All", "Stage 1", "Stage 2", "Stage 3", "Stage 4"])
    action = c.selectbox("Action", ["All", "BUY★", "BUY", "HOLD", "WAIT", "WATCH★", "WATCH", "REDUCE", "SELL", "AVOID"])
    min_rs = dcol.number_input("Minimum RS", min_value=1, max_value=99, value=1, step=1)
    query = st.text_input("Search", placeholder="Symbol or company")
    view = data.copy()
    if ind != "All":
        view = view[view["Industry"].astype(str) == ind]
    if stage != "All":
        view = view[view["Stage_Label"] == stage]
    if action != "All":
        view = view[view["Action"] == action]
    view = view[pd.to_numeric(view["RS_Score"], errors="coerce") >= min_rs]
    if query.strip():
        q = query.strip().upper()
        view = view[view["Symbol"].str.upper().str.contains(q, na=False) | view["Company Name"].astype(str).str.upper().str.contains(q, na=False)]
    view = view.sort_values(["RS_Score", "Breakout_Confirmed"], ascending=[False, False])
    st.caption(f"{len(view):,} stocks · sorted by RS")
    st.markdown('<div class="rs-table-note"><span>● green = confirmed/positive</span><span>— muted = not confirmed</span><span>RS shading = relative rank</span></div>', unsafe_allow_html=True)
    display_table(view, ["Symbol", "Company Name", "Industry", "RS_Score", "R3M", "R6M", "R9M", "R12M", "Stage_Label", "Near_52W_High", "Volume_Ratio", "U_D", "Breakout_Confirmed", "Action"], 560)

with tabs[2]:
    st.markdown('<div class="rs-section">Industry leadership</div><div class="rs-note">Industry aggregates are descriptive; stock-level calculations remain the source of Action.</div>', unsafe_allow_html=True)
    industry = data.groupby("Industry", dropna=False).agg(Stocks=("Symbol", "count"), Median_RS=("RS_Score", "median"), Stage2=("Stage_Label", lambda s: int((s == "Stage 2").sum())), Confirmed=("Breakout_Confirmed", lambda s: int(s.fillna(False).astype(bool).sum()))).reset_index()
    industry["Median_RS"] = industry["Median_RS"].round().astype("Int64")
    industry = industry.sort_values(["Median_RS", "Stage2"], ascending=[False, False])
    display_table(industry, ["Industry", "Stocks", "Median_RS", "Stage2", "Confirmed"], 560)

with tabs[3]:
    st.markdown('<div class="rs-section">Movers & setups</div><div class="rs-note">Recent 3-month movement, with stage and action shown alongside the return.</div>', unsafe_allow_html=True)
    up = data.sort_values("R3M", ascending=False).head(25)
    down = data.sort_values("R3M", ascending=True).head(25)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown('<div class="rs-panel-title">Strongest 3M</div>', unsafe_allow_html=True)
        display_table(up, ["Symbol", "Company Name", "R3M", "RS_Score", "Stage_Label", "Action"], 520)
    with c2:
        st.markdown('<div class="rs-panel-title">Weakest 3M</div>', unsafe_allow_html=True)
        display_table(down, ["Symbol", "Company Name", "R3M", "RS_Score", "Stage_Label", "Action"], 520)

with tabs[4]:
    st.markdown('<div class="rs-section">Stock terminal</div><div class="rs-note">Select a snapshot symbol for price structure and the visible inputs behind its Action.</div>', unsafe_allow_html=True)
    symbols = data.sort_values("RS_Score", ascending=False)["Symbol"].dropna().astype(str).tolist()
    symbol = st.selectbox("Symbol", symbols, index=0 if symbols else None)
    row = data.loc[data["Symbol"] == symbol].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RS", fmt(row.get("RS_Score"), 0))
    c2.metric("Stage", row.get("Stage_Label", "—"))
    c3.metric("U/D", multiple(row.get("U_D")))
    c4.metric("Action", row.get("Action", "—"))
    left, right = st.columns([1.7, 1], gap="medium")
    with left:
        try:
            end = pd.Timestamp(last) + pd.Timedelta(days=1)
            start = pd.Timestamp(last) - pd.Timedelta(days=760)
            history = download_yfinance_history(symbol, start=start, end=end)
            chart(history, symbol)
        except Exception as exc:
            st.warning(f"Price chart unavailable: {type(exc).__name__}")
    with right:
        st.markdown('<div class="rs-panel-title">Action evidence</div>', unsafe_allow_html=True)
        act = str(row.get("Action", "—"))
        tone = "green" if act in {"BUY", "BUY★", "HOLD"} else "red" if act in {"SELL", "REDUCE"} else "amber"
        st.markdown(signal(act, tone), unsafe_allow_html=True)
        st.write(row.get("Action_Reason", "—"))
        evidence = pd.DataFrame({"Metric": ["R3M", "R6M", "R9M", "R12M", "30W MA", "30W slope (10S)", "52W High", "Near 52W High", "Volume Ratio", "U/D", "Breakout", "Confirmed"], "Value": [pct(row.get("R3M")), pct(row.get("R6M")), pct(row.get("R9M")), pct(row.get("R12M")), fmt(row.get("MA_30W"), 2), pct(row.get("MA_30W_Slope_10S_Pct"), 2), fmt(row.get("High_52W"), 2), str(row.get("Near_52W_High", "—")), multiple(row.get("Volume_Ratio")), multiple(row.get("U_D")), str(row.get("Breakout", "—")), str(row.get("Breakout_Confirmed", "—"))]})
        st.dataframe(evidence, hide_index=True, use_container_width=True, height=390)

with tabs[5]:
    st.markdown('<div class="rs-section">Methodology & information boundary</div>', unsafe_allow_html=True)
    st.markdown('''
<div class="rs-panel">
<div class="rs-panel-title">Quantitative engine</div>
<div class="rs-note">3/6/9/12-calendar-month returns feed the RS blend; cross-sectional RS is ranked from that blend. Stage uses the 30-calendar-week SMA and 10-session percentage slope. Breakout requires Stage 2, within 3% of the 52-week adjusted High and Volume Ratio &gt; 1.5. Confirmation adds U/D &gt; 1.3.</div>
<div class="rs-panel-title">Guide-based action layer</div>
<div class="rs-note">BUY★, BUY, HOLD, WAIT, WATCH★, WATCH, REDUCE, SELL and AVOID are project-level interpretation labels. They do not silently modify the underlying quantitative calculations.</div>
<div class="rs-panel-title">Information boundary</div>
<div class="rs-note">Only completed NSE sessions available before the decision session are used. Missing history produces insufficiency rather than fabricated values.</div>
</div>
''', unsafe_allow_html=True)
    st.markdown('<div class="rs-section">Current snapshot</div>', unsafe_allow_html=True)
    st.json({"decision_date": last.strftime("%Y-%m-%d") if pd.notna(last) else None, "universe": int(len(universe)), "valid_rs": valid, "stage_2": stage2, "confirmed_breakouts": confirmed})

st.markdown('<div class="rs-foot">Research and decision-support software. Verify the underlying data, methodology and current market conditions before taking any real-world investment action.</div>', unsafe_allow_html=True)
