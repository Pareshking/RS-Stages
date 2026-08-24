from __future__ import annotations

import html
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from rs_stages.actions import action_for, action_reason
from rs_stages.data import download_yfinance_history
from rs_stages.quant import ma_30w_series

st.set_page_config(page_title="RS-Stages | Quantitative Platform", page_icon="RS", layout="wide", initial_sidebar_state="collapsed")

RESEARCH = Path("data/latest_research.csv")
UNIVERSE = Path("data/ind_niftytotalmarket_list.csv")

# ---- visual system ---------------------------------------------------------
st.markdown("""
<style>
:root { color-scheme: light; }
.stApp { background:#f7f8fa; color:#18202d; }
.block-container { max-width:1500px; padding:0 34px 48px; }
[data-testid="stSidebar"] { display:none; }
[data-testid="stToolbar"] { visibility:hidden; height:0; }
header[data-testid="stHeader"] { background:transparent; }
.rs-top { position:relative; margin:0 -34px; padding:18px 34px 12px; background:#fff; border-bottom:1px solid #e7e9ed; }
.rs-topline { display:flex; align-items:center; justify-content:space-between; gap:24px; }
.rs-brand { display:flex; align-items:center; gap:11px; }
.rs-logo { width:34px; height:34px; border-radius:8px; background:#172131; color:#fff; display:grid; place-items:center; font-size:11px; font-weight:900; letter-spacing:.04em; }
.rs-brand-title { font-size:16px; font-weight:850; letter-spacing:-.025em; }
.rs-brand-sub { margin-top:2px; color:#8992a1; font-size:9px; letter-spacing:.13em; font-weight:750; }
.rs-status { border:1px solid #d8eadf; background:#f3faf6; color:#28734e; border-radius:999px; padding:6px 10px; font-size:10px; font-weight:800; }
.rs-kicker { margin-top:26px; color:#778191; font-size:10px; letter-spacing:.16em; text-transform:uppercase; font-weight:850; }
.rs-h1 { margin:4px 0 7px; font-size:42px; line-height:1.02; letter-spacing:-.055em; font-weight:900; color:#121a27; }
.rs-lead { max-width:930px; color:#667181; font-size:13px; line-height:1.65; }
.rs-strip { display:grid; grid-template-columns:repeat(5,1fr); gap:8px; margin:20px 0 22px; }
.rs-metric { background:#fff; border:1px solid #e1e5ea; border-radius:11px; padding:13px 14px; }
.rs-metric-label { color:#87909e; font-size:9px; text-transform:uppercase; letter-spacing:.12em; font-weight:800; }
.rs-metric-value { color:#182131; font-size:22px; line-height:1.1; margin-top:5px; font-weight:900; letter-spacing:-.045em; }
.rs-metric-note { color:#9aa2ae; font-size:9px; margin-top:4px; }
.rs-section { margin:24px 0 8px; font-size:17px; font-weight:900; letter-spacing:-.035em; color:#182131; }
.rs-note { color:#7b8492; font-size:11px; line-height:1.55; margin-bottom:10px; }
.rs-panel { background:#fff; border:1px solid #e1e5ea; border-radius:13px; padding:16px; }
.rs-panel-title { font-size:12px; font-weight:850; color:#202a39; margin-bottom:10px; }
.rs-action { display:inline-flex; align-items:center; border-radius:999px; padding:5px 9px; font-size:10px; font-weight:900; border:1px solid; }
.buy { color:#18714b; background:#eff9f3; border-color:#cce7d7; }
.hold { color:#3e668c; background:#f1f6fb; border-color:#d5e2ef; }
.wait { color:#786315; background:#fff9e8; border-color:#eee0ad; }
.reduce { color:#96501e; background:#fff5ec; border-color:#eed8c4; }
.sell { color:#a33d3d; background:#fff2f2; border-color:#edcece; }
.stage2 { color:#18714b; }
.stage1 { color:#8a6a12; }
.stage3 { color:#a85b2a; }
.stage4 { color:#a33d3d; }
.stTabs [data-baseweb="tab-list"] { gap:0; background:#fff; border:1px solid #e1e5ea; border-radius:10px; padding:4px; }
.stTabs [data-baseweb="tab"] { height:32px; padding:0 15px; border-radius:7px; color:#7b8492; font-size:11px; font-weight:800; }
.stTabs [aria-selected="true"] { color:#172131; background:#f0f2f5; }
.stTabs [data-baseweb="tab-highlight"] { display:none; }
div[data-baseweb="select"] > div { background:#fff; border-color:#dfe3e8; border-radius:8px; }
[data-testid="stDataFrame"] { border:1px solid #e1e5ea; border-radius:10px; overflow:hidden; }
button[kind="secondary"] { border-radius:8px; }
.rs-foot { color:#9aa2ae; font-size:9px; line-height:1.6; margin-top:30px; border-top:1px solid #e6e8ec; padding-top:12px; }
@media(max-width:900px){ .block-container{padding:0 12px 36px}.rs-top{margin:0 -12px;padding:14px 12px 10px}.rs-h1{font-size:32px}.rs-strip{grid-template-columns:repeat(2,1fr)} }
</style>
""", unsafe_allow_html=True)


def fmt(v, d=1):
    try: return "—" if pd.isna(v) else f"{float(v):,.{d}f}"
    except Exception: return "—"


def pct(v, d=1):
    try: return "—" if pd.isna(v) else f"{float(v):+.{d}f}%"
    except Exception: return "—"


def multiple(v):
    try:
        if pd.isna(v): return "—"
        x=float(v)
        return "∞" if np.isinf(x) else f"{x:.2f}×"
    except Exception: return "—"


def rupees(v):
    try:
        x=float(v)
        if pd.isna(x): return "—"
        return f"₹{x/1e7:,.1f} Cr" if abs(x)>=1e7 else f"₹{x/1e5:,.1f} L"
    except Exception: return "—"


def stage_label(v):
    return str(v).split(" — ", 1)[0] if pd.notna(v) else "Unknown"


def action_class(a):
    if a in ("BUY", "BUY★"): return "buy"
    if a == "HOLD": return "hold"
    if a in ("WAIT", "WATCH", "WATCH★"): return "wait"
    if a == "REDUCE": return "reduce"
    return "sell"


def action_badge(a):
    return f'<span class="rs-action {action_class(a)}">{html.escape(str(a))}</span>'


@st.cache_data(ttl=1800, show_spinner=False)
def load_snapshot():
    r=pd.read_csv(RESEARCH)
    u=pd.read_csv(UNIVERSE)
    for x in (r,u): x["Symbol"]=x["Symbol"].astype(str).str.strip()
    company=next((c for c in ("Company Name","Company","Name") if c in u.columns), None)
    cols=["Symbol"] + (["Industry"] if "Industry" in u.columns else []) + ([company] if company else [])
    d=r.merge(u[cols].drop_duplicates("Symbol"), on="Symbol", how="left", suffixes=("","_u"))
    if "Industry_u" in d:
        d["Industry"]=d["Industry"].fillna(d["Industry_u"]); d.drop(columns=["Industry_u"], inplace=True)
    if company: d["Company"]=d[company]
    d["Stage_Label"]=d["Stage"].map(stage_label)
    d["Action"]=d.apply(action_for, axis=1)
    d["Action_Reason"]=d.apply(lambda x: action_reason(x, x.Action), axis=1)
    return d,u


def metric_strip(items):
    s='<div class="rs-strip">'
    for label,value,note in items:
        s+=f'<div class="rs-metric"><div class="rs-metric-label">{html.escape(label)}</div><div class="rs-metric-value">{html.escape(value)}</div><div class="rs-metric-note">{html.escape(note)}</div></div>'
    st.markdown(s+'</div>', unsafe_allow_html=True)


def table(df, cols, height=390):
    v=df[[c for c in cols if c in df]].copy()
    if "RS_Score" in v: v["RS_Score"]=pd.to_numeric(v["RS_Score"],errors="coerce").round().astype("Int64")
    if "Volume_Ratio" in v: v["Volume_Ratio"]=v["Volume_Ratio"].map(multiple)
    if "U_D" in v: v["U_D"]=v["U_D"].map(multiple)
    if "MA_30W_Slope_10S_Pct" in v: v["MA_30W_Slope_10S_Pct"]=v["MA_30W_Slope_10S_Pct"].map(pct)
    st.dataframe(v, hide_index=True, use_container_width=True, height=height)


d,u=load_snapshot()
last=pd.to_datetime(d.get("Date"),errors="coerce").max()
valid=int(d.RS_Score.notna().sum()) if "RS_Score" in d else 0
stage2=int((d.Stage_Label=="Stage 2").sum())
confirmed=int(d.Breakout_Confirmed.fillna(False).astype(bool).sum()) if "Breakout_Confirmed" in d else 0
leadership=int((pd.to_numeric(d.RS_Score,errors="coerce")>=80).sum()) if "RS_Score" in d else 0

st.markdown(f'''<div class="rs-top"><div class="rs-topline"><div class="rs-brand"><div class="rs-logo">RS</div><div><div class="rs-brand-title">RS-Stages</div><div class="rs-brand-sub">NIFTY TOTAL MARKET · QUANTITATIVE PLATFORM</div></div></div><div class="rs-status">● VALIDATED SNAPSHOT</div></div></div>''', unsafe_allow_html=True)
st.markdown('<div class="rs-kicker">Nifty Total Market · pre-market decision support</div><div class="rs-h1">Leadership, stage and action — in one view.</div><div class="rs-lead">A research terminal built around independently validated Relative Strength, 30-week stage analysis, breakout evidence, Industry context and a transparent nine-label Action layer. No uploads. No manual dates. The production snapshot is loaded automatically.</div>', unsafe_allow_html=True)

metric_strip([
    ("Universe", f"{len(u):,}", "Nifty Total Market"),
    ("Leadership", f"{leadership:,}", "RS ≥ 80"),
    ("Stage 2", f"{stage2:,}", "advancing structure"),
    ("Confirmed", f"{confirmed:,}", "breakout + U/D > 1.3"),
    ("As of", last.strftime("%d %b %Y") if pd.notna(last) else "—", "latest completed session"),
])

tabs=st.tabs(["Dashboard","Screener","Industries","Movers","Stock","Methodology"])

with tabs[0]:
    left,right=st.columns([1,1], gap="large")
    with left:
        st.markdown('<div class="rs-section">Market structure</div><div class="rs-note">Distribution of the four Weinstein stages across the validated snapshot.</div>',unsafe_allow_html=True)
        x=d.Stage_Label.value_counts().reindex(["Stage 1","Stage 2","Stage 3","Stage 4"]).fillna(0).astype(int)
        st.dataframe(pd.DataFrame({"Stage":x.index,"Stocks":x.values}),hide_index=True,use_container_width=True,height=205)
    with right:
        st.markdown('<div class="rs-section">Action distribution</div><div class="rs-note">Decision layer derived from the locked v2 Action specification.</div>',unsafe_allow_html=True)
        order=["BUY★","BUY","HOLD","WAIT","WATCH★","WATCH","REDUCE","SELL","AVOID"]
        x=d.Action.value_counts().reindex(order).fillna(0).astype(int)
        st.dataframe(pd.DataFrame({"Action":x.index,"Stocks":x.values}),hide_index=True,use_container_width=True,height=205)
    st.markdown('<div class="rs-section">Strongest setups</div><div class="rs-note">Evidence first; Action remains the final decision column.</div>',unsafe_allow_html=True)
    v=d[d.Action.isin(["BUY★","BUY","HOLD"])].sort_values(["RS_Score","Breakout_Confirmed"],ascending=[False,False]).head(20)
    table(v,["Symbol","Company","Industry","RS_Score","Stage_Label","Volume_Ratio","U_D","Breakout_Confirmed","Action"],390)

with tabs[1]:
    st.markdown('<div class="rs-section">Full-universe screener</div><div class="rs-note">Filters change presentation only; they never change the RS ranking universe.</div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    inds=["All"]+sorted(d.Industry.dropna().astype(str).unique()) if "Industry" in d else ["All"]
    ind=c1.selectbox("Industry",inds)
    stg=c2.selectbox("Stage",["All","Stage 1","Stage 2","Stage 3","Stage 4"])
    act=c3.selectbox("Action",["All","BUY★","BUY","HOLD","WAIT","WATCH★","WATCH","REDUCE","SELL","AVOID"])
    minrs=c4.number_input("Minimum RS",1,99,1)
    q=st.text_input("Search",placeholder="Symbol or company")
    v=d.copy()
    if ind!="All": v=v[v.Industry.astype(str)==ind]
    if stg!="All": v=v[v.Stage_Label==stg]
    if act!="All": v=v[v.Action==act]
    v=v[pd.to_numeric(v.RS_Score,errors="coerce").fillna(0)>=minrs]
    if q:
        z=q.strip().upper(); name=v.get("Company",pd.Series(index=v.index,dtype=str)).astype(str).str.upper()
        v=v[v.Symbol.str.upper().str.contains(z,na=False)|name.str.contains(z,na=False)]
    cols=["Symbol","Company","Industry","RS_Score","R3M","R6M","R9M","R12M","Stage_Label","MA_30W","MA_30W_Slope_10S_Pct","Near_52W_High","Volume_Ratio","U_D","Breakout","Breakout_Confirmed","Extended_20Pct","Below_50DMA","Action"]
    table(v.sort_values("RS_Score",ascending=False),cols,520)

with tabs[2]:
    st.markdown('<div class="rs-section">Industry leadership</div><div class="rs-note">Industry context comes from the official Nifty Total Market constituent classification.</div>',unsafe_allow_html=True)
    g=d.groupby("Industry",dropna=False)
    indf=g.agg(Stocks=("Symbol","count"),Median_RS=("RS_Score","median"),Leadership=("RS_Score",lambda x:int((pd.to_numeric(x,errors="coerce")>=80).sum())),Stage2=("Stage_Label",lambda x:int((x=="Stage 2").sum())),Buy=("Action",lambda x:int(x.isin(["BUY★","BUY"]).sum())),Sell=("Action",lambda x:int((x=="SELL").sum()))).reset_index().rename(columns={"Industry":"Industry"}).sort_values(["Median_RS","Leadership"],ascending=False)
    indf["Median_RS"]=indf.Median_RS.round(1)
    st.dataframe(indf,hide_index=True,use_container_width=True,height=560)

with tabs[3]:
    st.markdown('<div class="rs-section">Movers & setups</div><div class="rs-note">Only fields actually present in the validated snapshot are shown; no fabricated daily-change series.</div>',unsafe_allow_html=True)
    top=d.sort_values("RS_Score",ascending=False).head(25)
    table(top,["Symbol","Company","Industry","RS_Score","Stage_Label","R3M","R6M","Volume_Ratio","U_D","Breakout","Breakout_Confirmed","Action"],540)

with tabs[4]:
    st.markdown('<div class="rs-section">Stock research</div><div class="rs-note">Select a stock from the validated snapshot. Individual history is fetched only when requested and cached for speed.</div>',unsafe_allow_html=True)
    choices=d.sort_values("RS_Score",ascending=False).Symbol.tolist()
    sym=st.selectbox("Stock",choices,format_func=lambda s: f"{s} · {d.loc[d.Symbol.eq(s),'Company'].iloc[0] if 'Company' in d and not d.loc[d.Symbol.eq(s),'Company'].empty else ''}")
    row=d.loc[d.Symbol.eq(sym)].iloc[0]
    a=str(row.Action); c=action_class(a)
    st.markdown(f'<div class="rs-panel"><div style="display:flex;justify-content:space-between;gap:18px;align-items:flex-start"><div><div style="font-size:26px;font-weight:900;letter-spacing:-.045em">{html.escape(str(row.get("Company",sym)))}</div><div style="color:#8992a1;font-size:11px;margin-top:3px">{html.escape(sym)} · {html.escape(str(row.get("Industry","—")))}</div></div><span class="rs-action {c}" style="font-size:13px;padding:7px 12px">{html.escape(a)}</span></div><div style="color:#657080;font-size:12px;line-height:1.55;margin-top:13px">{html.escape(str(row.Action_Reason))}</div></div>',unsafe_allow_html=True)
    metric_strip([("RS Score",fmt(row.RS_Score,0),"cross-sectional 1–99"),("Stage",str(row.Stage_Label),"30W MA + slope"),("30W MA",fmt(row.MA_30W,2),"calendar-week SMA"),("Slope",pct(row.MA_30W_Slope_10S_Pct),"10-session slope"),("U/D",multiple(row.U_D),"20 completed sessions")])
    evcols=["Near_52W_High","Volume_Ratio","Breakout","Breakout_Confirmed","Extended_20Pct","Below_50DMA"]
    st.markdown('<div class="rs-section">Evidence</div>',unsafe_allow_html=True)
    table(pd.DataFrame([row]),["Symbol"]+evcols+['Action'],125)
    st.markdown('<div class="rs-section">Price & 30W MA</div>',unsafe_allow_html=True)
    if st.button("Load interactive chart", type="primary"):
        with st.spinner("Loading history…"):
            hist=download_yfinance_history(sym)
        if hist is None or hist.empty: st.error("No usable market history returned for this symbol.")
        else:
            h=hist.sort_index().tail(420).copy(); ma=ma_30w_series(h.Close)
            chart_df=pd.DataFrame({"Close":h.Close,"30W MA":ma}).dropna(how="all")
            st.line_chart(chart_df,height=420)
    st.markdown('<div class="rs-section">Calculation detail</div>',unsafe_allow_html=True)
    detail={k:row[k] for k in ["R3M","R6M","R9M","R12M","RS_Blend","RS_Score","MA_30W","MA_30W_Slope_10S_Pct","High_52W","Volume_Ratio","U_D"] if k in row.index}
    st.dataframe(pd.DataFrame({"Measure":list(detail.keys()),"Value":[fmt(v) if k not in ("RS_Score",) else fmt(v,0) for k,v in detail.items()]}),hide_index=True,use_container_width=True,height=360)

with tabs[5]:
    st.markdown('<div class="rs-section">Methodology</div><div class="rs-note">The platform exposes the mathematics and the interpretation layer separately.</div>',unsafe_allow_html=True)
    st.markdown('''**Information boundary**  
Every production signal terminates at the latest completed NSE session. The upcoming/incomplete session is never used.

**Relative Strength**  
3/6/9/12-month calendar-date returns → `RS_Blend = 0.40×R3 + 0.20×R6 + 0.20×R9 + 0.20×R12` → cross-sectional percentile score using the locked `method="min"` transformation.

**Stage**  
30-calendar-week simple moving average using valid NSE observations, with the locked 10-session percentage slope.

**Evidence**  
52-calendar-week high, prior-50-session shifted volume baseline, 20-session U/D, breakout and confirmation are independently calculated before the Action layer.

**Action**  
`BUY★ · BUY · HOLD · WAIT · WATCH★ · WATCH · REDUCE · SELL · AVOID` from the adopted v2 interpretation guide. Stage has precedence when it conflicts with RS.

**Data**  
Official Nifty Total Market universe + yfinance history. Adjusted OHLC and raw Volume are preserved according to the data specification. `DUMMY*` constituents are excluded before Yahoo acquisition.
''')

st.markdown('<div class="rs-foot">RS-Stages · quantitative research platform · validated repository snapshot · Action is decision support, not a guarantee of future returns.</div>',unsafe_allow_html=True)
