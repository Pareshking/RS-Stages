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
    """Return the guide action from existing quantitative outputs."""
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


def _wait_gap(row: Any, stage: str, rs: float) -> str:
    """Name the condition a WAIT is actually waiting for.

    docs/ACTION_SPEC.md section 5 requires the exact reason for an Action.
    "Wait for the missing guide condition" names nothing, which leaves the
    reader unable to tell an extended leader from a lagging one. Each branch
    below states the specific rule that is unmet.
    """
    if stage == "Stage 2":
        if bool(row.get("Extended_20Pct")):
            ext = _num(row.get("Ext_Pct"))
            at = f" (currently {ext:+.0f}%)" if math.isfinite(ext) else ""
            return (
                "wait because price is more than 20% above the 30-week line"
                f"{at} — the guide treats that as poor entry timing, not a failed trend."
            )
        if bool(row.get("Below_50DMA")):
            return (
                "wait because the close is below its 50-session average — short-term timing "
                "has weakened even though the 30-week trend is intact."
            )
        if math.isfinite(rs) and rs < 50.0:
            return (
                "wait because relative strength is below 50 — the trend has turned up but the "
                "stock still lags most of the universe."
            )
        if math.isfinite(rs) and rs < 80.0:
            if bool(row.get("Breakout")):
                return (
                    f"wait because a breakout without leadership is not an entry: RS needs 80, "
                    f"short by {80.0 - rs:.0f}."
                )
            return f"wait because RS is below the 80 leadership band, short by {80.0 - rs:.0f}."
        return "wait for a clearer entry trigger; no breakout setup is present."
    return f"wait because the guide requires Stage 2 before buying, and this is {stage}."


def action_reason(row: Any, action: str) -> str:
    """Explain the exact decision precedence that produced an Action."""
    stage = _stage(row.get("Stage"))
    rs = _num(row.get("RS_Score"))
    ud = _num(row.get("U_D"))
    rs_text = "RS unavailable" if not math.isfinite(rs) else f"RS {rs:.0f}"
    ud_text = "U/D unavailable" if not math.isfinite(ud) else f"U/D {ud:.2f}"

    if action == "SELL":
        if stage == "Stage 4":
            return "Stage 4 takes precedence: the guide requires SELL regardless of RS."
        return f"{stage} + {rs_text}; RS below 50 in Stage 3 triggers SELL."
    if action == "REDUCE":
        if stage == "Stage 3":
            return f"Stage 3 with {rs_text}; the guide requires REDUCE when RS is 50 or higher."
        return f"{stage} + {rs_text}; distribution warning ({ud_text}) triggers REDUCE."
    if action == "WATCH★":
        return f"{stage} + {rs_text}; high leadership in a basing stage is WATCH★, not a buy."
    if action == "WATCH":
        return f"{stage} + {rs_text}; adequate RS in a basing stage remains WATCH."
    if action == "AVOID":
        return f"{stage} + {rs_text}; weak RS in a basing stage is AVOID."
    if action == "WAIT":
        return f"{stage} + {rs_text}; {_wait_gap(row, stage, rs)}"
    if action == "BUY★":
        return f"{stage} + {rs_text}; breakout is confirmed and no guide timing warning is active."
    if action == "BUY":
        return f"{stage} + {rs_text}; breakout setup is present but confirmation is incomplete."
    if action == "HOLD":
        return f"{stage} + {rs_text}; trend/leadership is adequate without a stronger entry trigger."
    return f"{stage} / {rs_text}; no action rule matched."


def with_actions(frame):
    out = frame.copy()
    out["Action"] = out.apply(action_for, axis=1)
    out["Action_Reason"] = out.apply(lambda r: action_reason(r, r["Action"]), axis=1)
    return out
