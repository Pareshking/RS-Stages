"""Production data-boundary primitives for RS-Stages.

Acquisition is separated from quantitative calculations. The pre-market
information-set invariant is enforced before calculations consume the data.
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
    """Normalize market data to a sorted, unique tz-naive DatetimeIndex."""
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
    """Return the latest session strictly before decision session D."""
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
    """Freeze only information available before the upcoming session opens."""
    data = normalize_session_index(market_data)
    decision = pd.Timestamp(decision_date)
    latest = latest_completed_session(data.index, decision)
    return DecisionSnapshot(
        decision_date=decision.normalize(),
        latest_completed_session=latest,
        data=data.loc[:latest].copy(),
    )


def validate_market_columns(frame: pd.DataFrame) -> None:
    """Require adjusted Close/High and raw share Volume columns."""
    required = {"Close", "High", "Volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required market columns: {sorted(missing)}")


def load_nse_constituents_csv(path: str | Path) -> pd.DataFrame:
    """Load the NSE universe and ignore symbols reserved for corporate actions.

    Symbols beginning with the literal prefix ``DUMMY`` are excluded from the
    analytical universe. The downloaded CSV itself remains unchanged so it is
    preserved as the official source file.
    """
    frame = pd.read_csv(path)
    required = {"Symbol", "Industry"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"NSE CSV missing required columns: {sorted(missing)}")
    if frame["Symbol"].isna().any() or frame["Industry"].isna().any():
        raise ValueError("NSE CSV contains missing Symbol or Industry values")
    frame["Symbol"] = frame["Symbol"].astype(str).str.strip()
    if frame["Symbol"].eq("").any():
        raise ValueError("NSE CSV contains empty Symbol values")
    if frame["Symbol"].duplicated().any():
        raise ValueError("NSE CSV contains duplicate symbols")
    return frame.loc[~frame["Symbol"].str.startswith("DUMMY", na=False)].copy()


def yfinance_symbol(symbol: str) -> str:
    """Map an NSE CSV symbol to its Yahoo Finance NSE ticker without changing the universe."""
    symbol = str(symbol).strip()
    if not symbol:
        raise ValueError("Empty NSE symbol")
    return symbol if symbol.upper().endswith(".NS") else f"{symbol}.NS"


def yfinance_history_kwargs() -> dict[str, bool]:
    """Return the locked yfinance adjustment policy."""
    return {"auto_adjust": True}


def download_yfinance_history(symbol: str, start: str | pd.Timestamp, end: str | pd.Timestamp) -> pd.DataFrame:
    """Download one NSE symbol's history using the locked yfinance policy.

    ``end`` is exclusive per yfinance. The caller must still pass the result
    through ``build_decision_snapshot`` before signal calculations.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("yfinance is required for market-data acquisition") from exc

    ticker = yfinance_symbol(symbol)
    frame = yf.download(
        ticker,
        start=pd.Timestamp(start),
        end=pd.Timestamp(end),
        auto_adjust=True,
        progress=False,
        actions=False,
    )
    if frame.empty:
        raise ValueError(f"No market data returned for {ticker}")

    if isinstance(frame.columns, pd.MultiIndex):
        if ticker in frame.columns.get_level_values(-1):
            frame = frame.xs(ticker, axis=1, level=-1)
        elif ticker in frame.columns.get_level_values(0):
            frame = frame.xs(ticker, axis=1, level=0)
    frame = normalize_session_index(frame)
    validate_market_columns(frame)
    return frame
