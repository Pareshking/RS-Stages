"""Deterministic integration pipeline for RS-Stages.

The pipeline connects the locked NSE universe to per-symbol market-data
snapshots. It deliberately stops before signal calculations: downstream code
must consume the returned pre-market snapshots, never raw provider data.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .data import DecisionSnapshot, build_decision_snapshot, load_nse_constituents_csv


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
