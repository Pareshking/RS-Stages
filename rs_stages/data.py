"""Production data-boundary primitives for RS-Stages.

This module deliberately separates acquisition from quantitative calculations.
The key invariant is that pre-market decisions for session D can only consume
information through the latest completed session strictly before D. Even if a
provider already contains D because the market has closed, D is excluded from
that decision's information set.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class DecisionSnapshot:
    """Market data snapshot permitted for a pre-market decision."""

    decision_date: pd.Timestamp
    latest_completed_session: pd.Timestamp
    data: pd.DataFrame


def normalize_session_index(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize a market-data frame to a sorted, unique tz-naive DatetimeIndex."""
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("Market data must use a DatetimeIndex")
    if frame.index.has_duplicates:
        raise ValueError("Duplicate market-data sessions detected")
    out = frame.copy()
    idx = pd.DatetimeIndex(out.index)
    if idx.tz is not None:
        idx = idx.tz_convert(None)
    out.index = idx.normalize()
    if out.index.has_duplicates:
        raise ValueError("Duplicate sessions after timestamp normalization")
    return out.sort_index()


def latest_completed_session(index: pd.DatetimeIndex, decision_date: pd.Timestamp) -> pd.Timestamp:
    """Resolve the latest completed session strictly before decision session D."""
    idx = pd.DatetimeIndex(index).sort_values().unique()
    if idx.tz is not None:
        idx = idx.tz_convert(None)
    decision = pd.Timestamp(decision_date)
    if decision.tzinfo is not None:
        decision = decision.tz_convert(None)
    decision = decision.normalize()
    pos = idx.searchsorted(decision, side="left") - 1
    if pos < 0:
        raise ValueError("No completed market session exists before decision date")
    return idx[pos]


def build_decision_snapshot(market_data: pd.DataFrame, decision_date: pd.Timestamp) -> DecisionSnapshot:
    """Freeze the information set available before the upcoming session opens."""
    data = normalize_session_index(market_data)
    decision = pd.Timestamp(decision_date)
    latest = latest_completed_session(data.index, decision)
    return DecisionSnapshot(
        decision_date=decision.normalize(),
        latest_completed_session=latest,
        data=data.loc[:latest].copy(),
    )


def validate_market_columns(frame: pd.DataFrame) -> None:
    """Require the adjusted-price/raw-volume columns needed by RS-Stages."""
    required = {"Close", "High", "Volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required market columns: {sorted(missing)}")


def load_nse_constituents_csv(path: str | Path) -> pd.DataFrame:
    """Load the NSE universe CSV without silently changing symbols or Industry."""
    frame = pd.read_csv(path)
    required = {"Symbol", "Industry"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"NSE CSV missing required columns: {sorted(missing)}")
    if frame["Symbol"].isna().any() or frame["Industry"].isna().any():
        raise ValueError("NSE CSV contains missing Symbol or Industry values")
    if frame["Symbol"].duplicated().any():
        raise ValueError("NSE CSV contains duplicate symbols")
    return frame.copy()


def yfinance_history_kwargs() -> dict[str, bool]:
    """Return the locked yfinance adjustment policy."""
    return {"auto_adjust": True}
