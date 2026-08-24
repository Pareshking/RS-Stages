from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from rs_stages.pipeline import acquire_and_build_universe_snapshots
from rs_stages.screener import analyze_universe

st.set_page_config(page_title="RS-Stages", page_icon="RS", layout="wide")

st.title("RS-Stages")
st.caption("Pre-market Relative Strength and Stage research")

home, screen, methodology = st.tabs(["Overview", "Research", "Methodology"])

with home:
    st.subheader("A transparent quantitative research platform")
    st.write(
        "RS-Stages evaluates the NSE constituent universe using calendar-based relative strength, "
        "a 30-calendar-week moving average, 52-calendar-week highs, volume behaviour, and stage/breakout states."
    )
    st.info(
        "All calculations use information through the latest completed NSE session before the selected decision session. "
        "The upcoming session is never used."
    )
    st.markdown("**Locked inputs:** NSE CSV universe · yfinance · adjusted Close/High · raw Volume · 3/6/9/12M RS · 30W MA · 52W high · 20-session U/D")

with screen:
    st.subheader("Universe Research")
    csv_file = st.file_uploader("NSE constituent CSV", type=["csv"])
    decision = st.date_input("Decision session", value=date.today())
    start = st.date_input("History start", value=date(2024, 1, 1))
    end = st.date_input("History end (exclusive)", value=date.today())

    if st.button("Run Research", type="primary", disabled=csv_file is None):
        path = "/tmp/rs_stages_nse.csv"
        with open(path, "wb") as handle:
            handle.write(csv_file.getvalue())
        with st.spinner("Downloading and validating market data…"):
            universe = acquire_and_build_universe_snapshots(path, start, end, pd.Timestamp(decision))
            result = analyze_universe(universe.snapshots)
        st.success(f"Analysed {len(result):,} NSE symbols using the pre-market information boundary.")
        st.dataframe(result.reset_index(), use_container_width=True, hide_index=True)

with methodology:
    st.subheader("Methodology")
    st.markdown(
        """
        - **RS:** 3/6/9/12 calendar-month returns, blended 40/20/20/20.
        - **RS score:** cross-sectional `rank(pct=True, method='min') × 98 + 1`, rounded.
        - **Stage:** mean of all valid sessions in the preceding 30 calendar weeks.
        - **Slope:** 10 trading sessions.
        - **52W high:** adjusted High over 52 calendar weeks, requiring at least 200 valid sessions.
        - **Volume ratio:** latest completed session volume divided by the preceding 50-session average.
        - **U/D:** up/down volume over the 20 completed sessions ending at the latest completed session.
        - **Breakout:** Stage 2 + within 3% of 52W high + Volume Ratio > 1.5.
        - **Breakout Confirmed:** Breakout + U/D > 1.3.
        - **Liquidity:** optional UI filter only; it does not change RS ranking.
        """
    )
