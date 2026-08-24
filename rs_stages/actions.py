"""Transparent RS/Stage interpretation layer based on the NSE Signal Interpretation Guide.

This module does not alter the quantitative engine. It maps already-calculated fields
into the guide's nine production-facing action labels.
"""
from __future__ import annotations

from typing import Any

import math

ACTIONS = ("BUY★", "BUY", "HOLD", "WAIT", "WATCH★", "WATCH", "REDUCE", "SELL", "AVOID")


def _num(value: Any) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else math.nan
    except (TypeError, ValueError):
        return math.nan


def _stage(value: Any) -> str:
    text = str(value or "")
    return text.split(" — ", 1)[0].strip()


def action_for(row: Any) -> str:
    """Return the guide action from existing quantitative outputs.

    Operational definitions added by the project adaptation:
    * ``Extended_20Pct`` is Close > 1.20 * 30W MA.
    * ``Below_50DMA`` is supplied by the screener as the latest close below
      its 50-session simple moving average.
    * ``Distribution`` means U/D < 0.7, matching the guide's warning band.
    * ``Heavy_Distribution`` means U/D < 0.6.

    Pullback/volume-drying is not inferred when the snapshot does not expose a
    dedicated, validated field; the engine therefore falls through to HOLD/WAIT
    rather than fabricating a condition.
    """
    stage = _stage(row.get("Stage"))
    rs = _num(row.get("RS_Score"))
    ud = _num(row.get("U_D"))
    breakout = bool(row.get("Breakout", False))
    confirmed = bool(row.get("Breakout_Confirmed", False))
    extended = bool(row.get("Extended_20Pct", False))
    below_50dma = bool(row.get("Below_50DMA", False))

    if stage == "Stage 4":
        return "SELL"
    if stage == "Stage 3":
        return "SELL" if math.isfinite(rs) and rs < 50 else "REDUCE"
    if stage == "Stage 1":
        if math.isfinite(rs) and rs >= 80:
            return "WATCH★"
        if math.isfinite(rs) and rs >= 50:
            return "WATCH"
        return "AVOID"
    if stage != "Stage 2":
        return "WAIT"

    distribution = math.isfinite(ud) and ud < 0.7
    if distribution:
        return "REDUCE"
    if not math.isfinite(rs) or rs < 50:
        return "WAIT"
    if rs < 80:
        return "WAIT" if breakout else "HOLD"
    if extended or below_50dma:
        return "WAIT"
    if confirmed:
        return "BUY★"
    if breakout:
        return "BUY"
    return "HOLD"


def action_reason(row: Any, action: str) -> str:
    stage = _stage(row.get("Stage"))
    rs = _num(row.get("RS_Score"))
    ud = _num(row.get("U_D"))
    rs_text = "RS unavailable" if not math.isfinite(rs) else f"RS {rs:.0f}"
    ud_text = "U/D unavailable" if not math.isfinite(ud) else f"U/D {ud:.2f}"

    reasons = {
        "BUY★": f"{stage} + {rs_text}; breakout is confirmed and no guide timing warning is active.",
        "BUY": f"{stage} + {rs_text}; breakout setup is present but confirmation is incomplete.",
        "HOLD": f"{stage} + {rs_text}; trend/leadership is adequate without a stronger entry trigger.",
        "WAIT": f"{stage} + {rs_text}; wait for the missing guide condition or improved timing.",
        "WATCH★": f"{stage} + {rs_text}; high leadership, but the guide requires Stage 2 before buying.",
        "WATCH": f"{stage} + {rs_text}; basing structure is not yet an entry condition.",
        "REDUCE": f"{stage}; distribution/topping evidence ({ud_text}) weakens the position case.",
        "SELL": f"{stage}; the guide treats this trend regime as an exit/avoid condition.",
        "AVOID": f"{stage} + {rs_text}; weak leadership and basing structure do not qualify for ownership.",
    }
    return reasons.get(action, f"{stage} / {rs_text}; no action rule matched.")


def with_actions(frame):
    out = frame.copy()
    out["Action"] = out.apply(action_for, axis=1)
    out["Action_Reason"] = out.apply(lambda r: action_reason(r, r["Action"]), axis=1)
    return out
