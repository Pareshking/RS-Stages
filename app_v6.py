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
:root{color-scheme:light;--bg:#f5f6f8;--surface:#fff;--ink:#18212f;--muted:#7d8794;--line:#e2e6ea;--green:#15966a;--green-soft:#e8f6f0;--red:#c55252;--red-soft:#faecec;--amber:#b7862c;--amber-soft:#fbf3df;--blue:#4e78a1;--blue-soft:#edf3f8}
.stApp{background:var(--bg);color:var(--ink)}
.block-container{max-width:1440px;padding:0 24px 42px}
[data-testid="stSidebar"]{display:none}
[data-testid="stToolbar"],header[data-testid="stHeader"],[data-testid="stDecoration"]{display:none}
html,body,[class*="css"]{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;-webkit-font-smoothing:antialiased}

.rs-header{margin:0 -24px;background:var(--surface);border-bottom:1px solid var(--line)}
.rs-head{height:62px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;gap:20px}
.rs-brand{display:flex;align-items:center;gap:11px;min-width:0}
.rs-mark{width:34px;height:34px;border-radius:9px;background:#172033;color:#fff;display:grid;place-items:center;font-size:10px;font-weight:850;letter-spacing:.04em}
.rs-name{font-size:15px;font-weight:850;letter-spacing:-.035em;color:#172033;line-height:1.05}
.rs-sub{font-size:7.5px;color:#9099a4;letter-spacing:.14em;font-weight:800;margin-top:4px}
.rs-status{display:flex;align-items:center;gap:15px;color:#7f8995;font-size:9px;white-space:nowrap}
.status{display:inline-flex;align-items:center;gap:6px}.dot{width:7px;height:7px;border-radius:50%;display:inline-block}.dot.green{background:var(--green)}.dot.red{background:var(--red)}.dot.amber{background:var(--amber)}.dot.blue{background:var(--blue)}
.rs-live{color:#277654;font-weight:800}

.rs-kicker{margin-top:25px;color:#858e9a;font-size:8px;letter-spacing:.18em;text-transform:uppercase;font-weight:850}
.rs-title{margin:5px 0 6px;color:#121b2a;font-size:31px;line-height:1.05;font-weight:900;letter-spacing:-.055em}
.rs-copy{color:#6e7886;font-size:11px;line-height:1.55;max-width:920px}
.rs-meta{display:flex;gap:7px;flex-wrap:wrap;margin-top:11px}.pill{font-size:8px;color:#697482;border:1px solid #dfe4e8;background:#fff;border-radius:999px;padding:6px 9px;font-weight:750}

/* navigation is intentionally quiet: one navigation row, no repeated table chrome */
.stTabs{margin-top:18px}.stTabs [data-baseweb="tab-list"]{gap:2px;background:#fff;border:1px solid #dce1e6;border-radius:10px;padding:3px;overflow-x:auto}.stTabs [data-baseweb="tab"]{height:32px;padding:0 13px;border-radius:7px;color:#687483;font-size:10px;font-weight:800;white-space:nowrap}.stTabs [aria-selected="true"]{background:#172033;color:#fff}.stTabs [data-baseweb="tab-highlight"]{display:none}

.section{font-size:17px;font-weight:880;letter-spacing:-.04em;color:#172033;margin:22px 0 4px}.note{font-size:9px;line-height:1.55;color:#7b8693;margin-bottom:10px}
.panel{background:#fff;border:1px solid var(--line);border-radius:11px;padding:15px}.panel-title{font-size:8px;color:#89929e;text-transform:uppercase;letter-spacing:.15em;font-weight:850;margin-bottom:8px}

/* briefing: editorial blocks rather than a fixed table */
.brief-grid{display:grid;grid-template-columns:1.35fr 1fr;gap:10px;margin-top:16px}.brief-card{background:#fff;border:1px solid var(--line);border-radius:11px;padding:15px}.brief-card.wide{grid-column:1/-1}
.regime-line{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.regime-word{font-size:21px;font-weight:900;letter-spacing:-.045em}.regime-detail{font-size:10px;color:#697584}.regime-copy{font-size:9px;color:#7c8794;line-height:1.55;margin-top:8px}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid #e0e4e8;background:#fbfcfd;border-radius:7px;padding:7px 9px;font-size:9px;color:#273142;font-weight:780}.chip small{font-size:8px;color:#8a94a0;font-weight:650}.chip.green{background:var(--green-soft);border-color:#d8eee5;color:#237653}.chip.red{background:var(--red-soft);border-color:#f1d8d8;color:#a84848}.chip.amber{background:var(--amber-soft);border-color:#f1e4c7;color:#80651e}.chip.blue{background:var(--blue-soft);border-color:#dce7f0;color:#4a6f93}
.change-row{display:grid;grid-template-columns:165px 1fr;gap:10px;align-items:start;padding:9px 0;border-bottom:1px solid #edf0f2}.change-row:last-child{border-bottom:0;padding-bottom:0}.change-label{font-size:9px;font-weight:850;display:flex;align-items:center;gap:7px}.change-items{display:flex;flex-wrap:wrap;gap:5px}
.brief-stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}.stat{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 13px}.stat-label{font-size:7px;color:#8b95a0;text-transform:uppercase;letter-spacing:.14em;font-weight:850}.stat-value{font-size:20px;line-height:1.1;margin-top:5px;font-weight:900;letter-spacing:-.045em}.stat-note{font-size:7.5px;color:#9aa2ab;margin-top:4px}

/* filters and table */
div[data-baseweb="select"]>div{background:#fff;border-color:#dce2e7;border-radius:8px;min-height:36px} [data-testid="stTextInput"] input{background:#fff;border-color:#dce2e7;border-radius:8px}[data-testid="stNumberInput"] input{background:#fff;border-color:#dce2e7}
[data-testid="stDataFrame"]{border:1px solid #dce2e7;border-radius:10px;overflow:hidden;background:#fff}.dataframe{font-size:10px!important}
.table-note{display:flex;gap:13px;flex-wrap:wrap;font-size:8px;color:#8a94a0;margin:5px 0 8px}.table-note span{display:inline-flex;align-items:center;gap:5px}
button[kind="primary"]{background:#172033;border-color:#172033;border-radius:7px}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:9px;padding:9px 11px}

.rs-foot{font-size:7.5px;line-height:1.55;color:#9aa3ae;border-top:1px solid #dfe4e9;margin-top:25px;padding-top:11px}

@media(max-width:900px){
 .block-container{padding:0 12px 32px}.rs-header{margin:0 -12px}.rs-head{height:58px;padding:0 12px}.rs-mark{width:32px;height:32px}.rs-name{font-size:14px}.rs-sub{font-size:7px}.rs-status{gap:7px;font-size:8px}.hide-mobile{display:none!important}.rs-kicker{margin-top:20px}.rs-title{font-size:28px}.rs-copy{font-size:10.5px}.brief-grid{grid-template-columns:1fr}.brief-card.wide{grid-column:auto}.brief-stat-grid{grid-template-columns:repeat(2,1fr)}.change-row{grid-template-columns:1fr;gap:5px}.stTabs [data-baseweb="tab"]{padding:0 10px;font-size:9px}
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
        if pd.isna(v): return "—"
        x=float(v)
        return "∞" if np.isinf(x) else f"{x:.2f}×"
    except Exception:
        return "—"


def stage_label(v):
    return str(v).split(" — ", 1)[0] if pd.notna(v) else "Unknown"


def action_color(action):
    action=str(action)
    if action in {"BUY","BUY★"}: return "#15966a"
    if action=="HOLD": return "#4e78a1"
    if action in {"WAIT","WATCH","WATCH★"}: return "#9a7624"
    if action=="REDUCE": return "#a85c2c"
    return "#c55252"


@st.cache_data(ttl=1800, show_spinner=False)
def load_snapshot():
    research=pd.read_csv(RESEARCH); universe=pd.read_csv(UNIVERSE)
    for frame in (research, universe): frame["Symbol"]=frame["Symbol"].astype(str).str.strip()
    cols=["Symbol"]
    for col in ("Industry", "Company Name"):
        if col in universe.columns: cols.append(col)
    data=research.merge(universe[cols].drop_duplicates("Symbol"),on="Symbol",how="left",suffixes=("","_u"))
    if "Industry_u" in data.columns:
        data["Industry"]=data["Industry"].fillna(data["Industry_u"]); data.drop(columns=["Industry_u"],inplace=True)
    if "Company Name_u" in data.columns:
        data["Company Name"]=data["Company Name"].fillna(data["Company Name_u"]); data.drop(columns=["Company Name_u"],inplace=True)
    data["Stage_Label"]=data["Stage"].map(stage_label)
    data["Action"]=data.apply(action_for,axis=1)
    data["Action_Reason"]=data.apply(lambda row: action_reason(row,row["Action"]),axis=1)
    return data,universe


def clean_view(frame, columns):
    cols=[c for c in columns if c in frame.columns]
    view=frame[cols].copy()
    rename={"RS_Score":"RS","Stage_Label":"Stage","Near_52W_High":"52W","Volume_Ratio":"Vol","U_D":"U/D","Breakout_Confirmed":"Confirmed","Breakout":"Setup","MA_30W_Slope_10S_Pct":"30W slope"}
    view.rename(columns=rename,inplace=True)
    for col in ("R3M","R6M","R9M","R12M","30W slope"):
        if col in view: view[col]=view[col].map(pct)
    for col in ("Vol","U/D"):
        if col in view: view[col]=view[col].map(multiple)
    if "RS" in view: view["RS"]=pd.to_numeric(view["RS"],errors="coerce").round().astype("Int64")
    if "Stage" in view:
        view["Stage"]=view["Stage"].map(lambda x: f"● {x}" if str(x)=="Stage 2" else f"● {x}" if str(x) in {"Stage 3","Stage 4"} else str(x))
    for col in ("52W","Setup","Confirmed"):
        if col in view: view[col]=view[col].map(lambda x: "●" if bool(x) else "—")
    return view


def render_table(frame, columns, height=520):
    view=clean_view(frame,columns)
    styler=view.style
    if "RS" in view: styler=styler.background_gradient(subset=["RS"],cmap="Greens",vmin=0,vmax=100)
    if "R3M" in view: styler=styler.map(lambda v: f"color:{'#15966a' if str(v).startswith('+') else '#c55252' if str(v).startswith('-') else '#788390'};font-weight:650",subset=["R3M"])
    if "Stage" in view:
        styler=styler.map(lambda v: "color:#15966a;font-weight:750" if "Stage 2" in str(v) else "color:#c55252;font-weight:750" if "Stage 4" in str(v) else "color:#a87825;font-weight:700" if "Stage 3" in str(v) else "color:#6f7a88",subset=["Stage"])
    for col in ("52W","Setup","Confirmed"):
        if col in view: styler=styler.map(lambda v: "color:#15966a;font-weight:850" if v=="●" else "color:#b7bec6",subset=[col])
    if "Action" in view: styler=styler.map(lambda v:f"color:{action_color(v)};font-weight:800",subset=["Action"])
    st.dataframe(styler,hide_index=True,use_container_width=True,height=height)


def signal(label,tone):
    return f'<span class="status" style="color:{action_color(label)};font-weight:800"><span class="dot {tone}"></span>{html.escape(label)}</span>'


def chart(hist,symbol):
    h=hist.sort_index().tail(420).copy()
    if h.empty or "Close" not in h.columns:
        st.error("No usable completed-session history was returned for this symbol."); return
    ma=ma_30w_series(h["Close"]); candles=[]; ma_points=[]
    for idx,row in h.iterrows():
        if all(pd.notna(row.get(k)) for k in ("Open","High","Low","Close")):
            candles.append({"time":idx.strftime("%Y-%m-%d"),"open":float(row.Open),"high":float(row.High),"low":float(row.Low),"close":float(row.Close)})
        if idx in ma.index and pd.notna(ma.loc[idx]): ma_points.append({"time":idx.strftime("%Y-%m-%d"),"value":float(ma.loc[idx])})
    payload=json.dumps({"candles":candles,"ma":ma_points}); safe=html.escape(symbol)
    components.html(f'''<div style="background:#fff;border:1px solid #e0e4e8;border-radius:10px;overflow:hidden"><div id="chart" style="height:390px"></div><div style="height:27px;display:flex;align-items:center;padding:0 10px;border-top:1px solid #edf0f2;color:#8993a0;font-size:8px">{safe} · daily OHLC · 30-calendar-week SMA · completed sessions only</div></div><script src="https://unpkg.com/lightweight-charts@5.2.0/dist/lightweight-charts.standalone.production.js"></script><script>const p={payload};const root=document.getElementById('chart');const chart=LightweightCharts.createChart(root,{{autoSize:true,layout:{{background:{{type:'solid',color:'#ffffff'}},textColor:'#707b89',fontFamily:'system-ui,-apple-system,Segoe UI,sans-serif',fontSize:10}},grid:{{vertLines:{{color:'#f1f3f5'}},horzLines:{{color:'#f1f3f5'}}}},rightPriceScale:{{borderColor:'#e1e5e9'}},timeScale:{{borderColor:'#e1e5e9',rightOffset:4,barSpacing:7}},crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}}}});const candles=chart.addSeries(LightweightCharts.CandlestickSeries,{{upColor:'#15966a',downColor:'#c55252',borderVisible:false,wickUpColor:'#15966a',wickDownColor:'#c55252'}});candles.setData(p.candles);const ma=chart.addSeries(LightweightCharts.LineSeries,{{color:'#5d7f9f',lineWidth:2,lastValueVisible:true,priceLineVisible:false,crosshairMarkerVisible:false}});ma.setData(p.ma);chart.timeScale().fitContent();</script>''',height=417,scrolling=False)


data,universe=load_snapshot()
last=pd.to_datetime(data["Date"],errors="coerce").max(); valid=int(data["RS_Score"].notna().sum()) if "RS_Score" in data else 0
stage2=int((data["Stage_Label"]=="Stage 2").sum()); confirmed=int(data["Breakout_Confirmed"].fillna(False).astype(bool).sum()) if "Breakout_Confirmed" in data else 0
stage4=int((data["Stage_Label"]=="Stage 4").sum()); near_high=int(data["Near_52W_High"].fillna(False).astype(bool).sum()) if "Near_52W_High" in data else 0

st.markdown(f'<div class="rs-header"><div class="rs-head"><div class="rs-brand"><div class="rs-mark">RS</div><div><div class="rs-name">RS-Stages</div><div class="rs-sub">NIFTY TOTAL MARKET · QUANTITATIVE PLATFORM</div></div></div><div class="rs-status"><span class="hide-mobile">{last.strftime("%d %b %Y") if pd.notna(last) else "—"}</span><span class="rs-live status"><span class="dot green"></span>VALIDATED SNAPSHOT</span></div></div></div>',unsafe_allow_html=True)
st.markdown('<div class="rs-kicker">Nifty Total Market · decision support</div><div class="rs-title">Leadership, stage and action.</div><div class="rs-copy">A transparent quantitative terminal for Relative Strength, 30-week stage structure, breakout evidence and industry context. The mathematics remains separate from the interpretation layer.</div>',unsafe_allow_html=True)
st.markdown(f'<div class="rs-meta"><span class="pill">Decision date · {last.strftime("%d %b %Y") if pd.notna(last) else "—"}</span><span class="pill">{valid:,} valid RS observations</span><span class="pill">Universe · {len(universe):,}</span></div>',unsafe_allow_html=True)

tabs=st.tabs(["Briefing","Screener","Industries","Movers","Stock","Methodology"])

with tabs[0]:
    regime_text="Broad participation" if stage2/len(data)>.45 else "Selective participation"
    regime_pct=stage2/len(data)*100 if len(data) else 0
    leaders=data.groupby("Industry",dropna=True)["RS_Score"].median().dropna().sort_values(ascending=False).head(6)
    top_break=data[data["Breakout_Confirmed"].fillna(False)].sort_values("RS_Score",ascending=False).head(8)
    stage_up=data[data["Stage_Label"]=="Stage 2"].sort_values("RS_Score",ascending=False).head(6)
    weak=data[data["Stage_Label"].isin(["Stage 3","Stage 4"])].sort_values("RS_Score",ascending=True).head(6)
    st.markdown('<div class="section">Today’s briefing</div><div class="note">A top-down read of the validated snapshot — regime, leadership, setups and weaker structure. This page is for orientation; the Screener is for selection.</div>',unsafe_allow_html=True)
    st.markdown(f'''<div class="brief-grid"><div class="brief-card"><div class="panel-title">Market regime</div><div class="regime-line"><span class="regime-word" style="color:#15966a">{html.escape(regime_text)}</span><span class="regime-detail">{regime_pct:.0f}% of the universe in Stage 2 · {stage4:,} in Stage 4</span></div><div class="regime-copy">Participation is measured from the same completed-session snapshot used by the quantitative engine. It is a description of breadth, not a trading call.</div></div><div class="brief-card"><div class="panel-title">Snapshot</div><div class="brief-stat-grid" style="margin-top:0"><div class="stat"><div class="stat-label">Valid RS</div><div class="stat-value">{valid:,}</div></div><div class="stat"><div class="stat-label">Stage 2</div><div class="stat-value">{stage2:,}</div></div><div class="stat"><div class="stat-label">Confirmed</div><div class="stat-value">{confirmed:,}</div></div><div class="stat"><div class="stat-label">Near 52W</div><div class="stat-value">{near_high:,}</div></div></div></div></div>''',unsafe_allow_html=True)
    leader_html=''.join(f'<span class="chip">{html.escape(str(name))}<small>RS {int(round(score))}</small></span>' for name,score in leaders.items())
    breakout_html=''.join(f'<span class="chip blue">{html.escape(str(r.Symbol))}<small>RS {int(round(r.RS_Score))}</small></span>' for _,r in top_break.iterrows()) or '<span class="note">No confirmed breakouts in the current snapshot.</span>'
    stage_html=''.join(f'<span class="chip green">{html.escape(str(r.Symbol))}<small>RS {int(round(r.RS_Score))}</small></span>' for _,r in stage_up.iterrows())
    weak_html=''.join(f'<span class="chip red">{html.escape(str(r.Symbol))}<small>RS {int(round(r.RS_Score))}</small></span>' for _,r in weak.iterrows())
    st.markdown(f'<div class="brief-grid"><div class="brief-card"><div class="panel-title">Leading industries</div><div class="chips">{leader_html}</div></div><div class="brief-card"><div class="panel-title">Confirmed setups</div><div class="chips">{breakout_html}</div></div><div class="brief-card wide"><div class="panel-title">What changed in the structure</div><div class="change-row"><div class="change-label"><span class="dot green"></span>Stage 2 leadership</div><div class="change-items">{stage_html}</div></div><div class="change-row"><div class="change-label"><span class="dot blue"></span>Confirmed breakout</div><div class="change-items">{breakout_html}</div></div><div class="change-row"><div class="change-label"><span class="dot red"></span>Weaker structure</div><div class="change-items">{weak_html}</div></div></div></div>',unsafe_allow_html=True)

with tabs[1]:
    st.markdown('<div class="section">Relative-strength screener</div><div class="note">Filters change presentation only. The underlying RS calculation, stage logic and information boundary are unchanged.</div>',unsafe_allow_html=True)
    a,b,c,d=st.columns(4)
    industries=["All"]+sorted(data["Industry"].dropna().astype(str).unique().tolist()) if "Industry" in data else ["All"]
    ind=a.selectbox("Industry",industries); stage=b.selectbox("Stage",["All","Stage 1","Stage 2","Stage 3","Stage 4"]); action=c.selectbox("Action",["All","BUY★","BUY","HOLD","WAIT","WATCH★","WATCH","REDUCE","SELL","AVOID"]); min_rs=d.number_input("Minimum RS",min_value=1,max_value=99,value=1,step=1)
    query=st.text_input("Search",placeholder="Symbol or industry")
    view=data.copy()
    if ind!="All": view=view[view["Industry"].astype(str)==ind]
    if stage!="All": view=view[view["Stage_Label"]==stage]
    if action!="All": view=view[view["Action"]==action]
    view=view[pd.to_numeric(view["RS_Score"],errors="coerce")>=min_rs]
    if query.strip():
        q=query.strip().upper(); view=view[view["Symbol"].str.upper().str.contains(q,na=False)|view["Industry"].astype(str).str.upper().str.contains(q,na=False)]
    view=view.sort_values(["RS_Score","Breakout_Confirmed"],ascending=[False,False])
    st.caption(f"{len(view):,} stocks · sorted by RS")
    st.markdown('<div class="table-note"><span><span class="dot green"></span> positive / confirmed</span><span><span class="dot red"></span> weaker stage</span><span>RS shading = relative rank</span></div>',unsafe_allow_html=True)
    render_table(view,["Symbol","Industry","RS_Score","R3M","R6M","R9M","R12M","Stage_Label","Near_52W_High","Breakout","U_D","Breakout_Confirmed","Action"],560)

with tabs[2]:
    st.markdown('<div class="section">Industry leadership</div><div class="note">Industry aggregates are descriptive. Stock-level calculations remain the source of the Action label.</div>',unsafe_allow_html=True)
    industry=data.groupby("Industry",dropna=False).agg(Stocks=("Symbol","count"),Median_RS=("RS_Score","median"),Stage2=("Stage_Label",lambda s:int((s=="Stage 2").sum())),Confirmed=("Breakout_Confirmed",lambda s:int(s.fillna(False).astype(bool).sum()))).reset_index().sort_values(["Median_RS","Stage2"],ascending=[False,False])
    render_table(industry,["Industry","Stocks","Median_RS","Stage2","Confirmed"],560)

with tabs[3]:
    st.markdown('<div class="section">Movers & setups</div><div class="note">Recent 3-month movement with stage, RS and action alongside it. No repeated master screener table.</div>',unsafe_allow_html=True)
    up=data.sort_values("R3M",ascending=False).head(15); down=data.sort_values("R3M",ascending=True).head(15)
    c1,c2=st.columns(2,gap="medium")
    with c1:
        st.markdown('<div class="panel-title">Strongest 3M</div>',unsafe_allow_html=True); render_table(up,["Symbol","Industry","R3M","RS_Score","Stage_Label","Action"],420)
    with c2:
        st.markdown('<div class="panel-title">Weakest 3M</div>',unsafe_allow_html=True); render_table(down,["Symbol","Industry","R3M","RS_Score","Stage_Label","Action"],420)

with tabs[4]:
    st.markdown('<div class="section">Stock terminal</div><div class="note">Select a symbol to inspect price structure and the visible inputs behind its interpretation.</div>',unsafe_allow_html=True)
    symbols=data.sort_values("RS_Score",ascending=False)["Symbol"].dropna().astype(str).tolist(); symbol=st.selectbox("Symbol",symbols,index=0 if symbols else None); row=data.loc[data["Symbol"]==symbol].iloc[0]
    c1,c2,c3,c4=st.columns(4); c1.metric("RS",fmt(row.get("RS_Score"),0)); c2.metric("Stage",row.get("Stage_Label","—")); c3.metric("U/D",multiple(row.get("U_D"))); c4.metric("Action",row.get("Action","—"))
    left,right=st.columns([1.7,1],gap="medium")
    with left:
        try:
            end=pd.Timestamp(last)+pd.Timedelta(days=1); start=pd.Timestamp(last)-pd.Timedelta(days=760); history=download_yfinance_history(symbol,start=start,end=end); chart(history,symbol)
        except Exception as exc: st.warning(f"Price chart unavailable: {type(exc).__name__}")
    with right:
        st.markdown('<div class="panel-title">Action evidence</div>',unsafe_allow_html=True); act=str(row.get("Action","—")); tone="green" if act in {"BUY","BUY★","HOLD"} else "red" if act in {"SELL","REDUCE"} else "amber"; st.markdown(signal(act,tone),unsafe_allow_html=True); st.write(row.get("Action_Reason","—"))
        evidence=pd.DataFrame({"Metric":["R3M","R6M","R9M","R12M","30W MA","30W slope (10S)","52W High","Near 52W High","Volume Ratio","U/D","Breakout","Confirmed"],"Value":[pct(row.get("R3M")),pct(row.get("R6M")),pct(row.get("R9M")),pct(row.get("R12M")),fmt(row.get("MA_30W"),2),pct(row.get("MA_30W_Slope_10S_Pct"),2),fmt(row.get("High_52W"),2),str(row.get("Near_52W_High","—")),multiple(row.get("Volume_Ratio")),multiple(row.get("U_D")),str(row.get("Breakout","—")),str(row.get("Breakout_Confirmed","—"))]})
        st.dataframe(evidence,hide_index=True,use_container_width=True,height=390)

with tabs[5]:
    st.markdown('<div class="section">Methodology & information boundary</div><div class="note">The UI is presentation only. These definitions describe the calculations already present in the research snapshot.</div>',unsafe_allow_html=True)
    st.markdown('''<div class="panel"><div class="panel-title">Quantitative engine</div><div class="note">3/6/9/12-calendar-month returns feed the RS blend; cross-sectional RS is ranked from that blend. Stage uses the 30-calendar-week SMA and 10-session percentage slope. Breakout requires Stage 2, within 3% of the 52-week adjusted High and Volume Ratio &gt; 1.5. Confirmation adds U/D &gt; 1.3.</div><div class="panel-title">Guide-based action layer</div><div class="note">BUY★, BUY, HOLD, WAIT, WATCH★, WATCH, REDUCE, SELL and AVOID are interpretation labels. They do not silently modify the underlying quantitative calculations.</div><div class="panel-title">Information boundary</div><div class="note">Only completed NSE sessions available before the decision session are used. Missing history produces insufficiency rather than fabricated values.</div></div>''',unsafe_allow_html=True)
    st.markdown('<div class="section">Current snapshot</div>',unsafe_allow_html=True)
    st.json({"decision_date":last.strftime("%Y-%m-%d") if pd.notna(last) else None,"universe":int(len(universe)),"valid_rs":valid,"stage_2":stage2,"confirmed_breakouts":confirmed})

st.markdown('<div class="rs-foot">Research and decision-support software. Verify the underlying data, methodology and current market conditions before taking any real-world investment action.</div>',unsafe_allow_html=True)
