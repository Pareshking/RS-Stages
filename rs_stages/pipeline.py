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
    download_yfinance_histories,
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
    """Acquire yfinance histories for the complete NSE universe in bulk.

    The NSE CSV remains the authority for the universe. Bulk acquisition is
    bounded into provider-safe batches, while the returned universe remains
    strict: a missing/invalid symbol fails the acquisition rather than being
    silently dropped.
    """
    constituents = load_nse_constituents_csv(constituents_csv)
    return download_yfinance_histories(
        symbols=[str(symbol) for symbol in constituents["Symbol"]],
        start=start,
        end=end,
        batch_size=100,
    )


def acquire_and_build_universe_snapshots(
    constituents_csv: str | Path,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    decision_date: pd.Timestamp,
) -> UniverseSnapshot:
    """Acquire the complete NSE universe, then enforce the pre-market boundary."""
    histories = acquire_universe_histories(constituents_csv, start=start, end=end)
    return build_universe_snapshots(constituents_csv, histories, decision_date)
