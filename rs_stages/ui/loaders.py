"""Loading of the published research artifacts for the presentation layer.

The UI reads only what the audit published. Nothing here recalculates a locked
field, and nothing substitutes a value for one that is absent: when an artifact
has not been generated yet, the loader says so and the page renders an explicit
notice instead of a plausible-looking number.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..actions import with_actions

DATA_DIR = Path("data")
RESEARCH_PATH = DATA_DIR / "latest_research.csv"
PREVIOUS_PATH = DATA_DIR / "previous_research.csv"
UNIVERSE_PATH = DATA_DIR / "ind_niftytotalmarket_list.csv"
PANEL_PATH = DATA_DIR / "price_panel.parquet"
BREADTH_PATH = DATA_DIR / "breadth_history.csv"

#: Fields introduced by locked-spec v2.1. A snapshot published before that
#: revision simply lacks them; the pages that need them degrade explicitly.
V21_FIELDS = ("Close", "MA_10W", "Low_52W", "Ext_Pct", "Pct_From_52W_High", "Trend_Health")

REGENERATE_HINT = (
    "Run the Real Data Research Audit workflow to publish it. Until then this "
    "section stays empty rather than showing a value the snapshot cannot support."
)


@dataclass
class Snapshot:
    """Everything the UI is allowed to read, plus what is missing and why."""

    research: pd.DataFrame
    universe: pd.DataFrame
    previous: pd.DataFrame | None = None
    panel: pd.DataFrame | None = None
    breadth: pd.DataFrame | None = None
    missing: dict[str, str] = field(default_factory=dict)

    @property
    def decision_date(self) -> pd.Timestamp | None:
        stamp = pd.to_datetime(self.research.get("Date"), errors="coerce").max()
        return None if pd.isna(stamp) else stamp

    @property
    def previous_date(self) -> pd.Timestamp | None:
        if self.previous is None:
            return None
        stamp = pd.to_datetime(self.previous.get("Date"), errors="coerce").max()
        return None if pd.isna(stamp) else stamp

    def has(self, *columns: str) -> bool:
        return all(column in self.research.columns for column in columns)

    def trend_windows(self, sessions: int = 63) -> dict[str, list[float]]:
        """Short close series per symbol for the sparkline column."""
        if self.panel is None or self.panel.empty:
            return {}
        panel = self.panel.sort_values(["Symbol", "Date"])
        return {
            str(symbol): group["Close"].tail(sessions).astype(float).tolist()
            for symbol, group in panel.groupby("Symbol", observed=True)
        }

    def symbol_history(self, symbol: str) -> pd.Series | None:
        """Full retained close series for one symbol, indexed by session."""
        if self.panel is None or self.panel.empty:
            return None
        rows = self.panel[self.panel["Symbol"].astype(str) == str(symbol)]
        if rows.empty:
            return None
        series = rows.set_index("Date")["Close"].astype(float).sort_index()
        series.index = pd.DatetimeIndex(series.index)
        return series


def _read_research(path: Path, universe: pd.DataFrame) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["Symbol"] = frame["Symbol"].astype(str).str.strip()

    # The universe CSV is authoritative for Industry and Company Name; the
    # snapshot may already carry them from the audit's own join.
    columns = ["Symbol"] + [c for c in ("Industry", "Company Name") if c in universe.columns]
    merged = frame.merge(
        universe[columns].drop_duplicates("Symbol"), on="Symbol", how="left", suffixes=("", "_u")
    )
    for column in ("Industry", "Company Name"):
        alias = f"{column}_u"
        if alias in merged.columns:
            if column in merged.columns:
                merged[column] = merged[column].fillna(merged[alias])
            else:
                merged[column] = merged[alias]
            merged = merged.drop(columns=[alias])

    merged["Stage_Label"] = merged["Stage"].map(lambda v: str(v).split(" — ", 1)[0])
    # Action is recomputed from the published columns with the same deterministic
    # function the audit used, so the table and the snapshot cannot disagree.
    return with_actions(merged)


def load_snapshot() -> Snapshot:
    """Read every published artifact, recording whatever is unavailable."""
    missing: dict[str, str] = {}
    universe = pd.read_csv(UNIVERSE_PATH)
    universe["Symbol"] = universe["Symbol"].astype(str).str.strip()
    research = _read_research(RESEARCH_PATH, universe)

    absent = [column for column in V21_FIELDS if column not in research.columns]
    if absent:
        missing["v21_fields"] = (
            "This snapshot predates locked-spec v2.1, so it carries no "
            + ", ".join(absent)
            + ". "
            + REGENERATE_HINT
        )

    previous = None
    if PREVIOUS_PATH.exists():
        try:
            previous = _read_research(PREVIOUS_PATH, universe)
        except (OSError, ValueError, KeyError) as exc:
            missing["previous"] = f"The previous-session snapshot could not be read ({type(exc).__name__})."
    else:
        missing["previous"] = (
            "No previous-session snapshot has been published, so day-over-day changes "
            "cannot be computed. " + REGENERATE_HINT
        )

    panel = None
    if PANEL_PATH.exists():
        try:
            panel = pd.read_parquet(PANEL_PATH)
            panel["Date"] = pd.to_datetime(panel["Date"], errors="coerce")
            panel = panel.dropna(subset=["Date"])
        except (OSError, ValueError, ImportError) as exc:
            missing["panel"] = f"The price panel could not be read ({type(exc).__name__})."
            panel = None
    else:
        missing["panel"] = (
            "No price panel has been published, so price history, trend lines and "
            "sparklines are unavailable. " + REGENERATE_HINT
        )

    breadth = None
    if BREADTH_PATH.exists():
        try:
            breadth = pd.read_csv(BREADTH_PATH)
            breadth["Date"] = pd.to_datetime(breadth["Date"], errors="coerce")
            breadth = breadth.dropna(subset=["Date"]).sort_values("Date")
        except (OSError, ValueError) as exc:
            missing["breadth"] = f"The breadth history could not be read ({type(exc).__name__})."
            breadth = None
    else:
        missing["breadth"] = (
            "No breadth history has been published, so the participation trend cannot "
            "be drawn. " + REGENERATE_HINT
        )

    return Snapshot(
        research=research,
        universe=universe,
        previous=previous,
        panel=panel,
        breadth=breadth,
        missing=missing,
    )
