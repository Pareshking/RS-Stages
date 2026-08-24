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
.stApp{background:#f4f6f8;color:#182235}
.block-container{max-width:1480px;padding:0 24px 42px}
[data-testid="stSidebar"]{display:none}
[data-testid="stToolbar"]{visibility:hidden;height:0}
header[data-testid="stHeader"]{height:0;background:transparent}
[data-testid="stDecoration"]{display:none}

/* terminal chrome */
.rs-shell{margin:0 -24px;background:#fff;border-bottom:1px solid #dfe4e9}
.rs-top{height:58px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;gap:20px}
.rs-brand{display:flex;align-items:center;gap:10px;min-width:210px}
.rs-mark{width:30px;height:30px;border-radius:7px;background:#172235;color:#fff;display:grid;place-items:center;font-size:10px;font-weight:900;letter-spacing:.04em}
.rs-name{font-size:14px;font-weight:900;letter-spacing:-.025em;color:#172235}
.rs-sub{font-size:8px;color:#87919e;letter-spacing:.12em;font-weight:800;margin-top:1px}
.rs-session{display:flex;align-items:center;gap:14px;color:#687486;font-size:9px;white-space:nowrap}
.rs-live{display:inline-flex;align-items:center;gap:5px;color:#28714f;background:#eef8f2;border:1px solid #cde5d6;border-radius:999px;padding:5px 8px;font-weight:850}
.rs-dot{width:5px;height:5px;border-radius:50%;background:#3b966a}
.rs-nav{display:flex;align-items:center;gap:2px;padding:0 24px;height:38px;border-top:1px solid #eef1f3;overflow-x:auto}
.rs-nav span{font-size:10px;color:#758092;font-weight:800;padding:7px 11px;border-radius:6px;white-space:nowrap}
.rs-nav .active{background:#172235;color:#fff}

/* compact hierarchy */
.rs-kicker{margin-top:22px;color:#778394;font-size:8px;letter-spacing:.18em;text-transform:uppercase;font-weight:900}
.rs-title{margin:3px 0 3px;color:#111b2d;font-size:30px;line-height:1.05;font-weight:950;letter-spacing:-.055em}
.rs-copy{color:#6f7b8c;font-size:10.5px;line-height:1.5;max-width:920px}
.rs-meta{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}
.rs-pill{font-size:8px;color:#667385;border:1px solid #dce2e8;background:#fff;border-radius:999px;padding:5px 8px;font-weight:800}

/* market cards */
.rs-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin:14px 0 18px}
.rs-card{background:#fff;border:1px solid #dce2e7;border-radius:9px;padding:11px 12px;min-width:0}
.rs-card-label{font-size:7px;color:#87919e;text-transform:uppercase;letter-spacing:.14em;font-weight:900}
.rs-card-value{font-size:20px;color:#172235;font-weight:950;letter-spacing:-.05em;line-height:1.1;margin-top:4px}
.rs-card-note{font-size:7.5px;color:#a0a8b2;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rs-card.stage2{border-top:2px solid #4b9872}.rs-card.confirmed{border-top:2px solid #b28b43}.rs-card.lead{border-top:2px solid #6587a8}

.rs-section{font-size:14px;font-weight:950;letter-spacing:-.035em;color:#172235;margin:20px 0 5px}
.rs-note{font-size:9px;line-height:1.45;color:#7b8795;margin-bottom:8px}
.rs-panel{background:#fff;border:1px solid #dce2e7;border-radius:10px;padding:12px}
.rs-panel-title{font-size:9px;color:#667384;text-transform:uppercase;letter-spacing:.12em;font-weight:900;margin-bottom:9px}

/* subtle state language */
.state-s1{color:#8a6d1b;background:#fff9e8;border-color:#eadcae}
.state-s2{color:#28714f;background:#eff8f2;border-color:#cde5d6}
.state-s3{color:#965522;background:#fff4eb;border-color:#e8d2be}
.state-s4{color:#a04444;background:#fff1f1;border-color:#e7cccc}
.action{display:inline-flex;align-items:center;border:1px solid;border-radius:999px;padding:3px 7px;font-size:8px;font-weight:950;white-space:nowrap}
.action-buy{color:#176e49;background:#edf8f1;border-color:#c8e4d3}.action-hold{color:#3e668c;background:#f0f5fa;border-color:#d3dfeb}.action-wait{color:#796515;background:#fff8e7;border-color:#eadcae}.action-reduce{color:#97501f;background:#fff3e9;border-color:#ead1bc}.action-sell{color:#a23f3f;background:#fff0f0;border-color:#e8caca}

/* charts */
.rs-chart{background:#fff;border:1px solid #dce2e7;border-radius:10px;overflow:hidden}
.rs-chart-note{height:25px;display:flex;align-items:center;padding:0 9px;border-top:1px solid #edf0f2;color:#8993a0;font-size:7.5px}

/* streamlit controls */
.stTabs [data-baseweb="tab-list"]{gap:2px;background:#fff;border:1px solid #dce2e7;border-radius:9px;padding:3px;overflow-x:auto}
.stTabs [data-baseweb="tab"]{height:29px;padding:0 11px;border-radius:6px;color:#778394;font-size:9px;font-weight:850;white-space:nowrap}
.stTabs [aria-selected="true"]{background:#172235;color:#fff}
.stTabs [data-baseweb="tab-highlight"]{display:none}
div[data-baseweb="select"]>div{background:#fff;border-color:#dce2e7;border-radius:7px;min-height:34px}
[data-testid="stDataFrame"]{border:1px solid #dce2e7;border-radius:9px;overflow:hidden;background:#fff}
[data-testid="stMetric"]{background:#fff;border:1px solid #dce2e7;border-radius:9px;padding:8px 10px}
button[kind="primary"]{background:#172235;border-color:#172235;border-radius:7px}
.rs-foot{font-size:7.5px;line-height:1.55;color:#9aa3ae;border-top:1px solid #dfe4e9;margin-top:24px;padding-top:10px}

@media(max-width:900px){
 .block-container{padding:0 12px 30px}
 .rs-shell{margin:0 -12px}
 .rs-top{height:54px;padding:0 12px}
 .rs-brand{min-width:0}.rs-name{font-size:13px}.rs-sub{font-size:7px}
 .rs-session{gap:6px;font-size:8px}.rs-session .hide-mobile{display:none}
 .rs-nav{padding:0 12px;height:36px}
 .rs-nav span{font-size:9px;padding:7px 9px}
 .rs-title{font-size:28px}.rs-copy{font-size:10px}
 .rs-grid{grid-template-columns:repeat(2,1fr);gap:6px}.rs-card{padding:10px}.rs-card-value{font-size:18px}.rs-card-note{font-size:7px}
 .rs-section{font-size:13px}
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


def action_class(action):
    if action in ("BUY", "BUY★"):
        return "action-buy"
    if action == "HOLD":
        return "action-hold"
    if action in ("WAIT", "WATCH", "WATCH★"):
        return "action-wait"
    if action == "REDUCE":
        return "action-reduce"
    return "action-sell"


def action_badge(action):
    return f'<span class="action {action_class(action)}">{html.escape(str(action))}</span>'


def stage_badge(stage):
    key = {"Stage 1":"state-s1","Stage 2":"state-s2","Stage 3":"state-s3","Stage 4":"state-s4"}.get(stage, "")
    return f'<span class="action {key}">{html.escape(str(stage))}</span>'


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
    chunks = ['<div class="rs-grid">']
    for label, value, note, cls in items:
        chunks.append(
            f'<div class="rs-card {cls}"><div class="rs-card-label">{html.escape(label)}</div>'
            f'<div class="rs-card-value">{html.escape(value)}</div><div class="rs-card-note">{html.escape(note)}</div></div>'
        )
    chunks.append('</div>')
    st.markdown("".join(chunks), unsafe_allow_html=True)


def display_table(frame, columns, height=390):
    view = frame[[c for c in columns if c in frame.columns]].copy()
    if "RS_Score" in view:
        view["RS_Score"] = pd.to_numeric(view["RS_Score"], errors="coerce").round().astype("Int64")
    if "R3M" in view:
        view["R3M"] = view["R3M"].map(pct)
    if "R6M" in view:
        view["R6M"] = view["R6M"].map(pct)
    if "R9M" in view:
        view["R9M"] = view["R9M"].map(pct)
    if "R12M" in view:
        view["R12M"] = view["R12M"].map(pct)
    if "Volume_Ratio" in view:
        view["Volume_Ratio"] = view["Volume_Ratio"].map(multiple)
    if "U_D" in view:
        view["U_D"] = view["U_D"].map(multiple)
    if "MA_30W_Slope_10S_Pct" in view:
        view["MA_30W_Slope_10S_Pct"] = view["MA_30W_Slope_10S_Pct"].map(pct)
    st.dataframe(view, hide_index=True, use_container_width=True, height=height)


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
<div class="rs-chart"><div id="chart" style="height:410px"></div><div class="rs-chart-note">{safe} · daily OHLC · 30-calendar-week SMA · completed sessions only</div></div>
<script src="https://unpkg.com/lightweight-charts@5.2.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
const p={payload};
const root=document.getElementById('chart');
const chart=LightweightCharts.createChart(root,{{autoSize:true,layout:{{background:{{type:'solid',color:'#ffffff'}},textColor:'#6f7b8c',fontFamily:'system-ui,-apple-system,Segoe UI,sans-serif',fontSize:10}},grid:{{vertLines:{{color:'#f0f2f4'}},horzLines:{{color:'#f0f2f4'}}}},rightPriceScale:{{borderColor:'#e1e5e9'}},timeScale:{{borderColor:'#e1e5e9',rightOffset:4,barSpacing:7}},crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}}}});
const candles=chart.addSeries(LightweightCharts.CandlestickSeries,{{upColor:'#3e966d',downColor:'#cc6262',borderVisible:false,wickUpColor:'#3e966d',wickDownColor:'#cc6262'}});candles.setData(p.candles);
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
leadership = int((pd.to_numeric(data["RS_Score"], errors="coerce") >= 80).sum()) if "RS_Score" in data else 0

st.markdown(
    f'<div class="rs-shell"><div class="rs-top"><div class="rs-brand"><div class="rs-mark">RS</div><div><div class="rs-name">RS-Stages</div><div class="rs-sub">NIFTY TOTAL MARKET · QUANTITATIVE TERMINAL</div></div></div><div class="rs-session"><span class="hide-mobile">PRE-MARKET DATA BOUNDARY</span><span class="rs-live"><span class="rs-dot"></span>VALIDATED</span></div></div><div class="rs-nav"><span class="active">Terminal</span><span>Relative Strength</span><span>Stages</span><span>Breakouts</span><span>Industries</span><span>Methodology</span></div></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="rs-kicker">Nifty Total Market · decision support</div><div class="rs-title">Leadership. Stage. Evidence.</div><div class="rs-copy">A compact research terminal for cross-sectional Relative Strength, 30-week stage structure, breakout evidence and guide-based actions. Calculations remain visible and the Action layer is explicitly separated from the mathematics.</div>', unsafe_allow_html=True)
st.markdown(f'<div class="rs-meta"><span class="rs-pill">Decision date · {last.strftime("%d %b %Y") if pd.notna(last) else "—"}</span><span class="rs-pill">{valid:,} valid RS observations</span><span class="rs-pill">Universe · {len(universe):,}</span></div>', unsafe_allow_html=True)

cards([
    ("Universe", f"{len(universe):,}", "official Nifty Total Market", ""),
    ("Leadership", f"{leadership:,}", "RS score ≥ 80", "lead"),
    ("Stage 2", f"{stage2:,}", "advancing structure", "stage2"),
    ("Confirmed", f"{confirmed:,}", "breakout + U/D > 1.3", "confirmed"),
    ("Valid RS", f"{valid:,}", "eligible cross-sectional rank", ""),
])

tabs = st.tabs(["Overview", "Screener", "Industries", "Movers", "Stock", "Methodology"])

with tabs[0]:
    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        st.markdown('<div class="rs-section">Stage breadth</div><div class="rs-note">Current stage distribution from the validated snapshot.</div>', unsafe_allow_html=True)
        stage_counts = data["Stage_Label"].value_counts().reindex(["Stage 1", "Stage 2", "Stage 3", "Stage 4"]).fillna(0).astype(int)
        display_table(pd.DataFrame({"Stage": stage_counts.index, "Stocks": stage_counts.values}), ["Stage", "Stocks"], 190)
    with c2:
        st.markdown('<div class="rs-section">Action breadth</div><div class="rs-note">Guide-derived interpretation, not a replacement for the underlying calculations.</div>', unsafe_allow_html=True)
        order = ["BUY★", "BUY", "HOLD", "WAIT", "WATCH★", "WATCH", "REDUCE", "SELL", "AVOID"]
        action_counts = data["Action"].value_counts().reindex(order).fillna(0).astype(int)
        display_table(pd.DataFrame({"Action": action_counts.index, "Stocks": action_counts.values}), ["Action", "Stocks"], 190)
    st.markdown('<div class="rs-section">Top leadership</div><div class="rs-note">Highest RS scores, with confirmed setups first where available.</div>', unsafe_allow_html=True)
    top = data.sort_values(["Breakout_Confirmed", "RS_Score"], ascending=[False, False]).head(25)
    display_table(top, ["Symbol", "Company Name", "Industry", "RS_Score", "Stage_Label", "R3M", "R6M", "R9M", "R12M", "Volume_Ratio", "U_D", "Action"], 430)

with tabs[1]:
    st.markdown('<div class="rs-section">Relative-strength screener</div><div class="rs-note">Filters are presentation controls only. RS is calculated before these UI filters.</div>', unsafe_allow_html=True)
    a, b, c, dcol = st.columns(4)
    industries = ["All"] + sorted(data["Industry"].dropna().astype(str).unique().tolist()) if "Industry" in data else ["All"]
    ind = a.selectbox("Industry", industries)
    stage = b.selectbox("Stage", ["All", "Stage 1", "Stage 2", "Stage 3", "Stage 4"])
    action = c.selectbox("Action", ["All", "BUY★", "BUY", "HOLD", "WAIT", "WATCH★", "WATCH", "REDUCE", "SELL", "AVOID"])
    min_rs = dcol.number_input("Minimum RS", min_value=1, max_value=99, value=1, step=1)
    query = st.text_input("Search symbol or company", placeholder="e.g. BEL, DIXON, TRENT")
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
    st.caption(f"{len(view):,} stocks shown")
    display_table(view, ["Symbol", "Company Name", "Industry", "RS_Score", "R3M", "R6M", "R9M", "R12M", "Stage_Label", "Near_52W_High", "Volume_Ratio", "U_D", "Action"], 560)

with tabs[2]:
    st.markdown('<div class="rs-section">Industry leadership</div><div class="rs-note">Industry aggregates are descriptive; stock-level calculations remain the source of Action.</div>', unsafe_allow_html=True)
    industry = data.groupby("Industry", dropna=False).agg(Stocks=("Symbol", "count"), Median_RS=("RS_Score", "median"), Stage2=("Stage_Label", lambda s: int((s == "Stage 2").sum())), Confirmed=("Breakout_Confirmed", lambda s: int(s.fillna(False).astype(bool).sum()))).reset_index()
    industry["Median_RS"] = industry["Median_RS"].round().astype("Int64")
    industry = industry.sort_values(["Median_RS", "Stage2"], ascending=[False, False])
    display_table(industry, ["Industry", "Stocks", "Median_RS", "Stage2", "Confirmed"], 560)

with tabs[3]:
    st.markdown('<div class="rs-section">Movers & setups</div><div class="rs-note">Sorted by recent 3-month return, with breakout confirmation surfaced separately.</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="rs-section">Stock terminal</div><div class="rs-note">Select a snapshot symbol for price structure and the exact visible inputs behind its Action.</div>', unsafe_allow_html=True)
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
        st.markdown(action_badge(row.get("Action", "—")), unsafe_allow_html=True)
        st.write(row.get("Action_Reason", "—"))
        evidence = pd.DataFrame({"Metric": ["R3M", "R6M", "R9M", "R12M", "30W MA", "30W slope (10S)", "52W High", "Near 52W High", "Volume Ratio", "U/D", "Breakout", "Confirmed"], "Value": [pct(row.get("R3M")), pct(row.get("R6M")), pct(row.get("R9M")), pct(row.get("R12M")), fmt(row.get("MA_30W"), 2), pct(row.get("MA_30W_Slope_10S_Pct"), 2), fmt(row.get("High_52W"), 2), str(row.get("Near_52W_High", "—")), multiple(row.get("Volume_Ratio")), multiple(row.get("U_D")), str(row.get("Breakout", "—")), str(row.get("Breakout_Confirmed", "—"))]})
        st.dataframe(evidence, hide_index=True, use_container_width=True, height=390)

with tabs[5]:
    st.markdown('<div class="rs-section">Methodology & information boundary</div>', unsafe_allow_html=True)
    st.markdown('''
<div class="rs-panel">
<div class="rs-panel-title">Locked quantitative engine</div>
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
