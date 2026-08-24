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

st.set_page_config(page_title="RS-Stages · Quantitative Research", page_icon="RS", layout="wide", initial_sidebar_state="collapsed")
RESEARCH = Path("data/latest_research.csv")
UNIVERSE = Path("data/ind_niftytotalmarket_list.csv")

st.markdown("""
<style>
:root{color-scheme:light}.stApp{background:#fbfcfe;color:#172033}.block-container{max-width:1480px;padding:1rem 2rem 4rem}
[data-testid="stSidebar"]{display:none}[data-testid="stToolbar"]{visibility:hidden;height:0}[data-testid="stDecoration"]{display:none}
.rsnav{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e5e9ef;padding:.2rem 0 .75rem}.brand{display:flex;gap:.65rem;align-items:center}.mark{width:32px;height:32px;border-radius:9px;background:#172033;color:white;display:grid;place-items:center;font-size:.68rem;font-weight:850}.brand b{letter-spacing:-.03em}.sub{font-size:.62rem;color:#8994a4;margin-top:1px}.ey{font-size:.62rem;letter-spacing:.18em;text-transform:uppercase;color:#7b8798;font-weight:800;margin-top:1.25rem}.hero{font-size:clamp(2.1rem,4.3vw,3.7rem);line-height:.98;letter-spacing:-.065em;font-weight:850;color:#121a2a;margin:.25rem 0 .7rem}.lead{max-width:880px;color:#68758a;font-size:.95rem;line-height:1.65}.sec{font-size:1.08rem;font-weight:800;letter-spacing:-.03em;margin:1.55rem 0 .5rem}.muted{font-size:.74rem;line-height:1.55;color:#7d8898}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:.8rem 0 1.15rem}.metric{background:#fff;border:1px solid #e0e6ed;border-radius:14px;padding:14px 15px;min-height:80px}.ml{font-size:.6rem;letter-spacing:.13em;text-transform:uppercase;color:#7f8a9a;font-weight:800}.mv{font-size:1.5rem;font-weight:850;letter-spacing:-.05em;margin-top:6px}.ms{font-size:.65rem;color:#99a3b1;margin-top:3px}.badge{display:inline-flex;border:1px solid #dfe5ec;border-radius:999px;padding:.28rem .62rem;font-size:.67rem;font-weight:800;background:#fff}.green{color:#17724a;background:#f1faf5;border-color:#cbe7d6}.blue{color:#356488;background:#f1f6fb;border-color:#d5e2ef}.amber{color:#7a6414;background:#fff9e9;border-color:#eee0ae}.orange{color:#99551f;background:#fff6ed;border-color:#eed9c5}.red{color:#a03a3a;background:#fff3f3;border-color:#eed0d0}.actioncard{background:#fff;border:1px solid #dfe6ee;border-radius:16px;padding:17px 20px;box-shadow:0 4px 18px rgba(23,32,51,.04)}.actionname{font-size:1.9rem;font-weight:900;letter-spacing:-.055em}.reason{font-size:.77rem;line-height:1.55;color:#69768a;margin-top:.3rem}.left-buy{border-left:5px solid #23835b}.left-hold{border-left:5px solid #4b78a0}.left-wait,.left-watch{border-left:5px solid #c19b2b}.left-reduce{border-left:5px solid #bf742d}.left-sell,.left-avoid{border-left:5px solid #b54a4a}.ev{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0}.ei{background:#fff;border:1px solid #e1e6ed;border-radius:11px;padding:10px 12px}.el{font-size:.58rem;text-transform:uppercase;letter-spacing:.1em;color:#8792a2;font-weight:800}.evv{font-size:.9rem;font-weight:800;margin-top:4px}.detail{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e1e6ed;font-size:.76rem}.detail td{padding:9px 12px;border-bottom:1px solid #edf0f4}.detail td:first-child{color:#7c8797;width:45%}.detail td:last-child{font-weight:700;color:#253045}.stTabs [data-baseweb="tab-list"]{gap:1.2rem;border-bottom:1px solid #e4e8ee}.stTabs [data-baseweb="tab"]{height:2.7rem;padding:0;color:#748095;font-size:.82rem;font-weight:680}.stTabs [aria-selected="true"]{color:#182133}.stTabs [data-baseweb="tab-highlight"]{height:2px;background:#182133}[data-testid="stDataFrame"]{border:1px solid #e1e6ed;border-radius:12px;overflow:hidden}div[data-baseweb="select"]>div{border-color:#dfe5ed;border-radius:9px;background:#fff}.footer{margin-top:2rem;color:#9aa4b3;font-size:.66rem;line-height:1.55}
@media(max-width:850px){.block-container{padding:.8rem .75rem 3rem}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.metric{padding:11px 12px}.mv{font-size:1.3rem}.hero{font-size:2.45rem}.ev{grid-template-columns:repeat(2,minmax(0,1fr))}.stTabs [data-baseweb="tab-list"]{overflow-x:auto;scrollbar-width:none;gap:.9rem}}
</style>
""", unsafe_allow_html=True)


def n(v,d=2):
    try:return "—" if pd.isna(v) else f"{float(v):,.{d}f}"
    except:return "—"
def pct(v,d=1):
    try:return "—" if pd.isna(v) else f"{float(v):+.{d}f}%"
    except:return "—"
def ratio(v):
    try:
        if pd.isna(v):return "—"
        x=float(v);return "∞" if np.isinf(x) else f"{x:.2f}×"
    except:return "—"
def inr(v):
    try:
        if pd.isna(v):return "—"
        x=float(v);return f"₹{x/1e7:,.1f} Cr" if abs(x)>=1e7 else (f"₹{x/1e5:,.1f} L" if abs(x)>=1e5 else f"₹{x:,.0f}")
    except:return "—"
def stage(v):return str(v).split(" — ",1)[0] if pd.notna(v) else "Unknown"
def acol(a):return {"BUY★":"green","BUY":"green","HOLD":"blue","WAIT":"amber","WATCH★":"amber","WATCH":"amber","REDUCE":"orange","SELL":"red","AVOID":"red"}.get(a,"amber")
def action_card(a):return f'<span class="badge {acol(a)}">{html.escape(a)}</span>'
def metrics(items):st.markdown('<div class="grid">'+''.join(f'<div class="metric"><div class="ml">{html.escape(k)}</div><div class="mv">{html.escape(v)}</div><div class="ms">{html.escape(s)}</div></div>' for k,v,s in items)+'</div>',unsafe_allow_html=True)

@st.cache_data(ttl=1800,show_spinner=False)
def load():
    r=pd.read_csv(RESEARCH);u=pd.read_csv(UNIVERSE)
    r["Symbol"]=r["Symbol"].astype(str).str.strip();u["Symbol"]=u["Symbol"].astype(str).str.strip()
    company=next((c for c in ["Company Name","Company","Name"] if c in u.columns),None)
    cols=["Symbol","Industry"]+([company] if company else [])
    d=r.merge(u[cols].drop_duplicates("Symbol"),on="Symbol",how="left",suffixes=("","_u"))
    if "Industry_u" in d:d["Industry"]=d["Industry"].fillna(d["Industry_u"]);d.drop(columns="Industry_u",inplace=True)
    if company:d["Company"]=d[company]
    d["Stage_Label"]=d["Stage"].map(stage);d["Action"]=d.apply(action_for,axis=1);d["Action_Reason"]=d.apply(lambda x:action_reason(x,x.Action),axis=1)
    return d,u

def chart(hist,symbol):
    f=hist.sort_index().tail(420);ma=ma_30w_series(hist.Close);c=[];m=[]
    for i,r in f.iterrows():
        if all(pd.notna(r.get(k)) for k in ["Open","High","Low","Close"]):c.append({"time":i.strftime("%Y-%m-%d"),"open":float(r.Open),"high":float(r.High),"low":float(r.Low),"close":float(r.Close)})
        if i in ma.index and pd.notna(ma.loc[i]):m.append({"time":i.strftime("%Y-%m-%d"),"value":float(ma.loc[i])})
    p=json.dumps({"c":c,"m":m})
    components.html(f'''<div id="x" style="height:500px"></div><script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script><script>const p={p},e=document.getElementById("x"),ch=LightweightCharts.createChart(e,{{autoSize:true,layout:{{background:{{type:"solid",color:"#fff"}},textColor:"#68758a"}},grid:{{vertLines:{{color:"#f0f2f5"}},horzLines:{{color:"#f0f2f5"}}}}}});let cs=ch.addCandlestickSeries({{upColor:"#23835b",downColor:"#c95757",borderVisible:false,wickUpColor:"#23835b",wickDownColor:"#c95757"}});cs.setData(p.c);let ms=ch.addLineSeries({{color:"#557da0",lineWidth:2,crosshairMarkerVisible:false}});ms.setData(p.m);ch.timeScale().fitContent();</script><div style="font:11px system-ui;color:#8a95a5;padding:6px 10px;border-top:1px solid #edf0f4">{html.escape(symbol)} · daily candles · 30-calendar-week MA</div>''',height=550,scrolling=False)

d,u=load();date=pd.to_datetime(d.Date,errors="coerce").max();rsn=d.RS_Score.notna().sum();s2=(d.Stage_Label=="Stage 2").sum();conf=d.Breakout_Confirmed.fillna(False).astype(bool).sum() if "Breakout_Confirmed" in d else 0
st.markdown('<div class="rsnav"><div class="brand"><div class="mark">RS</div><div><b>RS-Stages</b><div class="sub">NIFTY TOTAL MARKET · QUANTITATIVE RESEARCH</div></div></div><span class="badge green">Validated snapshot</span></div>',unsafe_allow_html=True)
st.markdown('<div class="ey">Nifty Total Market · decision support</div><div class="hero">Find leadership.<br>Understand the stage.</div><div class="lead">A transparent research platform for Relative Strength, Weinstein-style stages, breakout evidence, industry breadth and guide-based actions. Evidence stays visible; the Action layer never replaces the calculations.</div>',unsafe_allow_html=True)
tabs=st.tabs(["Dashboard","Screener","Industries","Movers","Stock","Methodology"])

with tabs[0]:
    st.markdown(f'<span class="badge">Decision date · {date.strftime("%d %b %Y") if pd.notna(date) else "—"}</span>',unsafe_allow_html=True)
    metrics([("Universe",f"{len(u):,}","official Nifty Total Market"),("Valid RS",f"{rsn:,}","cross-sectional rank"),("Stage 2",f"{s2:,}","advancing structure"),("Confirmed",f"{conf:,}","breakout + U/D > 1.3")])
    a,b=st.columns([1.1,.9]);
    with a:
        st.markdown('<div class="sec">Stage breadth</div>',unsafe_allow_html=True);x=d.Stage_Label.value_counts().reindex(["Stage 1","Stage 2","Stage 3","Stage 4"]).fillna(0).astype(int);st.dataframe(pd.DataFrame({"Stage":x.index,"Stocks":x.values}),hide_index=True,use_container_width=True,height=205)
    with b:
        st.markdown('<div class="sec">Action board</div>',unsafe_allow_html=True);x=d.Action.value_counts().reindex(["BUY★","BUY","HOLD","WAIT","WATCH★","WATCH","REDUCE","SELL","AVOID"]).fillna(0).astype(int);st.dataframe(pd.DataFrame({"Action":x.index,"Stocks":x.values}),hide_index=True,use_container_width=True,height=205)
    st.markdown('<div class="sec">Leadership board</div><div class="muted">Sorted by RS, with the guide Action shown at the end.</div>',unsafe_allow_html=True)
    cols=[c for c in ["Symbol","Company","Industry","RS_Score","Stage_Label","Volume_Ratio","U_D","Breakout_Confirmed","Action"] if c in d];v=d[d.Action.isin(["BUY★","BUY","HOLD"])].sort_values(["RS_Score","Breakout_Confirmed"],ascending=[False,False]).head(15)[cols].copy();
    if "RS_Score" in v:v["RS_Score"]=pd.to_numeric(v.RS_Score).round().astype("Int64")
    if "Volume_Ratio" in v:v["Volume_Ratio"]=v.Volume_Ratio.map(ratio)
    if "U_D" in v:v["U_D"]=v.U_D.map(ratio)
    st.dataframe(v,hide_index=True,use_container_width=True,height=390)

with tabs[1]:
    st.markdown('<div class="sec">Relative-strength screener</div><div class="muted">Filters are presentation-only. Action is deliberately the final column.</div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4);inds=["All"]+sorted(d.Industry.dropna().astype(str).unique());ind=c1.selectbox("Industry",inds);stg=c2.selectbox("Stage",["All","Stage 1","Stage 2","Stage 3","Stage 4"]);act=c3.selectbox("Action",["All","BUY★","BUY","HOLD","WAIT","WATCH★","WATCH","REDUCE","SELL","AVOID"]);minrs=c4.number_input("Minimum RS",1,99,1)
    c5,c6=st.columns([2,1]);q=c5.text_input("Search symbol / company",placeholder="e.g. BEL, DIXON, TRENT");liq=c6.checkbox("Liquid only")
    v=d.copy()
    if ind!="All":v=v[v.Industry.astype(str)==ind]
    if stg!="All":v=v[v.Stage_Label==stg]
    if act!="All":v=v[v.Action==act]
    v=v[pd.to_numeric(v.RS_Score,errors="coerce").fillna(0)>=minrs]
    if liq and "Liquid_UI_Filter" in v:v=v[v.Liquid_UI_Filter.fillna(False)]
    if q:
        z=q.strip().upper();name=v.get("Company",pd.Series(index=v.index,dtype=str)).astype(str).str.upper();v=v[v.Symbol.str.upper().str.contains(z,na=False)|name.str.contains(z,na=False)]
    cols=[c for c in ["Symbol","Company","Industry","RS_Score","R3M","R6M","R9M","R12M","Stage_Label","MA_30W","MA_30W_Slope_10S_Pct","Near_52W_High","Volume_Ratio","U_D","Breakout","Breakout_Confirmed","Extended_20Pct","Below_50DMA","Action"] if c in v]
    out=v.sort_values("RS_Score",ascending=False)[cols].copy()
    if "RS_Score" in out:out.RS_Score=pd.to_numeric(out.RS_Score,errors="coerce").round().astype("Int64")
    for c in ["R3M","R6M","R9M","R12M"]:
        if c in out:out[c]=out[c].map(pct)
    if "MA_30W" in out:out.MA_30W=out.MA_30W.map(n)
    if "MA_30W_Slope_10S_Pct" in out:out.MA_30W_Slope_10S_Pct=out.MA_30W_Slope_10S_Pct.map(pct)
    for c in ["Volume_Ratio","U_D"]:
        if c in out:out[c]=out[c].map(ratio)
    st.markdown(f'<div class="muted">{len(out):,} stocks shown</div>',unsafe_allow_html=True);st.dataframe(out,hide_index=True,use_container_width=True,height=620)

with tabs[2]:
    st.markdown('<div class="sec">Industry leadership</div><div class="muted">Exact NSE Industry field; no remapping.</div>',unsafe_allow_html=True)
    x=d.groupby("Industry",dropna=False).agg(Stocks=("Symbol","count"),Avg_RS=("RS_Score","mean"),Stage2=("Stage_Label",lambda s:(s=="Stage 2").sum()),Buy=("Action",lambda s:s.isin(["BUY★","BUY"]).sum()),Reduce=("Action",lambda s:(s=="REDUCE").sum()),Sell=("Action",lambda s:(s=="SELL").sum())).reset_index().sort_values("Avg_RS",ascending=False);x.Avg_RS=x.Avg_RS.round(1);st.dataframe(x,hide_index=True,use_container_width=True,height=620)

with tabs[3]:
    st.markdown('<div class="sec">Movers & setups</div><div class="muted">No fabricated historical mover series. This view surfaces the strongest current setups supported by the snapshot.</div>',unsafe_allow_html=True)
    cols=[c for c in ["Symbol","Company","Industry","RS_Score","Stage_Label","R3M","R6M","R9M","R12M","Breakout","Breakout_Confirmed","Action"] if c in d];x=d.sort_values(["Breakout_Confirmed","RS_Score","R3M"],ascending=[False,False,False]).head(50)[cols].copy();
    if "RS_Score" in x:x.RS_Score=pd.to_numeric(x.RS_Score,errors="coerce").round().astype("Int64")
    for c in ["R3M","R6M","R9M","R12M"]:
        if c in x:x[c]=x[c].map(pct)
    st.dataframe(x,hide_index=True,use_container_width=True,height=620)

with tabs[4]:
    selected=st.selectbox("Search / select symbol",sorted(d.Symbol.tolist()))
    r=d[d.Symbol==selected].iloc[0];a=r.Action
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:start"><div><div style="font-size:2rem;font-weight:900;letter-spacing:-.055em">{html.escape(selected)}</div><div class="muted">{html.escape(str(r.get("Company","") or ""))} · {html.escape(str(r.get("Industry","") or ""))}</div></div>{action_card(a)}</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="actioncard left-{a.replace("★","").lower()}"><div class="actionname">{html.escape(a)}</div><div class="reason">{html.escape(action_reason(r,a))}</div></div>',unsafe_allow_html=True)
    metrics([("Stage",stage(r.Stage),"30W MA structure"),("RS",n(r.RS_Score,0),"80+ = guide leadership"),("Volume",ratio(r.Volume_Ratio),"prior-50-session baseline"),("U/D",ratio(r.U_D),"20-session volume balance")])
    vals=[("52W proximity","YES" if bool(r.get("Near_52W_High")) else "NO"),("Breakout","YES" if bool(r.get("Breakout")) else "NO"),("Confirmed","YES" if bool(r.get("Breakout_Confirmed")) else "NO"),("Timing","EXTENDED" if bool(r.get("Extended_20Pct")) else ("BELOW 50DMA" if bool(r.get("Below_50DMA")) else "CLEAR"))];st.markdown('<div class="ev">'+''.join(f'<div class="ei"><div class="el">{k}</div><div class="evv">{v}</div></div>' for k,v in vals)+'</div>',unsafe_allow_html=True)
    try: chart(download_yfinance_history(selected,pd.Timestamp(r.Date)-pd.Timedelta(days=800),pd.Timestamp(r.Date)+pd.Timedelta(days=1)),selected)
    except Exception as e:st.warning(f"Chart data unavailable: {e}")
    st.markdown('<div class="sec">Calculation detail</div>',unsafe_allow_html=True)
    rows=[("R3M",pct(r.R3M)),("R6M",pct(r.R6M)),("R9M",pct(r.R9M)),("R12M",pct(r.R12M)),("30W MA",n(r.MA_30W)),("30W slope",pct(r.MA_30W_Slope_10S_Pct)),("52W High",n(r.High_52W)),("Volume Ratio",ratio(r.Volume_Ratio)),("U/D",ratio(r.U_D)),("50DMA",n(r.SMA_50)),("Avg Value 20",inr(r.AvgValue20)),("Action reason",action_reason(r,a))];st.markdown('<table class="detail">'+''.join(f'<tr><td>{k}</td><td>{html.escape(v)}</td></tr>' for k,v in rows)+'</table>',unsafe_allow_html=True)

with tabs[5]:
    st.markdown('<div class="sec">Methodology & action rules</div>',unsafe_allow_html=True)
    st.markdown('<div class="actioncard"><b>Information boundary</b><br><span class="muted">Only completed NSE sessions available before the upcoming decision session are permitted. Missing history produces insufficiency.</span><br><br><b>Relative Strength</b><br><span class="muted">3/6/9/12 calendar-month returns, 40/20/20/20 blend, cross-sectional 1–99 score. Guide leadership begins at RS 80.</span><br><br><b>Stage</b><br><span class="muted">30-calendar-week SMA over valid sessions, 10-session percentage slope. Stage 2 = above rising MA; Stage 3 = above non-rising MA; Stage 4 = below non-rising MA; Stage 1 = below rising MA.</span><br><br><b>Breakout</b><br><span class="muted">Stage 2 + within 3% of 52W High + Volume Ratio >1.5×. Confirmation adds U/D >1.3.</span><br><br><b>Actions</b><br><span class="muted">BUY★, BUY, HOLD, WAIT, WATCH★, WATCH, REDUCE, SELL, AVOID. Stage takes precedence when Stage and RS conflict. This nine-label mapping is the project specification adopted from the supplied guide.</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="sec">Source boundary</div><div class="muted">Weinstein informs Stage structure and the 30-week trend lens. O’Neil informs RS leadership and breakout interpretation. Project-defined mechanical mappings are labelled as project decisions. TradingView Lightweight Charts is used only as a charting library; calculations remain repository-side.</div>',unsafe_allow_html=True)

st.markdown('<div class="footer">For research and decision support. Verify underlying data and methodology before real-world investment action.</div>',unsafe_allow_html=True)
