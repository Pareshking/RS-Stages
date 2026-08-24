"""Controlled experiment: locked V1 Stage classifier vs a research model.

This file is research-only. It must never be imported by production code.
The research model is intentionally explicit so its assumptions can be changed
and tested without altering the locked V1 methodology.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Scenario:
    name: str
    close: list[float]
    ma: list[float]
    slope_pct: list[float]
    expected_research: str


def locked_v1(close: float, ma: float, slope_pct: float) -> str:
    above = close > ma
    rising = slope_pct > 0.0
    if above and rising:
        return "Stage 2"
    if above and not rising:
        return "Stage 3"
    if not above and not rising:
        return "Stage 4"
    return "Stage 1"


def crossing_count(close: pd.Series, ma: pd.Series) -> int:
    side = np.sign(close - ma)
    # Ignore exact equality when counting a crossing; it is not itself a
    # directional cross.
    side = side.replace(0, np.nan).ffill().bfill()
    return int((side != side.shift(1)).fillna(False).sum())


def research_stage(
    close: pd.Series,
    ma: pd.Series,
    slope_pct: pd.Series,
    *,
    neutral_band_pct: float = 0.02,
    weaving_window: int = 8,
    min_crossings: int = 2,
) -> str:
    """Candidate slope-neutral/weaving classifier for research only.

    Stage 2/4 require a clearly rising/falling MA and price on the matching
    side. A near-zero slope becomes a transition zone: repeated price/MA
    crossings are treated as a consolidation signal. Stage 1 vs Stage 3 is
    separated by the preceding non-neutral slope direction.
    """
    if len(close) != len(ma) or len(close) != len(slope_pct):
        raise ValueError("Series lengths must match")
    if len(close) < max(weaving_window, 2):
        raise ValueError("Insufficient synthetic history")

    slope = float(slope_pct.iloc[-1])
    price = float(close.iloc[-1])
    average = float(ma.iloc[-1])

    if slope > neutral_band_pct and price > average:
        return "Stage 2"
    if slope < -neutral_band_pct and price < average:
        return "Stage 4"

    recent_close = close.iloc[-weaving_window:]
    recent_ma = ma.iloc[-weaving_window:]
    crosses = crossing_count(recent_close, recent_ma)
    if abs(slope) <= neutral_band_pct and crosses >= min_crossings:
        prior = slope_pct.iloc[:-1]
        prior_non_neutral = prior[prior.abs() > neutral_band_pct]
        if len(prior_non_neutral):
            return "Stage 1" if float(prior_non_neutral.iloc[-1]) < 0 else "Stage 3"
        # With no prior directional evidence, classify as a neutral base
        # rather than pretending it is a top.
        return "Stage 1"

    # Outside the candidate consolidation definition, use the directional
    # side/slope combination as a conservative fallback for comparison.
    if slope > 0 and price > average:
        return "Stage 2"
    if slope < 0 and price < average:
        return "Stage 4"
    return "Unclassified"


def scenarios() -> list[Scenario]:
    # Each scenario deliberately stresses a conceptual difference rather
    # than fitting a historical security. Values are synthetic by design.
    return [
        Scenario(
            "clear advance",
            [101, 103, 105, 107, 109, 111, 113, 115],
            [100] * 8,
            [0.8] * 7 + [0.9],
            "Stage 2",
        ),
        Scenario(
            "clear decline",
            [99, 97, 95, 93, 91, 89, 87, 85],
            [100] * 8,
            [-0.8] * 7 + [-0.9],
            "Stage 4",
        ),
        Scenario(
            "base weaving after decline",
            [96, 104, 97, 103, 98, 102, 99, 101],
            [100] * 8,
            [-0.8, -0.7, -0.6, -0.5, -0.4, -0.3, -0.1, 0.0],
            "Stage 1",
        ),
        Scenario(
            "top weaving after advance",
            [104, 96, 103, 97, 102, 98, 101, 99],
            [100] * 8,
            [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.1, 0.0],
            "Stage 3",
        ),
        Scenario(
            "price below flat MA without weaving",
            [96, 97, 98, 97, 96, 97, 98, 97],
            [100] * 8,
            [0.0] * 8,
            "Unclassified",
        ),
        Scenario(
            "price above flat MA without weaving",
            [104, 103, 102, 103, 104, 103, 102, 103],
            [100] * 8,
            [0.0] * 8,
            "Unclassified",
        ),
    ]


def run() -> pd.DataFrame:
    rows = []
    for case in scenarios():
        close = pd.Series(case.close, dtype=float)
        ma = pd.Series(case.ma, dtype=float)
        slope = pd.Series(case.slope_pct, dtype=float)
        v1 = locked_v1(float(close.iloc[-1]), float(ma.iloc[-1]), float(slope.iloc[-1]))
        research = research_stage(close, ma, slope)
        rows.append(
            {
                "scenario": case.name,
                "v1_locked": v1,
                "research_candidate": research,
                "expected_research": case.expected_research,
                "candidate_matches_expected": research == case.expected_research,
                "models_agree": v1 == research,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    result = run()
    print(result.to_string(index=False))
    print("\nAgreement rate:", f"{result['models_agree'].mean():.1%}")
    print("Candidate expected-case pass rate:", f"{result['candidate_matches_expected'].mean():.1%}")
