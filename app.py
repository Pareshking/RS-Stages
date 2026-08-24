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
    st.markdown(
        "**Locked inputs:** NSE CSV universe · yfinance · adjusted Close/High · raw Volume · "
        "3/6/9/12M RS · 30W MA · 52W high · 20-session U/D"
    )

with screen:
    st.subheader("Universe Research")
    csv_file = st.file_uploader("NSE constituent CSV", type=["csv"])
    decision = st.date_input("Decision session", value=date.today())
    start = st.date_input("History start", value=date(2024, 1, 1))
    end = st.date_input("History end (exclusive)", value=date.today())

    if start >= end:
        st.error("History start must be earlier than the exclusive history end.")
    elif pd.Timestamp(decision) <= pd.Timestamp(start):
        st.warning("The history start must precede the decision session so all required lookbacks can be evaluated.")

    if st.button("Run Research", type="primary", disabled=csv_file is None or start >= end):
        path = "/tmp/rs_stages_nse.csv"
        with open(path, "wb") as handle:
            handle.write(csv_file.getvalue())
        with st.spinner("Downloading and validating market data…"):
            universe = acquire_and_build_universe_snapshots(
                path, start, end, pd.Timestamp(decision)
            )
            result = analyze_universe(universe.snapshots)

        dates = [snapshot.latest_completed_session for snapshot in universe.snapshots.values()]
        if dates:
            latest_common = min(dates)
            latest_dates = pd.Series(dates).value_counts().sort_index(ascending=False).head(5)
        else:
            latest_common = None
            latest_dates = pd.Series(dtype=int)

        st.success(f"Analysed {len(result):,} NSE symbols using the pre-market information boundary.")

        with st.expander("Calculation traceability", expanded=True):
            st.write(f"**Decision session:** {pd.Timestamp(decision).date()}")
            st.write(f"**History requested:** {pd.Timestamp(start).date()} through {pd.Timestamp(end).date()} (end exclusive)")
            st.write(f"**Earliest latest-completed-session across symbols:** {latest_common.date() if latest_common is not None else 'None'}")
            st.write("**Price inputs:** adjusted Close and adjusted High")
            st.write("**Volume input:** raw share Volume")
            st.write("**Information boundary:** latest completed NSE session strictly before the decision session")
            st.write("**RS:** 3/6/9/12 calendar-month simple returns; 40/20/20/20 blend; cross-sectional min-percentile score")
            st.write("**Stage:** 30-calendar-week SMA; 10-session slope")
            st.write("**52W high:** 52-calendar-week adjusted High; minimum 200 valid sessions")
            st.write("**Volume Ratio:** latest completed session / preceding 50-session average")
            st.write("**U/D:** 20 completed sessions, unchanged closes excluded")
            st.write("**Liquidity:** optional UI filter only; minimum 20 valid completed sessions")
            st.write("**Missing history:** retained as explicit NaN/False outputs rather than fabricated values")

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
