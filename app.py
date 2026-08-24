from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from rs_stages.data import download_yfinance_history
from rs_stages.quant import ma_30w_series

st.set_page_config(page_title="RS-Stages", page_icon="RS", layout="wide", initial_sidebar_state="collapsed")
st.set_option("client.toolbarMode", "minimal")

RESEARCH_PATH = Path("data/latest_research.csv")
UNIVERSE_PATH = Path("data/ind_niftytotalmarket_list.csv")

st.markdown("""
<style>
:root { color-scheme: light; }
.stApp { background:#fff; color:#111827; }
.block-container { max-width:1440px; padding:1.25rem 2.7rem 3.2rem; }
[data-testid="stHeader"] { background:#fff; }
[data-testid="stSidebar"] { display:none; }
/* quiet Streamlit chrome */
[data-testid="stToolbar"] { visibility:hidden; height:0; }
[data-testid="stDecoration"] { display:none; }
/* typography */
.rs-brand { display:flex; align-items:baseline; gap:.55rem; margin:.1rem 0 .75rem; }
.rs-mark { font-size:.72rem; font-weight:750; letter-spacing:.12em; color:#475467; }
.rs-name { font-size:1.08rem; font-weight:720; letter-spacing:-.02em; color:#111827; }
.rs-eyebrow { color:#7b8492; font-size:.66rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase; margin-top:1.2rem; }
.rs-title { color:#111827; font-size:2.55rem; font-weight:720; letter-spacing:-.055em; line-height:1.02; margin:.25rem 0 0; }
.rs-subtitle { color:#667085; font-size:.94rem; line-height:1.55; max-width:780px; margin:.5rem 0 1.25rem; }
.rs-section { color:#111827; font-size:1rem; font-weight:680; letter-spacing:-.018em; margin:1.45rem 0 .45rem; }
.rs-note { color:#7b8492; font-size:.76rem; line-height:1.45; }
.rs-rule { border-top:1px solid #eceef2; margin:.9rem 0 1rem; }
.rs-chip { display:inline-block; padding:.25rem .55rem; border:1px solid #e5e7eb; border-radius:999px; background:#fafafa; color:#59636f; font-size:.7rem; font-weight:600; }
.rs-action { display:inline-block; padding:.28rem .62rem; border-radius:999px; border:1px solid #e5e7eb; font-size:.72rem; font-weight:700; letter-spacing:.01em; }
.rs-action-buy { background:#eef8f1; color:#17633a; border-color:#d8eedf; }
.rs-action-hold { background:#f3f7fb; color:#315b7d; border-color:#dce8f2; }
.rs-action-wait { background:#faf8ef; color:#77631d; border-color:#eee7c9; }
.rs-action-reduce { background:#fff5ed; color:#8a4a17; border-color:#f2dfcb; }
.rs-action-sell { background:#fff0f0; color:#8a2e2e; border-color:#f0d5d5; }
[data-testid="stMetric"] { background:#fff; border:1px solid #e7e9ee; border-radius:9px; padding:.75rem .85rem; box-shadow:none; }
[data-testid="stMetricValue"] { font-size:1.32rem; font-weight:680; letter-spacing:-.035em; }
[data-testid="stMetricLabel"] { color:#7b8492; font-size:.67rem; text-transform:uppercase; letter-spacing:.075em; }
.stTabs [data-baseweb="tab-list"] { gap:1.15rem; border-bottom:1px solid #e7e9ee; }
.stTabs [data-baseweb="tab"] { height:2.65rem; padding:0 .05rem; color:#737d8a; font-size:.84rem; font-weight:570; }
.stTabs [aria-selected="true"] { color:#111827; }
[data-testid="stDataFrame"] { border:1px solid #e7e9ee; border-radius:9px; overflow:hidden; }
[data-testid="stSelectbox"] label, [data-testid="stTextInput"] label, [data-testid="stNumberInput"] label { font-size:.72rem; color:#667085; }
div[data-baseweb="select"] > div { border-color:#e5e7eb; border-radius:7px; }
@media (max-width: 700px) {
  .block-container { padding:1rem .85rem 2.5rem; }
  .rs-title { font-size:2rem; }
  .rs-subtitle { font-size:.88rem; }
  .stTabs [data-baseweb="tab-list"] { gap:.8rem; overflow-x:auto; }
  .stTabs [data-baseweb="tab"] { font-size:.78rem; }
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_research() -> pd.DataFrame:
    if not RESEARCH_PATH.exists():
        raise FileNotFoundError("The validated research snapshot has not been published yet.")
    frame = pd.read_csv(RESEARCH_PATH)
    if "Symbol" not in frame.columns:
        raise ValueError("Research snapshot is missing Symbol")
    frame["Symbol"] = frame["Symbol"].astype(str).str.strip()
    return frame.set_index("Symbol")


@st.cache_data(ttl=3600, show_spinner=False)
def load_stock_history(symbol: str, end_date: str) -> pd.DataFrame:
    return download_yfinance_history(symbol, start=pd.Timestamp(end_date) - pd.Timedelta(days=550), end=pd.Timestamp(end_date) + pd.Timedelta(days=1))


def stage_name(value: object) -> str:
    if not isinstance(value, str):
        return "Unknown"
    return value.replace("Stage 1 — Basing", "Stage 1").replace("Stage 2 — Advancing", "Stage 2").replace("Stage 3 — Topping", "Stage 3").replace("Stage 4 — Declining", "Stage 4")


def action_for(row: pd.Series) -> str:
    """Transparent research overlay; does not alter locked quantitative fields."""
    stage = stage_name(row.get("Stage"))
    rs = row.get("RS_Score")
    breakout = bool(row.get("Breakout_Confirmed", False))
    try:
        rs_valid = pd.notna(rs)
        rs_value = float(rs) if rs_valid else float("nan")
    except (TypeError, ValueError):
        rs_value = float("nan")
    if stage == "Stage 4":
        return "SELL"
    if stage == "Stage 3":
        return "REDUCE"
    if stage == "Stage 2" and rs_value >= 85 and breakout:
        return "BUY"
    if stage == "Stage 2" and rs_value >= 70:
        return "HOLD"
    return "WAIT"


def action_reason(row: pd.Series, action: str) -> str:
    stage = stage_name(row.get("Stage"))
    rs = row.get("RS_Score")
    rs_text = "RS unavailable" if pd.isna(rs) else f"RS {float(rs):.0f}"
    if action == "BUY":
        return f"Stage 2 + {rs_text} + confirmed breakout (Volume Ratio > 1.5 and U/D > 1.3)."
    if action == "HOLD":
        return f"{stage} + {rs_text}; leadership is present but no confirmed breakout requirement is met."
    if action == "REDUCE":
        return f"{stage}; topping structure warrants defensive review rather than a fresh entry."
    if action == "SELL":
        return f"{stage}; price/trend structure is in the declining regime."
    return f"{stage} / {rs_text}; wait for stronger Stage/RS confirmation."


def with_actions(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Action"] = out.apply(action_for, axis=1)
    return out


def styled_actions(frame: pd.DataFrame) -> pd.io.formats.style.Styler:
    def colour_action(value: object) -> str:
        cls = {
            "BUY": "background-color:#eef8f1;color:#17633a;font-weight:700",
            "HOLD": "background-color:#f3f7fb;color:#315b7d;font-weight:700",
            "WAIT": "background-color:#faf8ef;color:#77631d;font-weight:700",
            "REDUCE": "background-color:#fff5ed;color:#8a4a17;font-weight:700",
            "SELL": "background-color:#fff0f0;color:#8a2e2e;font-weight:700",
        }.get(str(value), "")
        return cls
    return frame.style.map(colour_action, subset=["Action"])


def tv_chart(symbol: str) -> None:
    tv_symbol = f"NSE:{symbol}"
    config = {
        "autosize": True,
        "symbol": tv_symbol,
        "interval": "D",
        "timezone": "Asia/Kolkata",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "allow_symbol_change": True,
        "calendar": False,
        "details": False,
        "hide_side_toolbar": True,
        "hide_top_toolbar": False,
        "hide_legend": False,
        "hide_volume": False,
        "hotlist": False,
        "withdateranges": True,
        "save_image": False,
        "backgroundColor": "#ffffff",
        "gridColor": "rgba(46,46,46,0.06)",
        "support_host": "https://www.tradingview.com",
    }
    html = f'''<div style="height:560px;width:100%;"><div class="tradingview-widget-container" style="height:100%;width:100%;"><div class="tradingview-widget-container__widget" style="height:100%;width:100%;"></div><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>{json.dumps(config)}</script></div></div>'''
    components.html(html, height=570, scrolling=False)


# Header
st.markdown('<div class="rs-brand"><span class="rs-mark">RS</span><span class="rs-name">RS-Stages</span></div>', unsafe_allow_html=True)
st.markdown('<div class="rs-eyebrow">Nifty Total Market · quantitative research platform</div>', unsafe_allow_html=True)
st.markdown('<div class="rs-title">Find leadership. Understand the stage.</div>', unsafe_allow_html=True)
st.markdown('<div class="rs-subtitle">A glass-box research dashboard for relative strength, Weinstein-style stage structure, industry breadth and transparent research actions. Every action is derived from visible inputs.</div>', unsafe_allow_html=True)

try:
    result = with_actions(load_research())
except Exception as exc:
    st.error("Research snapshot unavailable")
    st.caption(str(exc))
    st.info("The production snapshot is generated only after the real-data audit and reconciliation workflow passes. No file upload or manual data entry is required.")
    st.stop()

source_universe = pd.read_csv(UNIVERSE_PATH) if UNIVERSE_PATH.exists() else pd.DataFrame()
dummy_count = int(source_universe["Symbol"].astype(str).str.startswith("DUMMY", na=False).sum()) if "Symbol" in source_universe.columns else 0
valid_rs = result["RS_Score"].notna() if "RS_Score" in result else pd.Series(False, index=result.index)
latest = pd.to_datetime(result["Date"], errors="coerce").dropna().max() if "Date" in result else pd.NaT

# Primary navigation mirrors the target product's research flow, while adding a dashboard as requested.
dashboard, screener, industries, movers, stock, methodology = st.tabs(["Dashboard", "Screener", "Industries", "Movers", "Stock", "Methodology"])

with dashboard:
    st.markdown('<span class="rs-chip">Validated snapshot</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="rs-note" style="margin-top:.45rem">Information boundary · {latest.date().isoformat() if pd.notna(latest) else "—"} · latest completed NSE session</div>', unsafe_allow_html=True)

    st.markdown('<div class="rs-section">Market at a glance</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Universe", f"{len(result):,}")
    c2.metric("Valid RS", f"{int(valid_rs.sum()):,}")
    c3.metric("Stage 2", f"{int((result['Stage'].map(stage_name) == 'Stage 2').sum()):,}")
    c4.metric("Breakouts", f"{int(result['Breakout'].sum()):,}")
    c5.metric("Confirmed", f"{int(result['Breakout_Confirmed'].sum()):,}")
    c6.metric("Industries", f"{result['Industry'].nunique():,}")

    left, right = st.columns([1.0, 1.35])
    with left:
        st.markdown('<div class="rs-section">Stage structure</div>', unsafe_allow_html=True)
        stage_counts = result["Stage"].map(stage_name).value_counts().reindex(["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Unknown"], fill_value=0)
        st.bar_chart(stage_counts, height=260)
        st.markdown(f'<div class="rs-note">Breadth above 30W MA: {((result["Stage"].map(stage_name).isin(["Stage 2", "Stage 3"])).mean()*100):.1f}% of the research universe.</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="rs-section">Leaders and research action</div>', unsafe_allow_html=True)
        cols = ["Industry", "RS_Score", "Stage", "Breakout_Confirmed", "Action"]
        leaders = result.loc[valid_rs].sort_values(["RS_Score", "RS_Blend"], ascending=False).head(15)[cols]
        st.dataframe(styled_actions(leaders), use_container_width=True, hide_index=False, height=300)

    st.markdown('<div class="rs-section">Action board</div>', unsafe_allow_html=True)
    ac = result["Action"].value_counts().reindex(["BUY", "HOLD", "WAIT", "REDUCE", "SELL"], fill_value=0)
    a1, a2, a3, a4, a5 = st.columns(5)
    for col, label in zip([a1,a2,a3,a4,a5], ac.index):
        col.metric(label, f"{int(ac[label]):,}")

    st.markdown('<div class="rs-section">What the dashboard is telling you</div>', unsafe_allow_html=True)
    buy_names = result.index[result["Action"] == "BUY"].tolist()[:8]
    sell_names = result.index[result["Action"] == "SELL"].tolist()[:8]
    x, y = st.columns(2)
    with x:
        st.markdown("**Strongest research candidates**")
        st.caption(", ".join(buy_names) if buy_names else "No names currently satisfy the transparent BUY overlay.")
    with y:
        st.markdown("**Declining-stage names**")
        st.caption(", ".join(sell_names) if sell_names else "No names currently classified Stage 4.")

with screener:
    st.markdown('<div class="rs-section">Relative-strength screener</div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-note">Cross-sectional RS is calculated before optional UI filters. Action is a transparent project overlay, not a hidden model output.</div>', unsafe_allow_html=True)
    f1, f2, f3, f4, f5 = st.columns(5)
    industries_list = ["All"] + sorted(result["Industry"].dropna().astype(str).unique().tolist())
    selected_industry = f1.selectbox("Industry", industries_list)
    selected_stage = f2.selectbox("Stage", ["All", "Stage 1", "Stage 2", "Stage 3", "Stage 4"])
    selected_action = f3.selectbox("Action", ["All", "BUY", "HOLD", "WAIT", "REDUCE", "SELL"])
    min_rs = f4.number_input("Minimum RS", min_value=1, max_value=99, value=1, step=1)
    liquid_only = f5.checkbox("Liquid only", value=False)
    search = st.text_input("Search symbol", placeholder="e.g. BEL, DIXON, TRENT")
    view = result.copy()
    if selected_industry != "All": view = view[view["Industry"] == selected_industry]
    if selected_stage != "All": view = view[view["Stage"].map(stage_name) == selected_stage]
    if selected_action != "All": view = view[view["Action"] == selected_action]
    view = view[view["RS_Score"].fillna(0) >= min_rs]
    if liquid_only: view = view[view["Liquid_UI_Filter"]]
    if search: view = view[view.index.astype(str).str.contains(search.strip(), case=False, regex=False)]
    display_cols = ["Industry", "RS_Score", "RS_Blend", "R3M", "R6M", "R9M", "R12M", "Stage", "Near_52W_High", "Volume_Ratio", "U_D", "Breakout", "Breakout_Confirmed", "Action"]
    st.markdown(f'<div class="rs-note">{len(view):,} stocks shown · sorted by RS Score.</div>', unsafe_allow_html=True)
    st.dataframe(styled_actions(view.sort_values(["RS_Score", "RS_Blend"], ascending=False)[display_cols]), use_container_width=True, height=650, hide_index=False)

with industries:
    st.markdown('<div class="rs-section">Industry leadership & rotation</div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-note">Industry is the exact NSE CSV Industry field. No WealthStar sector remapping or consolidation is introduced.</div>', unsafe_allow_html=True)
    industry_summary = result.groupby("Industry", dropna=False).agg(
        Stocks=("RS_Score", "size"), Valid_RS=("RS_Score", "count"), Median_RS=("RS_Score", "median"),
        Stage_2=("Stage", lambda s: (s.map(stage_name) == "Stage 2").sum()),
        Stage_4=("Stage", lambda s: (s.map(stage_name) == "Stage 4").sum()),
        Breakouts=("Breakout", "sum"), Confirmed=("Breakout_Confirmed", "sum"),
    ).sort_values(["Median_RS", "Valid_RS"], ascending=False)
    top_industries = industry_summary.head(20)
    left, right = st.columns([1.45, .85])
    with left:
        st.dataframe(top_industries, use_container_width=True, height=620)
    with right:
        st.markdown('<div class="rs-section">Median RS leaders</div>', unsafe_allow_html=True)
        st.bar_chart(top_industries["Median_RS"], height=400)
        st.markdown('<div class="rs-section">How to read it</div>', unsafe_allow_html=True)
        st.caption("High median RS + high Stage-2 participation indicates broad leadership inside the industry. Use the individual-stock page before acting on any name.")

with movers:
    st.markdown('<div class="rs-section">Setups & movers</div>', unsafe_allow_html=True)
    st.markdown('<div class="rs-note">The current snapshot does not claim historical stage-transition data. This page therefore shows observable current setup changes without inventing yesterday-vs-today transitions.</div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        st.markdown('<div class="rs-section">Confirmed breakouts</div>', unsafe_allow_html=True)
        breakout = result[result["Breakout_Confirmed"]].sort_values(["RS_Score", "RS_Blend"], ascending=False)
        cols = ["Industry", "RS_Score", "Stage", "Near_52W_High", "Volume_Ratio", "U_D", "Action"]
        st.dataframe(styled_actions(breakout[cols].head(40)), use_container_width=True, height=520)
    with b2:
        st.markdown('<div class="rs-section">Stage 2 leaders</div>', unsafe_allow_html=True)
        leaders = result[result["Stage"].map(stage_name) == "Stage 2"].sort_values(["RS_Score", "RS_Blend"], ascending=False)
        st.dataframe(styled_actions(leaders[cols].head(40)), use_container_width=True, height=520)

with stock:
    st.markdown('<div class="rs-section">Individual stock research</div>', unsafe_allow_html=True)
    symbols = sorted(result.index.astype(str).tolist())
    selected_symbol = st.selectbox("Stock", symbols)
    row = result.loc[selected_symbol]
    action = row["Action"]
    st.markdown(f'<span class="rs-action rs-action-{action.lower()}">{action}</span>', unsafe_allow_html=True)
    st.caption(action_reason(row, action))
    st.markdown(f"**{selected_symbol}** · {row.get('Industry', '—')} · {pd.Timestamp(row['Date']).date()}")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("RS Score", "—" if pd.isna(row.get("RS_Score")) else f"{int(row['RS_Score'])}")
    m2.metric("Stage", stage_name(row.get("Stage")))
    m3.metric("RS Blend", "—" if pd.isna(row.get("RS_Blend")) else f"{float(row['RS_Blend']):.2%}")
    m4.metric("3M Return", "—" if pd.isna(row.get("R3M")) else f"{float(row['R3M']):.1%}")
    m5.metric("Volume Ratio", "—" if pd.isna(row.get("Volume_Ratio")) else f"{float(row['Volume_Ratio']):.2f}×")
    m6.metric("U/D", "—" if pd.isna(row.get("U_D")) else f"{float(row['U_D']):.2f}")

    chart_left, chart_right = st.columns([1.7, .8])
    with chart_left:
        st.markdown('<div class="rs-section">Price & 30W structure</div>', unsafe_allow_html=True)
        tv_chart(selected_symbol)
    with chart_right:
        st.markdown('<div class="rs-section">Research checklist</div>', unsafe_allow_html=True)
        checklist = pd.DataFrame({"Check": ["RS leadership", "Stage", "52W proximity", "Volume confirmation", "U/D confirmation", "Liquidity"], "Value": [f"{row.get('RS_Score', '—')}", stage_name(row.get('Stage')), "Yes" if bool(row.get('Near_52W_High', False)) else "No", "Yes" if float(row.get('Volume_Ratio', 0) or 0) > 1.5 else "No", "Yes" if float(row.get('U_D', 0) or 0) > 1.3 else "No", "Yes" if bool(row.get('Liquid_UI_Filter', False)) else "No"]})
        st.dataframe(checklist, use_container_width=True, hide_index=True, height=255)
        st.markdown('<div class="rs-section">Why this action?</div>', unsafe_allow_html=True)
        st.caption(action_reason(row, action))

    st.markdown('<div class="rs-section">Calculation detail</div>', unsafe_allow_html=True)
    detail = pd.DataFrame({"Metric": ["R3M", "R6M", "R9M", "R12M", "MA_30W", "MA_30W slope (10S)", "52W High", "Near 52W High", "AvgValue20", "Breakout", "Breakout Confirmed"], "Value": [row.get("R3M"), row.get("R6M"), row.get("R9M"), row.get("R12M"), row.get("MA_30W"), row.get("MA_30W_Slope_10S_Pct"), row.get("High_52W"), row.get("Near_52W_High"), row.get("AvgValue20"), row.get("Breakout"), row.get("Breakout_Confirmed")]})
    st.dataframe(detail, use_container_width=True, hide_index=True)

with methodology:
    st.markdown('<div class="rs-section">Glass-box methodology</div>', unsafe_allow_html=True)
    st.markdown("**Universe** — Official Nifty Total Market constituent CSV; exact NSE `Industry` field; no F&O filtering.\n\n**Relative Strength** — 3/6/9/12 calendar-month adjusted-Close returns; 40/20/20/20 blend; cross-sectional `rank(pct=True, method='min') × 98 + 1`.\n\n**Stage** — 30-calendar-week SMA over all valid sessions; 10-session percentage slope; Stage 1/2/3/4 follow the repository's locked Close-vs-MA and slope truth table.\n\n**Breakout** — Stage 2 + within 3% of 52-calendar-week adjusted High + Volume Ratio > 1.5. Confirmed adds U/D > 1.3.\n\n**Liquidity** — optional UI filter only: 20 completed sessions of Close × raw Volume with average > ₹5 crore.\n\n**Information boundary** — calculations use only completed NSE sessions available before the decision session. Missing history produces insufficiency, never fabricated values.")
    st.markdown('<div class="rs-section">Research Action overlay</div>', unsafe_allow_html=True)
    st.markdown("The Action column is deliberately **not hidden inside the mathematics**. It is a transparent project-level interpretation layer over the locked RS/Stage outputs: **BUY** = Stage 2 + RS ≥ 85 + confirmed breakout; **HOLD** = Stage 2 + RS ≥ 70 without the BUY condition; **REDUCE** = Stage 3; **SELL** = Stage 4; **WAIT** = everything else. These thresholds are an explicit project overlay, not a claim that Stan Weinstein or any source book specified an RS=85 threshold. They can be independently reviewed without changing the underlying quantitative engine.")
    st.caption("For research and decision support. Verify the underlying data and methodology before taking any real-world investment action.")
