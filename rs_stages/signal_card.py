"""The Signal Card — the guide's Option B evidence panel.

Section 4 of the NSE Signal Interpretation Guide specifies a card that puts the
interpretation label on top and keeps every component that produced it visible
underneath: a stage line, an RS line, a volume line, an extension line, the
source attribution, and — when they apply — a note for what a WAIT is waiting
for, a note where RS and Stage disagree, and a caution the label alone misses.

This module produces that content from already-computed locked fields. It adds
no quantitative definition: the bands below are presentation vocabulary for
numbers the screener already published, and no locked signal consumes them.

The guide's own framing: "The label is a filter. The evidence panel is the
decision."
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .actions import _stage


def _num(value: Any) -> float:
    """Float for display, preserving infinity.

    The action layer deliberately collapses a non-finite value to NaN, because
    an infinite ratio cannot be compared against a decision threshold there. For
    display the distinction matters: an infinite U/D means zero down-volume over
    the window, which the locked spec defines explicitly. Showing it as
    "unavailable" would hide a real, meaningful reading.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan

#: Locked thresholds the guide states, quoted so a card can show value against
#: threshold rather than a bare number.
RS_LEADERSHIP = 80.0
RS_ADEQUATE = 50.0
VOLUME_BREAKOUT = 1.5
UD_CONFIRM = 1.3
UD_DISTRIBUTION = 0.7
UD_HEAVY = 0.6
EXTENSION_IDEAL = 20.0

#: Presentation bands for how far price sits from the 30-week line. The guide
#: calls +12% "normal range", +53% and +66% "extended", and +89% "very
#: extended". "At the line" is added for crossings inside a couple of percent,
#: where the label reads as a decisive move but the distance is a hair.
#: These are display vocabulary only; the locked warning remains Close > 1.20 × MA.
EXTENSION_BANDS = (
    (75.0, "very extended", "bad"),
    (EXTENSION_IDEAL, "extended", "warn"),
    (2.0, "normal range", "good"),
    (-2.0, "at the line", "warn"),
    (float("-inf"), "below the line", "bad"),
)


@dataclass(frozen=True)
class SignalRow:
    """One line of the threshold table: value against the rule it must meet."""

    signal: str
    value: str
    threshold: str
    status: str  # "met" | "unmet" | "caution" | "neutral"
    note: str = ""


def rs_percentile_text(rs: Any) -> str:
    """Describe an RS score in the guide's language: 'RS 99 — top 1%'."""
    value = _num(rs)
    if not math.isfinite(value):
        return "RS unavailable"
    if value >= RS_LEADERSHIP:
        return f"RS {value:.0f} — top {max(1, int(round(100 - value)))}%"
    if value >= RS_ADEQUATE:
        return f"RS {value:.0f} — adequate, not leadership"
    return f"RS {value:.0f} — lagging"


def extension_band(ext_pct: Any) -> tuple[str, str]:
    """Return the (band name, tone) for extension above the 30-week line."""
    value = _num(ext_pct)
    if not math.isfinite(value):
        return "unavailable", "neutral"
    for floor, name, tone in EXTENSION_BANDS:
        if value >= floor:
            return name, tone
    return "unavailable", "neutral"


def volume_state(row: Any) -> str:
    """Describe accumulation using the locked U/D bands."""
    ud = _num(row.get("U_D"))
    if not math.isfinite(ud):
        return "U/D unavailable"
    if ud < UD_HEAVY:
        return "heavy distribution"
    if ud < UD_DISTRIBUTION:
        return "distribution warning"
    if ud <= UD_CONFIRM:
        return "neutral"
    if ud <= 1.5:
        return "accumulating"
    return "strong accumulation"


def wait_note(row: Any, action: Any) -> str:
    """State exactly what a WAIT or WATCH is waiting for.

    The guide requires the card to show the gap, not merely that one exists.
    """
    if str(action) not in {"WAIT", "WATCH", "WATCH★"}:
        return ""
    stage = _stage(row.get("Stage"))
    rs = _num(row.get("RS_Score"))
    reasons: list[str] = []

    if stage != "Stage 2":
        reasons.append(f"{stage} — the guide requires Stage 2 before buying")
    if math.isfinite(rs) and rs < RS_LEADERSHIP:
        shortfall = RS_LEADERSHIP - rs
        reasons.append(f"RS {rs:.0f} (needs {RS_LEADERSHIP:.0f}, short by {shortfall:.0f})")
    if bool(row.get("Extended_20Pct")):
        ext = _num(row.get("Ext_Pct"))
        detail = f" at {ext:+.0f}%" if math.isfinite(ext) else ""
        reasons.append(f"extended beyond 20% above the 30-week line{detail}")
    if bool(row.get("Below_50DMA")):
        reasons.append("below the 50-session average")
    return " · ".join(reasons)


def conflict_note(row: Any) -> str:
    """Flag the cases where the three signals disagree with each other.

    Section 6 of the guide: when RS and Stage conflict, resolve in favour of
    Stage. The card must say so rather than leaving the reader to notice.
    """
    stage = _stage(row.get("Stage"))
    rs = _num(row.get("RS_Score"))
    ud = _num(row.get("U_D"))

    if stage in {"Stage 3", "Stage 4"} and math.isfinite(rs) and rs >= RS_LEADERSHIP:
        return (
            f"RS {rs:.0f} in a {stage.lower()} trend. A high rank in a falling market means "
            "least bad, not good. Stage overrides RS absolutely."
        )
    if stage == "Stage 2" and math.isfinite(ud) and ud < UD_DISTRIBUTION:
        return (
            f"Price is above a rising 30-week line but U/D is {ud:.2f} — volume contradicts "
            "the price stage. Sellers dominate; Stage 3 may be forming."
        )
    if stage == "Stage 2" and math.isfinite(rs) and rs < RS_ADEQUATE:
        ext = _num(row.get("Ext_Pct"))
        hair = " by a hair" if math.isfinite(ext) and abs(ext) < 2.0 else ""
        return (
            f"The 30-week structure turned up{hair}, but RS {rs:.0f} means the stock still lags "
            "most of the universe. Stage describes its own trend; RS describes strength against "
            "everything else."
        )
    return ""


def caution_note(row: Any) -> str:
    """Risk the label alone misses — chiefly entry timing at high extension."""
    ext = _num(row.get("Ext_Pct"))
    if not math.isfinite(ext):
        return ""
    band, _ = extension_band(ext)
    if band == "very extended":
        return (
            f"Extension {ext:+.0f}% — very far above the 30-week line. The signal may be valid "
            "but the entry is poor. Wait for a pullback toward the line, or size very small."
        )
    if band == "extended":
        return (
            f"Extension {ext:+.0f}% — beyond the guide's 20% comfort band. Do not add here; "
            "risk back to the line is large."
        )
    if band == "at the line":
        return (
            f"Extension {ext:+.1f}% — price is sitting on the 30-week line. A crossing this "
            "narrow can reverse on a single session."
        )
    return ""


def source_line(row: Any) -> str:
    """Trace the reading back to the book it comes from."""
    stage = _stage(row.get("Stage"))
    parts: list[str] = []
    if stage == "Stage 2":
        parts.append("Weinstein: price above a rising 30-week line is Stage 2")
    elif stage == "Stage 4":
        parts.append("Weinstein: never hold Stage 4")
    elif stage == "Stage 3":
        parts.append("Weinstein: Stage 3 is topping — reduce exposure")
    elif stage == "Stage 1":
        parts.append("Weinstein: Stage 1 is basing — wait for the breakout")

    rs = _num(row.get("RS_Score"))
    if math.isfinite(rs):
        parts.append(
            "O'Neil: leadership requires RS ≥ 80"
            if rs >= RS_LEADERSHIP
            else "O'Neil: buy leaders, not laggards"
        )
    if bool(row.get("Breakout_Confirmed")):
        parts.append("Weinstein: breakout confirmed by volume")

    # v2.2 sources. Guarded on the evidence actually being present, so a
    # snapshot published before v2.2 simply cites the two earlier authors
    # rather than claiming a reading it does not carry.
    if bool(row.get("RS_Line_NH_Before_Price")):
        parts.append(
            "O'Neil: the relative-strength line turning up before price is the leading tell"
        )
    if bool(row.get("VCP_Setup")):
        parts.append(
            "Minervini: a contracting range on drying volume is the base tightening before a move"
        )
    if bool(row.get("Trend_Template_Pass")):
        parts.append(
            "Minervini: all eight trend-template criteria met (thresholds provisional)"
        )
    return " · ".join(parts)


def signal_rows(row: Any) -> list[SignalRow]:
    """The threshold table: every signal, its value, its rule and whether it is met."""
    stage = _stage(row.get("Stage"))
    rs = _num(row.get("RS_Score"))
    vol = _num(row.get("Volume_Ratio"))
    ud = _num(row.get("U_D"))
    slope = _num(row.get("MA_30W_Slope_10S_Pct"))
    ext = _num(row.get("Ext_Pct"))

    def num(value: float, suffix: str = "", digits: int = 2) -> str:
        if math.isnan(value):
            return "—"
        if math.isinf(value):
            return "∞" if value > 0 else "−∞"
        return f"{value:,.{digits}f}{suffix}"

    rows = [
        SignalRow(
            "Stage",
            stage or "—",
            "Stage 2 required to buy",
            "met" if stage == "Stage 2" else "unmet",
            "Price above a rising 30-week line" if stage == "Stage 2" else "Not an entry condition",
        ),
        SignalRow(
            "Relative strength",
            num(rs, digits=0),
            f"≥ {RS_LEADERSHIP:.0f} for leadership",
            "met" if math.isfinite(rs) and rs >= RS_LEADERSHIP else "unmet",
            rs_percentile_text(rs),
        ),
        SignalRow(
            "Volume ratio",
            num(vol, "×"),
            f"≥ {VOLUME_BREAKOUT}× confirms a breakout",
            "met" if not math.isnan(vol) and vol > VOLUME_BREAKOUT else "unmet",
            "Latest session against the prior-50 baseline",
        ),
        SignalRow(
            "U/D ratio",
            num(ud),
            f"≥ {UD_CONFIRM} confirms accumulation",
            "met"
            if math.isfinite(ud) and ud > UD_CONFIRM
            else ("caution" if not math.isnan(ud) and ud < UD_DISTRIBUTION else "unmet"),
            volume_state(row).capitalize(),
        ),
        SignalRow(
            "Extension",
            num(ext, "%", 1) if math.isfinite(ext) else "—",
            f"< {EXTENSION_IDEAL:.0f}% is the comfort band",
            "met"
            if math.isfinite(ext) and abs(ext) < EXTENSION_IDEAL and abs(ext) >= 2.0
            else "caution",
            extension_band(ext)[0].capitalize(),
        ),
        SignalRow(
            "30-week slope",
            num(slope, "%", 2),
            "> 0% means the line is rising",
            "met" if math.isfinite(slope) and slope > 0 else "unmet",
            "Change over 10 completed sessions",
        ),
    ]
    if "Near_52W_High" in getattr(row, "index", {}) or isinstance(row, dict):
        rows.append(
            SignalRow(
                "Near the 52-week high",
                "Yes" if bool(row.get("Near_52W_High")) else "No",
                "within 3% for a breakout setup",
                "met" if bool(row.get("Near_52W_High")) else "unmet",
                "Close against the 52-week adjusted high",
            )
        )
    return rows
