"""Deterministic integration pipeline for RS-Stages.

The pipeline connects the locked NSE universe to market-data acquisition and
pre-market snapshots. It deliberately stops before signal calculations:
downstream code must consume the returned snapshots, never raw provider data.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .data import (
    DecisionSnapshot,
    build_decision_snapshot,
    download_yfinance_history,
    load_nse_constituents_csv,
)


@dataclass(frozen=True)
class UniverseSnapshot:
    """NSE universe plus the permitted market-data snapshot for each symbol."""

    constituents: pd.DataFrame
    snapshots: dict[str, DecisionSnapshot]


def build_universe_snapshots(
    constituents_csv: str | Path,
    histories: dict[str, pd.DataFrame],
    decision_date: pd.Timestamp,
) -> UniverseSnapshot:
    """Join NSE symbols to supplied histories and freeze the pre-market set.

    ``histories`` is keyed by NSE CSV Symbol. Every universe symbol must have a
    history. No symbol is silently dropped, and no provider data is allowed to
    bypass the decision-date boundary.
    """
    constituents = load_nse_constituents_csv(constituents_csv)
    missing = [s for s in constituents["Symbol"] if s not in histories]
    if missing:
        raise ValueError(f"Missing market history for universe symbols: {missing}")

    snapshots: dict[str, DecisionSnapshot] = {}
    for symbol in constituents["Symbol"]:
        snapshots[str(symbol)] = build_decision_snapshot(histories[str(symbol)], decision_date)

    return UniverseSnapshot(constituents=constituents, snapshots=snapshots)


def acquire_universe_histories(
    constituents_csv: str | Path,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    """Acquire yfinance histories for every NSE universe symbol.

    The NSE CSV remains the authority for the universe. A failed symbol is not
    silently dropped; the acquisition fails explicitly so the caller cannot
    accidentally calculate a partial universe.
    """
    constituents = load_nse_constituents_csv(constituents_csv)
    histories: dict[str, pd.DataFrame] = {}
    failures: dict[str, str] = {}

    for symbol in constituents["Symbol"]:
        key = str(symbol)
        try:
            histories[key] = download_yfinance_history(key, start=start, end=end)
        except Exception as exc:
            failures[key] = f"{type(exc).__name__}: {exc}"

    if failures:
        raise RuntimeError(f"Market-data acquisition failed for symbols: {failures}")

    return histories


def acquire_and_build_universe_snapshots(
    constituents_csv: str | Path,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    decision_date: pd.Timestamp,
) -> UniverseSnapshot:
    """Acquire the complete NSE universe, then enforce the pre-market boundary."""
    histories = acquire_universe_histories(constituents_csv, start=start, end=end)
    return build_universe_snapshots(constituents_csv, histories, decision_date)
