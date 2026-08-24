from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from rs_stages.pipeline import UniverseSnapshot, acquire_and_build_universe_snapshots
from rs_stages.quant import ma_30w_series
from rs_stages.screener import analyze_universe

st.set_page_config(page_title="RS-Stages", page_icon="RS", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    .block-container {max-width: 1450px; padding-top: 1.4rem; padding-bottom: 2rem;}
    h1, h2, h3 {letter-spacing: -0.02em;}
    [data-testid="stMetric"] {padding: .35rem 0;}
    [data-testid="stMetricLabel"] {font-size: .78rem;}
    [data-testid="stDataFrame"] {border-radius: 8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

UNIVERSE_PATH = Path("data/ind_niftytotalmarket_list.csv")


def _default_decision() -> pd.Timestamp:
    return pd.Timestamp(date.today()).normalize()


@st.cache_data(ttl=3600, show_spinner=False)
def load_live_research(decision_date: pd.Timestamp, refresh_key: int) -> tuple[UniverseSnapshot, pd.DataFrame]:
    """Build the live dashboard from the repository's maintained NSE universe."""
    if not UNIVERSE_PATH.exists():
        raise FileNotFoundError(f"Maintained universe not found: {UNIVERSE_PATH}")
    start = decision_date - pd.DateOffset(months=18)
    end = decision_date + pd.Timedelta(days=1)
    universe = acquire_and_build_universe_snapshots(
        UNIVERSE_PATH, start, end, decision_date
    )
    result = analyze_universe(universe.snapshots)
    industry = universe.constituents[["Symbol", "Industry"]].copy()
    result = result.reset_index().merge(industry, on="Symbol", how="left", validate="one_to_one").set_index("Symbol")
    return universe, result


def stage_name(value: object) -> str:
    if not isinstance(value, str):
        return "Unknown"
    return value.replace("Stage 1 — Basing", "Stage 1").replace("Stage 2 — Advancing", "Stage 2").replace("Stage 3 — Topping", "Stage 3").replace("Stage 4 — Declining", "Stage 4")


if "refresh_key" not in st.session_state:
    st.session_state.refresh_key = 0

with st.sidebar:
    st.markdown("### RS-Stages")
    st.caption("Nifty Total Market · pre-market quantitative dashboard")
    decision = st.date_input("Decision session", value=_default_decision().date())
    if st.button("Refresh market data", use_container_width=True):
        st.session_state.refresh_key += 1
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Data source")
    st.write("Official Nifty Total Market universe")
    st.caption("Industry = exact NSE CSV Industry field")


decision_ts = pd.Timestamp(decision).normalize()

st.title("RS-Stages")
st.caption("Relative Strength · Stage · Breakout · Industry research")

try:
    with st.spinner("Loading the maintained Nifty Total Market universe and latest completed-session data…"):
        universe, result = load_live_research(decision_ts, st.session_state.refresh_key)
except Exception as exc:
    st.error(f"Live dashboard could not load: {exc}")
    st.info("The dashboard uses the repository's maintained Nifty Total Market snapshot automatically; no CSV upload is required.")
    st.stop()

valid_rs = result["RS_Score"].notna()
latest_dates = pd.to_datetime(result["Date"], errors="coerce").dropna()
latest_common = latest_dates.min() if not latest_dates.empty else pd.NaT

home, ranking, industry_tab, stock_tab, methodology = st.tabs(
    ["Dashboard", "RS Ranking", "Industry", "Stock", "Methodology"]
)

with home:
    st.subheader("Market Dashboard")
    st.caption(
        f"Decision session: {decision_ts.date()} · information boundary: latest completed NSE session before the decision"
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Universe", f"{len(result):,}")
    c2.metric("Valid RS", f"{int(valid_rs.sum()):,}")
    c3.metric("Industries", f"{result['Industry'].nunique():,}")
    c4.metric("Breakouts", f"{int(result['Breakout'].sum()):,}")
    c5.metric("Confirmed", f"{int(result['Breakout_Confirmed'].sum()):,}")

    left, right = st.columns([1.05, 1])
    with left:
        st.markdown("#### Stage distribution")
        stage_counts = result["Stage"].map(stage_name).value_counts().reindex(
            ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Unknown"], fill_value=0
        )
        st.bar_chart(stage_counts)
    with right:
        st.markdown("#### Strongest RS")
        cols = ["Industry", "RS_Score", "RS_Blend", "Stage", "Near_52W_High", "Breakout", "Breakout_Confirmed"]
        st.dataframe(
            result.loc[valid_rs].sort_values("RS_Score", ascending=False).head(15)[cols],
            use_container_width=True,
            hide_index=False,
        )

    st.markdown("#### Market / data status")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Latest completed session", latest_common.date().isoformat() if pd.notna(latest_common) else "—")
    s2.metric("Liquid > ₹5Cr", f"{int(result['Liquid_UI_Filter'].sum()):,}")
    s3.metric("Near 52W high", f"{int(result['Near_52W_High'].sum()):,}")
    s4.metric("DUMMY excluded", f"{len(universe.constituents) - len(result):,}")

with ranking:
    st.subheader("RS Ranking")
    f1, f2, f3, f4 = st.columns(4)
    industries = ["All"] + sorted(result["Industry"].dropna().unique().tolist())
    selected_industry = f1.selectbox("Industry", industries)
    stages = ["All", "Stage 1", "Stage 2", "Stage 3", "Stage 4"]
    selected_stage = f2.selectbox("Stage", stages)
    min_rs = f3.number_input("Minimum RS Score", min_value=1, max_value=99, value=1, step=1)
    liquid_only = f4.checkbox("Liquid only", value=False)
    search = st.text_input("Search symbol", placeholder="e.g. RELIANCE")

    view = result.copy()
    if selected_industry != "All":
        view = view[view["Industry"] == selected_industry]
    if selected_stage != "All":
        view = view[view["Stage"].map(stage_name) == selected_stage]
    view = view[view["RS_Score"].fillna(0) >= min_rs]
    if liquid_only:
        view = view[view["Liquid_UI_Filter"]]
    if search:
        view = view[view.index.astype(str).str.contains(search.strip(), case=False, regex=False)]

    display_cols = [
        "Industry", "Date", "RS_Score", "RS_Blend", "R3M", "R6M", "R9M", "R12M",
        "Stage", "MA_30W", "MA_30W_Slope_10S_Pct", "Near_52W_High", "Volume_Ratio",
        "U_D", "AvgValue20", "Breakout", "Breakout_Confirmed",
    ]
    st.caption(f"{len(view):,} stocks shown · liquidity is a display filter and does not change RS ranking")
    st.dataframe(
        view.sort_values(["RS_Score", "RS_Blend"], ascending=False)[display_cols],
        use_container_width=True,
        height=650,
        hide_index=False,
    )

with industry_tab:
    st.subheader("Industry / Sector View")
    st.caption("Industry classification is the exact `Industry` field from the official Nifty Total Market CSV; no remapping is applied.")
    industry_summary = (
        result.groupby("Industry", dropna=False)
        .agg(
            Stocks=("RS_Score", "size"),
            Valid_RS=("RS_Score", "count"),
            Median_RS=("RS_Score", "median"),
            Stage_2=("Stage", lambda s: (s == "Stage 2 — Advancing").sum()),
            Stage_4=("Stage", lambda s: (s == "Stage 4 — Declining").sum()),
            Breakouts=("Breakout", "sum"),
            Confirmed=("Breakout_Confirmed", "sum"),
        )
        .sort_values("Median_RS", ascending=False)
    )
    st.dataframe(industry_summary, use_container_width=True, height=650)
    st.markdown("#### Industry breadth")
    st.bar_chart(industry_summary.head(20)["Median_RS"])

with stock_tab:
    st.subheader("Stock Detail")
    symbol_options = sorted(result.index.astype(str).tolist())
    selected_symbol = st.selectbox("Select stock", symbol_options)
    row = result.loc[selected_symbol]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("RS Score", "—" if pd.isna(row["RS_Score"]) else f"{int(row['RS_Score'])}")
    m2.metric("Stage", stage_name(row["Stage"]))
    m3.metric("RS Blend", "—" if pd.isna(row["RS_Blend"]) else f"{row['RS_Blend']:.2%}")
    m4.metric("Volume Ratio", "—" if pd.isna(row["Volume_Ratio"]) else f"{row['Volume_Ratio']:.2f}×")
    m5.metric("U/D", "—" if pd.isna(row["U_D"]) else f"{row['U_D']:.2f}")

    st.write(f"**Industry:** {row['Industry']}  ·  **Date:** {pd.Timestamp(row['Date']).date()}")
    snap = universe.snapshots[selected_symbol]
    chart = snap.data[["Close"]].copy()
    chart["MA_30W"] = ma_30w_series(chart["Close"])
    st.line_chart(chart.tail(220), height=360)

    detail = pd.DataFrame(
        {
            "Metric": ["R3M", "R6M", "R9M", "R12M", "MA_30W", "MA_30W slope (10S)", "52W High", "Near 52W High", "AvgValue20", "Breakout", "Breakout Confirmed"],
            "Value": [row.get("R3M"), row.get("R6M"), row.get("R9M"), row.get("R12M"), row.get("MA_30W"), row.get("MA_30W_Slope_10S_Pct"), row.get("High_52W"), row.get("Near_52W_High"), row.get("AvgValue20"), row.get("Breakout"), row.get("Breakout_Confirmed")],
        }
    )
    st.dataframe(detail, use_container_width=True, hide_index=True)

with methodology:
    st.subheader("Locked Methodology")
    st.markdown(
        """
        **Universe** — Official Nifty Total Market constituent CSV. Industry is exactly the NSE CSV `Industry` field. No F&O filtering or sector remapping.

        **Relative Strength** — 3/6/9/12 calendar-month returns using the last available NSE session on or before each reference date. Blend = 40% / 20% / 20% / 20%. RS Score = `rank(pct=True, method='min') × 98 + 1`, rounded.

        **Stage** — 30-calendar-week simple moving average using all valid sessions in the calendar window. Slope is the 10-session percentage change in that MA. Stage 1/2/3/4 follow the locked Close-vs-MA and slope truth table.

        **Breakout** — Stage 2 + within 3% of the 52-calendar-week adjusted High + latest completed-session Volume Ratio > 1.5. Confirmed adds U/D > 1.3.

        **Liquidity** — optional display filter only: 20 completed sessions of Close × raw Volume with average > ₹5 crore. It never changes the mathematical RS universe.

        **Information boundary** — all calculations use information through the latest completed NSE session before the selected decision session. The upcoming/incomplete session is never used.
        """
    )
    st.info("This application is a dashboard over the locked V1 quantitative engine. It does not ask the user to upload the maintained NSE universe.")
