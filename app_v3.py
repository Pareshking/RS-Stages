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

st.set_page_config(page_title="RS-Stages | Quantitative Platform", page_icon="RS", layout="wide", initial_sidebar_state="collapsed")
RESEARCH = Path("data/latest_research.csv")
UNIVERSE = Path("data/ind_niftytotalmarket_list.csv")

st.markdown("""
<style>
:root{color-scheme:light}.stApp{background:#f5f7fa;color:#172033}.block-container{max-width:1500px;padding:0 32px 44px}
[data-testid="stSidebar"]{display:none}[data-testid="stToolbar"]{visibility:hidden;height:0}header[data-testid="stHeader"]{height:0;background:transparent}[data-testid="stDecoration"]{display:none}
.rs-top{margin:0 -32px;padding:12px 32px 10px;background:rgba(255,255,255,.97);border-bottom:1px solid #e3e7ec;position:relative;z-index:2}.rs-topline{display:flex;align-items:center;justify-content:space-between;gap:20px}.rs-brand{display:flex;align-items:center;gap:10px}.rs-logo{width:30px;height:30px;border-radius:8px;background:#172033;color:#fff;display:grid;place-items:center;font-size:10px;font-weight:900;letter-spacing:.04em}.rs-brand-title{font-size:15px;font-weight:850;letter-spacing:-.025em}.rs-brand-sub{margin-top:1px;color:#8b95a4;font-size:8px;letter-spacing:.13em;font-weight:800}.rs-status{display:inline-flex;align-items:center;gap:5px;border:1px solid #cfe5d8;background:#f0f8f3;color:#26734d;border-radius:999px;padding:5px 9px;font-size:9px;font-weight:850}.rs-status-dot{width:6px;height:6px;border-radius:50%;background:#2b8a5a}
.rs-kicker{margin-top:25px;color:#7c8796;font-size:9px;letter-spacing:.18em;text-transform:uppercase;font-weight:850}.rs-h1{margin:3px 0 6px;font-size:40px;line-height:1.03;letter-spacing:-.06em;font-weight:900;color:#111a2b}.rs-lead{max-width:900px;color:#687589;font-size:12.5px;line-height:1.62}
.rs-strip{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:18px 0 20px}.rs-metric{position:relative;background:#fff;border:1px solid #dfe5eb;border-radius:12px;padding:12px 13px;overflow:hidden;box-shadow:0 1px 2px rgba(23,32,51,.025)}.rs-metric:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#d8dee6}.rs-metric:nth-child(2):before{background:#6f94b8}.rs-metric:nth-child(3):before{background:#4d9b72}.rs-metric:nth-child(4):before{background:#c59643}.rs-metric:nth-child(5):before{background:#8994a4}.rs-metric-label{color:#7f8a99;font-size:8px;text-transform:uppercase;letter-spacing:.13em;font-weight:850}.rs-metric-value{color:#172033;font-size:21px;line-height:1.1;margin-top:5px;font-weight:900;letter-spacing:-.045em}.rs-metric-note{color:#9aa4b2;font-size:8.5px;margin-top:4px}
.rs-section{margin:22px 0 7px;font-size:16px;font-weight:900;letter-spacing:-.035em;color:#182235}.rs-note{color:#7a8696;font-size:10.5px;line-height:1.5;margin-bottom:9px}.rs-panel{background:#fff;border:1px solid #dfe5eb;border-radius:13px;padding:15px;box-shadow:0 1px 2px rgba(23,32,51,.025)}
.rs-pulse{display:grid;grid-template-columns:1.15fr .85fr;gap:9px;margin:5px 0 4px}.rs-pulse-card{background:#fff;border:1px solid #dfe5eb;border-radius:12px;padding:13px}.rs-pulse-head{display:flex;justify-content:space-between;align-items:center;gap:12px}.rs-pulse-title{font-size:10px;font-weight:850;color:#5e6a7c;text-transform:uppercase;letter-spacing:.12em}.rs-pulse-value{font-size:16px;font-weight:900;color:#182235}.rs-bar{height:7px;background:#edf1f4;border-radius:99px;overflow:hidden;margin-top:9px}.rs-bar>span{display:block;height:100%;border-radius:99px}.rs-stage-row{display:grid;grid-template-columns:58px 1fr 40px;align-items:center;gap:8px;margin:7px 0}.rs-stage-label{font-size:9px;font-weight:800;color:#6d7888}.rs-stage-count{font-size:9px;font-weight:850;text-align:right;color:#263246}.s1{background:#c9a85b}.s2{background:#4b9a72}.s3{background:#bf7b45}.s4{background:#b95b5b}
.rs-action{display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;font-size:9px;font-weight:900;border:1px solid}.buy{color:#176f49;background:#eef8f2;border-color:#c9e4d4}.hold{color:#3d658a;background:#f0f5fa;border-color:#d3dfeb}.wait{color:#7b6415;background:#fff8e7;border-color:#ebdda9}.reduce{color:#97511f;background:#fff4ea;border-color:#ead4bd}.sell{color:#a13d3d;background:#fff1f1;border-color:#ebcccc}
.stTabs [data-baseweb="tab-list"]{gap:2px;background:#fff;border:1px solid #dfe5eb;border-radius:10px;padding:3px;overflow-x:auto}.stTabs [data-baseweb="tab"]{height:31px;padding:0 13px;border-radius:7px;color:#788494;font-size:10px;font-weight:800;white-space:nowrap}.stTabs [aria-selected="true"]{color:#172033;background:#eef1f4}.stTabs [data-baseweb="tab-highlight"]{display:none}div[data-baseweb="select"]>div{background:#fff;border-color:#dce2e8;border-radius:8px}[data-testid="stDataFrame"]{border:1px solid #dfe5eb;border-radius:10px;overflow:hidden;background:#fff}button[kind="primary"]{border-radius:8px;background:#172033;border-color:#172033}.rs-chart{border:1px solid #dfe5eb;border-radius:12px;background:#fff;overflow:hidden}.rs-chart-note{padding:7px 10px;border-top:1px solid #edf0f3;color:#8a94a2;font-size:8.5px}.rs-foot{color:#98a2b0;font-size:8.5px;line-height:1.6;margin-top:28px;border-top:1px solid #e1e6eb;padding-top:11px}
@media(max-width:900px){.block-container{padding:0 12px 34px}.rs-top{margin:0 -12px;padding:11px 12px 9px}.rs-brand-sub{font-size:7px}.rs-h1{font-size:31px;letter-spacing:-.055em}.rs-lead{font-size:11.5px}.rs-strip{grid-template-columns:repeat(2,1fr);gap:7px}.rs-metric{padding:10px 11px}.rs-metric-value{font-size:18px}.rs-pulse{grid-template-columns:1fr}.stTabs [data-baseweb="tab"]{padding:0 10px}}
</style>
""", unsafe_allow_html=True)


def fmt(v,d=1):
    try:return "—" if pd.isna(v) else f"{float(v):,.{d}f}"
    except Exception:return "—"


def pct(v,d=1):
    try:return "—" if pd.isna(v) else f"{float(v):+.{d}f}%"
    except Exception:return "—"


def multiple(v):
    try:
        if pd.isna(v):return "—"
        x=float(v);return "∞" if np.isinf(x) else f"{x:.2f}×"
    except Exception:return "—"


def stage_label(v):return str(v).split(" — ",1)[0] if pd.notna(v) else "Unknown"


def action_class(a):
    if a in ("BUY","BUY★"):return "buy"
    if a=="HOLD":return "hold"
    if a in ("WAIT","WATCH","WATCH★"):return "wait"
    if a=="REDUCE":return "reduce"
    return "sell"


@st.cache_data(ttl=1800,show_spinner=False)
def load_snapshot():
    r=pd.read_csv(RESEARCH);u=pd.read_csv(UNIVERSE)
    for x in (r,u):x["Symbol"]=x["Symbol"].astype(str).str.strip()
    company=next((c for c in ("Company Name","Company","Name") if c in u.columns),None)
    cols=["Symbol"]+(["Industry"] if "Industry" in u.columns else [])+([company] if company else [])
    d=r.merge(u[cols].drop_duplicates("Symbol"),on="Symbol",how="left",suffixes=("","_u"))
    if "Industry_u" in d:
        d["Industry"]=d["Industry"].fillna(d["Industry_u"]);d.drop(columns=["Industry_u"],inplace=True)
    if company:d["Company"]=d[company]
    d["Stage_Label"]=d["Stage"].map(stage_label);d["Action"]=d.apply(action_for,axis=1);d["Action_Reason"]=d.apply(lambda x:action_reason(x,x.Action),axis=1)
    return d,u


def metric_strip(items):
    s='<div class="rs-strip">'
    for label,value,note in items:s+=f'<div class="rs-metric"><div class="rs-metric-label">{html.escape(label)}</div><div class="rs-metric-value">{html.escape(value)}</div><div class="rs-metric-note">{html.escape(note)}</div></div>'
    st.markdown(s+'</div>',unsafe_allow_html=True)


def table(df,cols,height=390):
    v=df[[c for c in cols if c in df]].copy()
    if "RS_Score" in v:v["RS_Score"]=pd.to_numeric(v["RS_Score"],errors="coerce").round().astype("Int64")
    if "Volume_Ratio" in v:v["Volume_Ratio"]=v["Volume_Ratio"].map(multiple)
    if "U_D" in v:v["U_D"]=v["U_D"].map(multiple)
    if "MA_30W_Slope_10S_Pct" in v:v["MA_30W_Slope_10S_Pct"]=v["MA_30W_Slope_10S_Pct"].map(pct)
    st.dataframe(v,hide_index=True,use_container_width=True,height=height)


def lightweight_chart(hist,symbol):
    h=hist.sort_index().tail(420).copy()
    if h.empty or "Close" not in h:
        st.error("No usable market history returned for this symbol.");return
    ma=ma_30w_series(h.Close);candles=[];ma_points=[]
    for idx,r in h.iterrows():
        if all(pd.notna(r.get(k)) for k in ("Open","High","Low","Close")):
            candles.append({"time":idx.strftime("%Y-%m-%d"),"open":float(r.Open),"high":float(r.High),"low":float(r.Low),"close":float(r.Close)})
        if idx in ma.index and pd.notna(ma.loc[idx]):ma_points.append({"time":idx.strftime("%Y-%m-%d"),"value":float(ma.loc[idx])})
    payload=json.dumps({"candles":candles,"ma":ma_points});safe_symbol=html.escape(symbol)
    components.html(f"""
<div class="rs-chart"><div id="rs-chart" style="height:430px"></div><div class="rs-chart-note">{safe_symbol} · daily OHLC · 30-calendar-week SMA · TradingView Lightweight Charts</div></div>
<script src="https://unpkg.com/lightweight-charts@5.2.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
const p={payload};const root=document.getElementById('rs-chart');
const chart=LightweightCharts.createChart(root,{{autoSize:true,layout:{{background:{{type:'solid',color:'#ffffff'}},textColor:'#687589',fontFamily:'system-ui,-apple-system,Segoe UI,sans-serif',fontSize:11}},grid:{{vertLines:{{color:'#f0f2f5'}},horzLines:{{color:'#f0f2f5'}}}},rightPriceScale:{{borderColor:'#e4e8ed'}},timeScale:{{borderColor:'#e4e8ed',rightOffset:4,barSpacing:7}},crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}}}});
const candle=chart.addSeries(LightweightCharts.CandlestickSeries,{{upColor:'#3f956d',downColor:'#cf6262',borderVisible:false,wickUpColor:'#3f956d',wickDownColor:'#cf6262'}});candle.setData(p.candles);
const ma=chart.addSeries(LightweightCharts.LineSeries,{{color:'#5d7f9f',lineWidth:2,crosshairMarkerVisible:false,lastValueVisible:true,priceLineVisible:false}});ma.setData(p.ma);chart.timeScale().fitContent();
</script>
""",height=455,scrolling=False)


d,u=load_snapshot();last=pd.to_datetime(d.get("Date"),errors="coerce").max();valid=int(d.RS_Score.notna().sum()) if "RS_Score" in d else 0;stage2=int((d.Stage_Label=="Stage 2").sum());confirmed=int(d.Breakout_Confirmed.fillna(False).astype(bool).sum()) if "Breakout_Confirmed" in d else 0

st.markdown('<div class="rs-top"><div class="rs-topline"><div class="rs-brand"><div class="rs-logo">RS</div><div><div class="rs-brand-title">RS-Stages</div><div class="rs-brand-sub">NIFTY TOTAL MARKET · QUANTITATIVE PLATFORM</div></div></div><div class="rs-status"><span class="rs-status-dot"></span>VALIDATED SNAPSHOT</div></div></div>',unsafe_allow_html=True)
st.markdown('<div class="rs-kicker">Nifty Total Market · decision support</div><div class="rs-h1">Leadership, stage and action.</div><div class="rs-lead">A transparent quantitative terminal for Relative Strength, 30-week stage structure, breakout evidence, industry context and guide-based actions. The mathematics remains separate from the interpretation layer.</div>',unsafe_allow_html=True)
metric_strip([("Universe",f"{len(u):,}","Nifty Total Market"),("Valid RS",f"{valid:,}","cross-sectional rank"),("Stage 2",f"{stage2:,}","advancing structure"),("Confirmed",f"{confirmed:,}","breakout + U/D > 1.3"),("As of",last.strftime("%d %b %Y") if pd.notna(last) else "—","latest completed NSE session")])

tabs=st.tabs(["Dashboard","Screener","Industries","Movers","Stock","Methodology"])

with tabs[0]:
    st.markdown('<div class="rs-section">Market pulse</div><div class="rs-note">Stage and action counts are directly derived from the validated snapshot. Presentation filters do not alter the quantitative universe.</div>',unsafe_allow_html=True)
    stage_counts=d.Stage_Label.value_counts().reindex(["Stage 1","Stage 2","Stage 3","Stage 4"]).fillna(0).astype(int);total_stage=max(int(stage_counts.sum()),1)
    action_order=["BUY★","BUY","HOLD","WAIT","WATCH★","WATCH","REDUCE","SELL","AVOID"];action_counts=d.Action.value_counts().reindex(action_order).fillna(0).astype(int);top_action=action_counts.idxmax() if action_counts.sum() else "—"
    pulse='<div class="rs-pulse"><div class="rs-pulse-card"><div class="rs-pulse-head"><span class="rs-pulse-title">Stage breadth</span><span class="rs-pulse-value">'+f'{stage2:,} Stage 2</span></div>'
    pulse+=''.join(f'<div class="rs-stage-row"><span class="rs-stage-label">{s}</span><div class="rs-bar"><span class="s{int(s[-1])}" style="width:{min(100,100*int(c)/total_stage):.1f}%"></span></div><span class="rs-stage-count">{int(c):,}</span></div>' for s,c in stage_counts.items())
    pulse+='</div><div class="rs-pulse-card"><div class="rs-pulse-head"><span class="rs-pulse-title">Action centre</span><span class="rs-pulse-value">'+html.escape(str(top_action))+'</span></div>'
    pulse+=''.join(f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px"><span class="rs-action {action_class(a)}">{html.escape(a)}</span><strong style="font-size:10px;color:#263246">{int(c):,}</strong></div>' for a,c in action_counts.items() if int(c)>0)+'</div></div>'
    st.markdown(pulse,unsafe_allow_html=True)
    st.markdown('<div class="rs-section">Strongest setups</div><div class="rs-note">Sorted by RS first, then confirmed breakout evidence. Action is the final visible interpretation.</div>',unsafe_allow_html=True)
    v=d[d.Action.isin(["BUY★","BUY","HOLD"])].sort_values(["RS_Score","Breakout_Confirmed"],ascending=[False,False]).head(20);table(v,["Symbol","Company","Industry","RS_Score","Stage_Label","Volume_Ratio","U_D","Breakout_Confirmed","Action"],390)

with tabs[1]:
    st.markdown('<div class="rs-section">Full-universe screener</div><div class="rs-note">Filters change presentation only; the underlying RS calculation and information boundary are unchanged.</div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4);inds=["All"]+sorted(d.Industry.dropna().astype(str).unique()) if "Industry" in d else ["All"];ind=c1.selectbox("Industry",inds);stg=c2.selectbox("Stage",["All","Stage 1","Stage 2","Stage 3","Stage 4"]);act=c3.selectbox("Action",["All","BUY★","BUY","HOLD","WAIT","WATCH★","WATCH","REDUCE","SELL","AVOID"]);minrs=c4.number_input("Minimum RS",1,99,1);q=st.text_input("Search",placeholder="Symbol or company")
    v=d.copy();
    if ind!="All":v=v[v.Industry.astype(str)==ind]
    if stg!="All":v=v[v.Stage_Label==stg]
    if act!="All":v=v[v.Action==act]
    v=v[pd.to_numeric(v.RS_Score,errors="coerce").fillna(0)>=minrs]
    if q:
        z=q.strip().upper();name=v.get("Company",pd.Series(index=v.index,dtype=str)).astype(str).str.upper();v=v[v.Symbol.str.upper().str.contains(z,na=False)|name.str.contains(z,na=False)]
    table(v.sort_values("RS_Score",ascending=False),["Symbol","Company","Industry","RS_Score","R3M","R6M","R9M","R12M","Stage_Label","MA_30W","MA_30W_Slope_10S_Pct","Near_52W_High","Volume_Ratio","U_D","Breakout","Breakout_Confirmed","Extended_20Pct","Below_50DMA","Action"],520)

with tabs[2]:
    st.markdown('<div class="rs-section">Industry leadership</div><div class="rs-note">Industry classification is taken from the official Nifty Total Market constituent file.</div>',unsafe_allow_html=True)
    g=d.groupby("Industry",dropna=False);indf=g.agg(Stocks=("Symbol","count"),Median_RS=("RS_Score","median"),Leadership=("RS_Score",lambda x:int((pd.to_numeric(x,errors="coerce")>=80).sum())),Stage2=("Stage_Label",lambda x:int((x=="Stage 2").sum())),Buy=("Action",lambda x:int(x.isin(["BUY★","BUY"]).sum())),Sell=("Action",lambda x:int((x=="SELL").sum()))).reset_index().sort_values(["Median_RS","Leadership"],ascending=False);indf["Median_RS"]=indf.Median_RS.round(1);st.dataframe(indf,hide_index=True,use_container_width=True,height=560)

with tabs[3]:
    st.markdown('<div class="rs-section">Movers & setups</div><div class="rs-note">Only fields present in the validated snapshot are shown. No fabricated daily-change series is introduced.</div>',unsafe_allow_html=True)
    top=d.sort_values("RS_Score",ascending=False).head(25);table(top,["Symbol","Company","Industry","RS_Score","Stage_Label","R3M","R6M","Volume_Ratio","U_D","Breakout","Breakout_Confirmed","Action"],540)

with tabs[4]:
    st.markdown('<div class="rs-section">Stock research</div><div class="rs-note">Only validated universe symbols are selectable. This prevents external symbols from entering the quantitative detail path.</div>',unsafe_allow_html=True)
    choices=d.sort_values("RS_Score",ascending=False).Symbol.tolist()
    if not choices:st.warning("No validated symbols are available in the current snapshot.")
    else:
        def stock_name(s):
            m=d.loc[d.Symbol.eq(s),"Company"] if "Company" in d else pd.Series(dtype=str);company=m.iloc[0] if not m.empty and pd.notna(m.iloc[0]) else "";return f"{s} · {company}"
        sym=st.selectbox("Stock",choices,format_func=stock_name);row_df=d.loc[d.Symbol.eq(sym)]
        if row_df.empty:st.error("Selected symbol is not present in the validated snapshot.")
        else:
            row=row_df.iloc[0];a=str(row.get("Action","WAIT"));c=action_class(a);company=str(row.get("Company",sym));industry=str(row.get("Industry","—"))
            st.markdown(f'<div class="rs-panel"><div style="display:flex;justify-content:space-between;gap:18px;align-items:flex-start"><div><div style="font-size:25px;font-weight:900;letter-spacing:-.045em">{html.escape(company)}</div><div style="color:#8992a1;font-size:10px;margin-top:3px">{html.escape(sym)} · {html.escape(industry)}</div></div><span class="rs-action {c}" style="font-size:12px;padding:7px 12px">{html.escape(a)}</span></div><div style="color:#657080;font-size:11px;line-height:1.55;margin-top:12px">{html.escape(str(row.get("Action_Reason","—")))}</div></div>',unsafe_allow_html=True)
            metric_strip([("RS Score",fmt(row.get("RS_Score"),0),"cross-sectional 1–99"),("Stage",str(row.get("Stage_Label","—")),"30W MA + slope"),("30W MA",fmt(row.get("MA_30W"),2),"calendar-week SMA"),("Slope",pct(row.get("MA_30W_Slope_10S_Pct")),"10-session slope"),("U/D",multiple(row.get("U_D")),"20 completed sessions")])
            st.markdown('<div class="rs-section">Evidence</div>',unsafe_allow_html=True);table(pd.DataFrame([row]),["Symbol","Near_52W_High","Volume_Ratio","Breakout","Breakout_Confirmed","Extended_20Pct","Below_50DMA","Action"],125)
            st.markdown('<div class="rs-section">Price & 30W structure</div>',unsafe_allow_html=True)
            if st.button("Load interactive chart",type="primary"):
                with st.spinner("Loading validated market history…"):
                    hist=download_yfinance_history(sym)
                if hist is None or hist.empty:st.error("No usable market history returned for this symbol.")
                else:lightweight_chart(hist,sym)
            st.markdown('<div class="rs-section">Calculation detail</div>',unsafe_allow_html=True)
            detail_keys=["R3M","R6M","R9M","R12M","RS_Blend","RS_Score","MA_30W","MA_30W_Slope_10S_Pct","High_52W","Volume_Ratio","U_D"];detail=[(k,row.get(k)) for k in detail_keys if k in row.index];detail_df=pd.DataFrame({"Measure":[k for k,_ in detail],"Value":[fmt(v,0) if k=="RS_Score" else fmt(v) for k,v in detail]});st.dataframe(detail_df,hide_index=True,use_container_width=True,height=360)

with tabs[5]:
    st.markdown('<div class="rs-section">Methodology</div><div class="rs-note">The platform exposes the mathematics and the guide interpretation layer separately.</div>',unsafe_allow_html=True)
    st.markdown('''**Information boundary**  
Every production signal terminates at the latest completed NSE session. The upcoming/incomplete session is never used.

**Relative Strength**  
3/6/9/12-month calendar-date returns → `RS_Blend = 0.40×R3 + 0.20×R6 + 0.20×R9 + 0.20×R12` → cross-sectional percentile score using the locked `method="min"` transformation.

**Stage**  
30-calendar-week simple moving average using valid NSE observations, with the locked 10-session percentage slope.

**Evidence**  
52-calendar-week high, prior-50-session shifted volume baseline, 20-session U/D, breakout and confirmation are independently calculated before the Action layer.

**Action**  
`BUY★ · BUY · HOLD · WAIT · WATCH★ · WATCH · REDUCE · SELL · AVOID` from the adopted guide. Stage has precedence when it conflicts with RS.

**Data**  
Official Nifty Total Market universe + yfinance history. Adjusted OHLC and raw Volume are preserved according to the data specification. `DUMMY*` constituents are excluded before Yahoo acquisition.
''')

st.markdown('<div class="rs-foot">RS-Stages · quantitative research platform · validated repository snapshot · Charts use TradingView Lightweight Charts (Apache 2.0) with required attribution · Action is decision support, not a guarantee of future returns.</div>',unsafe_allow_html=True)
