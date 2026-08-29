"""HTML component builders for the RS-Stages terminal.

Each function returns a self-contained HTML fragment. The component geometry —
the avatar-tile row, the rank-bar cell, the 52-week range track, the stacked
posture bar, the shelf list and the stat card — is adopted from the WealthStar
reference terminal, which is the design source for this project. The data poured
into them is entirely ours.

Every value that originates in data is escaped before it reaches the markup.
Components never invent a value: an unavailable number renders as an em dash.
"""
from __future__ import annotations

import html
import math
from urllib.parse import quote
from typing import Any, Iterable, Sequence

import pandas as pd

from .theme import (
    DASH,
    NEGATIVE,
    POSITIVE,
    action_style,
    fmt_pct,
    fmt_price,
    fmt_return,
    fmt_rs,
    initials,
    signed_color,
    stage_color,
    stage_display,
    stage_key,
    to_float,
)


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def query_href(**params: Any) -> str:
    """Build an in-app link from query parameters.

    Values are URL-encoded before being HTML-escaped. html.escape alone is not
    enough: it turns "&" into "&amp;" for the attribute but leaves it a
    parameter separator for the browser, so an industry named
    "Metals & Mining" would arrive truncated at the ampersand and match nothing.
    """
    query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items() if v is not None)
    return html.escape(f"?{query}", quote=True)


def query_href_multi(params: dict[str, Any], **repeated: list[Any]) -> str:
    """An in-app link where one parameter may appear more than once.

    Streamlit reads a repeated parameter as a list, which is how a multi-select
    filter is addressed. query_href takes one value per key and cannot express
    that, so a link to "every SELL and REDUCE" needed this.
    """
    parts = [f"{k}={quote(str(v), safe='')}" for k, v in params.items() if v is not None]
    for key, values in repeated.items():
        parts.extend(f"{key}={quote(str(v), safe='')}" for v in values)
    return html.escape("?" + "&".join(parts), quote=True)


def stock_href(symbol: Any) -> str:
    """Link into the Stock view for a symbol."""
    return query_href(view="Stock", symbol=symbol)


# --- small parts ------------------------------------------------------------


def dot(color: str, size: int = 8) -> str:
    return f'<span class="ws-dot" style="width:{size}px;height:{size}px;background:{color}"></span>'


def sparkline(values: Sequence[float], width: int = 84, height: int = 26) -> str:
    """Inline SVG trend line, coloured by net direction over the window.

    Returns an em dash when there is not enough history to draw a line, rather
    than drawing a flat line that would imply a price series we do not have.
    """
    points = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if len(points) < 2:
        return f'<span style="color:var(--faint)">{DASH}</span>'
    low, high = min(points), max(points)
    span = high - low
    step = width / (len(points) - 1)
    if span <= 0:
        coords = " ".join(f"{i * step:.1f},{height / 2:.1f}" for i in range(len(points)))
    else:
        coords = " ".join(
            f"{i * step:.1f},{(height - 2) - ((v - low) / span) * (height - 4):.1f}"
            for i, v in enumerate(points)
        )
    color = POSITIVE if points[-1] >= points[0] else NEGATIVE
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none" aria-hidden="true">'
        f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def range_track(low: Any, close: Any, high: Any, width: int | None = 96, caps: bool = True) -> str:
    """52-week range with the close positioned inside it.

    ``width=None`` lets the track fill its container, for the wider stock-page
    variant. Returns an em dash when the range cannot be bounded, rather than
    drawing a dot at an arbitrary position.
    """
    low_v, close_v, high_v = to_float(low), to_float(close), to_float(high)
    if not all(math.isfinite(v) for v in (low_v, close_v, high_v)) or high_v <= low_v:
        return f'<span style="color:var(--faint)">{DASH}</span>'
    position = min(100.0, max(0.0, (close_v - low_v) / (high_v - low_v) * 100.0))
    sizing = f"width:{width}px" if width else "flex:1"
    cap_left = '<span class="ws-range-cap">L</span>' if caps else ""
    cap_right = '<span class="ws-range-cap">H</span>' if caps else ""
    return (
        f'<span class="ws-range" style="{sizing}">{cap_left}'
        f'<span class="ws-range-track">'
        f'<span class="ws-range-dot" style="left:{position:.2f}%"></span></span>'
        f"{cap_right}</span>"
    )


def rs_cell(rs: Any) -> str:
    """RS number over a proportional rank bar."""
    value = to_float(rs)
    if not math.isfinite(value):
        return f'<span style="color:var(--faint)">{DASH}</span>'
    color = stage_color("Stage 2") if value >= 80 else ("#2465DE" if value >= 50 else "#68717F")
    return (
        f'<span class="ws-rs num">{fmt_rs(value)}</span>'
        f'<span class="ws-rs-bar bar-grow" style="width:{min(100.0, value):.0f}%;background:{color}"></span>'
    )


def action_chip(action: Any) -> str:
    color, background = action_style(action)
    label = esc(action) if action is not None and str(action) != "nan" else DASH
    return f'<span class="ws-chip" style="background:{background};color:{color}">{label}</span>'


def stage_cell(stage: Any) -> str:
    """Stage in a table row: marked dot, number, and the name it stands for.

    The name is wrapped so the mobile stylesheet can drop it and keep the row
    within 390px. The dot then carries the reading on its own, so it is not
    left to colour alone: each Stage gets a glyph that says which direction it
    describes. Roughly one man in twelve cannot separate the Stage 2 green from
    the Stage 4 red, and those are the two that decide whether to hold.
    """
    key = stage_key(stage)
    if key not in {"Stage 1", "Stage 2", "Stage 3", "Stage 4"}:
        return f'<span style="color:var(--faint)">{DASH}</span>'
    name = stage_display(stage).split(" · ")[1]
    return (
        f'<span class="ws-stage">{stage_mark(stage)}{esc(key)}'
        f'<span class="stage-name">· {esc(name)}</span></span>'
    )


#: A glyph per Stage, so the four are distinguishable without colour vision.
#: Chosen to describe the Stage's own direction, not to rank it: advancing
#: rises, declining falls, basing is flat, topping turns over.
STAGE_MARKS = {"Stage 1": "=", "Stage 2": "▲", "Stage 3": "◆", "Stage 4": "▼"}


def stage_mark(stage: Any, size: int = 15) -> str:
    """The Stage dot, carrying its glyph."""
    key = stage_key(stage)
    color = stage_color(stage)
    glyph = STAGE_MARKS.get(key)
    if glyph is None:
        return dot(color)
    return (
        f'<span class="ws-stage-mark" aria-hidden="true" '
        f'style="width:{size}px;height:{size}px;background:{color}1F;color:{color}">'
        f"{glyph}</span>"
    )


def symbol_cell(symbol: Any, subtitle: Any, stage: Any) -> str:
    """Avatar tile plus symbol and industry, linking into the Stock view."""
    color = stage_color(stage)
    return (
        f'<a class="ws-sym-cell" target="_self" href="{stock_href(symbol)}">'
        f'<span class="ws-tile" style="background:{color}14;color:{color}">{esc(initials(symbol))}</span>'
        f'<span style="display:flex;flex-direction:column;min-width:0">'
        f'<span class="ws-sym">{esc(symbol)}</span>'
        f'<span class="ws-sym-sub col-hide-sm">{esc(subtitle) if subtitle and str(subtitle) != "nan" else ""}</span>'
        f"</span></a>"
    )


def pill_link(symbol: Any, meta: Any = None) -> str:
    meta_html = f'<span class="meta num">{esc(meta)}</span>' if meta not in (None, "") else ""
    return (
        f'<a class="ws-pill-link pop" target="_self" href="{stock_href(symbol)}">'
        f'<span class="sym">{esc(symbol)}</span>{meta_html}</a>'
    )


def pill_row(items: Iterable[tuple[Any, Any]], empty: str = "Nothing in this group today.") -> str:
    pills = "".join(pill_link(symbol, meta) for symbol, meta in items)
    if not pills:
        return f'<div class="ws-note">{esc(empty)}</div>'
    return f'<div class="ws-chips">{pills}</div>'


# --- cards and shelves ------------------------------------------------------


def card(inner: str, extra_class: str = "", style: str = "") -> str:
    classes = f"ws-card {extra_class}".strip()
    style_attr = f' style="{style}"' if style else ""
    return f'<div class="{classes}"{style_attr}>{inner}</div>'


def stat_card(label: str, value: str, suffix: str = "", note: str = "", color: str = "var(--ink)") -> str:
    suffix_html = f"<small>{esc(suffix)}</small>" if suffix else ""
    note_html = f'<div class="ws-stat-note num">{esc(note)}</div>' if note else ""
    return (
        f'<div class="ws-stat lift"><div class="ws-stat-label">{esc(label)}</div>'
        f'<div class="ws-stat-value num" style="color:{color}">{esc(value)}{suffix_html}</div>'
        f"{note_html}</div>"
    )


def stat_row(cards: Iterable[str]) -> str:
    return f'<div class="ws-stat-row">{"".join(cards)}</div>'


def posture_bar(stage_counts: dict[str, int], title: str = "Stage posture") -> str:
    """Legend plus a stacked bar of the four locked Stages.

    Widths are shares of the classified universe; stocks whose Stage could not
    be classified are excluded from the bar and from its denominator.
    """
    order = ["Stage 2", "Stage 3", "Stage 4", "Stage 1"]
    total = sum(int(stage_counts.get(key, 0)) for key in order)
    legend = "".join(
        f'<span class="item">{dot(stage_color(key))}{esc(stage_display(key).split(" · ")[1])}'
        f'<b class="num">{int(stage_counts.get(key, 0)):,}</b></span>'
        for key in order
    )
    if total <= 0:
        segments = '<div style="width:100%;background:var(--track)"></div>'
    else:
        segments = "".join(
            f'<div class="bar-grow" style="width:{int(stage_counts.get(key, 0)) / total * 100:.4f}%;'
            f'background:{stage_color(key)}"></div>'
            for key in order
        )
    return (
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:8px;margin-bottom:2px">'
        f'<span style="font-size:12.5px;font-weight:600;color:var(--sub)">{esc(title)}</span>'
        f'<span class="ws-legend">{legend}</span></div>'
        f'<div class="ws-segbar">{segments}</div>'
    )


def shelf(
    label: str,
    count: int,
    color: str,
    items: Iterable[tuple[Any, Any]],
    limit: int = 12,
    more_href: str = "",
) -> str:
    """One 'what changed' row: label, count badge, and member pills.

    When the group is larger than the row can hold, the overflow is stated
    rather than silently dropped, with a link to where the rest lives.
    """
    all_items = list(items)
    members = all_items[:limit]
    pills = "".join(pill_link(symbol, meta) for symbol, meta in members)
    hidden = len(all_items) - len(members)
    if hidden > 0:
        target = f' href="{more_href}"' if more_href else ""
        tag = "a" if more_href else "span"
        pills += (
            f'<{tag} class="ws-pill-link pop" target="_self"{target} '
            f'style="color:var(--sub)"><span class="sym">+{hidden} more</span></{tag}>'
        )
    return (
        f'<div class="ws-shelf">'
        f'<span class="ws-shelf-label" style="color:{color}">{esc(label)}</span>'
        f'<span class="ws-shelf-count num" style="color:{color};background:{color}18">{int(count)}</span>'
        f'<div class="ws-chips" style="flex:1 1 200px;min-width:0">{pills}</div></div>'
    )


def checklist(items: Sequence[tuple[str, bool]]) -> str:
    """Evidence checklist with a pass/fail mark per condition."""
    rows = []
    for label, passed in items:
        color, background = (POSITIVE, "var(--up-bg)") if passed else (NEGATIVE, "var(--down-bg)")
        mark = "✓" if passed else "✕"
        rows.append(
            f'<div class="ws-check">'
            f'<span class="ws-check-mark" style="background:{background};color:{color}">{mark}</span>'
            f'<span>{esc(label)}</span></div>'
        )
    return "".join(rows)


def kv_grid(items: Sequence[tuple[str, str, str, str]]) -> str:
    """Grid of label / value / note tiles. Items are (label, value, note, colour)."""
    tiles = "".join(
        f'<div><div class="ws-kv-label">{esc(label)}</div>'
        f'<div class="ws-kv-value num" style="color:{color}">{esc(value)}</div>'
        f'<div class="ws-kv-note">{esc(note)}</div></div>'
        for label, value, note, color in items
    )
    return f'<div class="ws-kv">{tiles}</div>'


#: Tone for a boolean condition. "good" means True is favourable evidence,
#: "warn" means True is a caution, "neutral" means True carries no valence.
STATE_TONES = {
    "good": (POSITIVE, "var(--up-bg)"),
    "warn": ("#966316", "var(--amber-bg)"),
    "bad": (NEGATIVE, "var(--down-bg)"),
    "neutral": ("var(--sub)", "var(--track)"),
}


def state_pill(value: Any, tone: str = "good", yes: str = "Yes", no: str = "No") -> str:
    """Render a boolean condition as a pill coloured by what it means.

    A flat "Yes" loses the distinction between confirmation and a warning: a
    confirmed breakout and a distribution warning are not the same kind of Yes.
    Only the meaningful state is coloured; its absence stays neutral.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return f'<span class="ws-state" style="background:var(--track);color:var(--faint)">{DASH}</span>'
    active = bool(value)
    color, background = STATE_TONES[tone if active else "neutral"]
    return f'<span class="ws-state" style="background:{background};color:{color}">{esc(yes if active else no)}</span>'


def evidence_card(title: str, rows: Sequence[tuple[str, str, str]]) -> str:
    """A titled block of label / value rows, each with its definition beneath.

    Replaces a flat field-value dump: the reader can see which measure a number
    belongs to, and what it means, without consulting the methodology page.
    """
    body = "".join(
        f'<div class="ws-ev"><div class="ws-ev-label">{esc(label)}'
        f'<div class="ws-ev-note">{esc(note)}</div></div>'
        f'<div class="ws-ev-value num">{value}</div></div>'
        for label, value, note in rows
    )
    return card(f'<div class="ws-card-title">{esc(title)}</div>{body}')


def evidence_grid(cards: Iterable[str]) -> str:
    return f'<div class="ws-ev-grid">{"".join(cards)}</div>'


#: Status marks for the threshold table, in the guide's own vocabulary.
STATUS_MARKS = {
    "met": ("✓", POSITIVE, "var(--up-bg)"),
    "unmet": ("✕", NEGATIVE, "var(--down-bg)"),
    "caution": ("■", "#966316", "var(--amber-bg)"),
    "neutral": ("·", "var(--sub)", "var(--track)"),
}


def signal_note(kind: str, text: str) -> str:
    """A WAIT / conflict / caution note. Absent notes render nothing at all."""
    if not text:
        return ""
    palette = {
        "wait": ("#966316", "var(--amber-bg)", "Waiting on"),
        "conflict": ("#2465DE", "var(--blue-bg)", "Conflict"),
        "caution": ("#AA4B29", "var(--slip-bg)", "Caution"),
        "source": ("var(--sub)", "var(--track)", "Source"),
    }
    color, background, title = palette[kind]
    return (
        f'<div class="ws-signote" style="background:{background};border-color:{color}33">'
        f'<span class="ws-signote-title" style="color:{color}">{title}</span>'
        f'<span class="ws-signote-body">{esc(text)}</span></div>'
    )


def threshold_table(rows: Sequence[Any]) -> str:
    """The guide's Signal / Value / Threshold / Status table, as boxes."""
    body = "".join(
        (
            lambda mark: (
                f'<div class="ws-thr">'
                f'<div class="ws-thr-signal">{esc(r.signal)}'
                f'<div class="ws-thr-note">{esc(r.note)}</div></div>'
                f'<div class="ws-thr-value num">{esc(r.value)}</div>'
                f'<div class="ws-thr-rule">{esc(r.threshold)}</div>'
                f'<div class="ws-thr-status"><span class="ws-state" '
                f'style="background:{mark[2]};color:{mark[1]}">{mark[0]}</span></div></div>'
            )
        )(STATUS_MARKS.get(r.status, STATUS_MARKS["neutral"]))
        for r in rows
    )
    head = (
        '<div class="ws-thr ws-thr-head"><div class="ws-thr-signal">Signal</div>'
        '<div class="ws-thr-value">Value</div><div class="ws-thr-rule">Threshold</div>'
        '<div class="ws-thr-status">Met</div></div>'
    )
    return card(head + body, style="padding:6px 16px 10px")


def missing_notice(title: str, detail: str) -> str:
    """Explicit unavailability. Never a zero, never a placeholder number."""
    return f'<div class="ws-missing"><b>{esc(title)}</b><br>{esc(detail)}</div>'


# --- the dense screener table ----------------------------------------------

#: Column key -> (header label, alignment, hide-on-mobile)
SCREENER_COLUMNS = {
    "symbol": ("Stock", "left", False),
    "trend": ("3M trend", "left", True),
    "rs": ("RS", "left", False),
    "stage": ("Stage", "left", False),
    "action": ("Action", "left", False),
    "ud": ("U/D", "right", True),
    "ext": ("Ext %", "right", True),
    "range": ("52W range", "left", True),
    "r3m": ("3M", "right", True),
    # --- v2.2 pre-breakout structure ---
    "evidence": ("Evidence", "left", False),
    "rsline": ("RS line", "left", False),
    "contraction": ("Contraction", "right", True),
    "dryup": ("Vol dry-up", "right", True),
    "pivot": ("To pivot", "right", False),
    "template": ("Template", "right", True),
    "readiness": ("Readiness", "right", False),
    "atr": ("ATR %", "right", True),
}

#: The Screener's default columns: the momentum evidence and the Action that
#: interprets it. Named explicitly rather than left to fall back on the whole
#: SCREENER_COLUMNS map — that fallback silently rendered all seventeen
#: columns, so the "momentum" default already carried every pre-breakout column
#: the toggle claims to swap in, and the table ran far past the page width.
#:
#: Action sits second, immediately after the symbol. It is the decision column,
#: and at mobile widths the columns after the third are off-screen until the
#: reader thinks to scroll a table sideways.
MOMENTUM_COLUMNS = (
    "symbol", "action", "rs", "stage", "trend", "ud", "ext", "range", "r3m",
)

#: The Screener's pre-breakout columns, for the toggle that swaps the evidence.
PREBREAKOUT_COLUMNS = (
    "symbol", "action", "rs", "stage", "evidence",
    "rsline", "contraction", "dryup", "pivot", "template",
)

#: The Setups view's columns. Deliberately omits Action: §11 assigns every
#: Stage 1 stock the same label, so showing it beside a readiness ranking would
#: imply the label were varying with the score. It is not.
#:
#: Readiness is undefined outside Stage 1, so on a Stage 2 list it is a column
#: of em dashes wide enough to push a real column off the screen. It is added
#: by :func:`setup_columns` only where it can carry a value.
SETUP_COLUMNS = (
    "symbol", "evidence", "template", "rs", "stage",
    "rsline", "contraction", "dryup", "pivot",
)


def setup_columns(frame: "pd.DataFrame") -> tuple[str, ...]:
    """Setup columns, plus readiness when the rows shown can actually have one."""
    if "Stage1_Readiness" not in frame.columns:
        return SETUP_COLUMNS
    if not pd.to_numeric(frame["Stage1_Readiness"], errors="coerce").notna().any():
        return SETUP_COLUMNS
    return SETUP_COLUMNS + ("readiness",)

#: The four published pre-breakout conditions, in the order the Setups view
#: lists them. Evidence is how many a stock satisfies at once.
SETUP_CONDITIONS = (
    ("Trend template", "Trend_Template_Pass"),
    ("RS leading price", "RS_Line_NH_Before_Price"),
    ("Contracting base", "VCP_Setup"),
    ("Stage 1 ready", "Stage1_Readiness"),
)


def _cell(key: str, row: pd.Series, trend: Sequence[float] | None) -> str:
    if key == "symbol":
        return symbol_cell(row.get("Symbol"), row.get("Industry"), row.get("Stage"))
    if key == "trend":
        return sparkline(trend) if trend is not None else f'<span style="color:var(--faint)">{DASH}</span>'
    if key == "rs":
        return rs_cell(row.get("RS_Score"))
    if key == "stage":
        return stage_cell(row.get("Stage"))
    if key == "action":
        return action_chip(row.get("Action"))
    if key == "ud":
        value = to_float(row.get("U_D"))
        if math.isnan(value):
            return f'<span style="color:var(--faint)">{DASH}</span>'
        text = "∞" if math.isinf(value) else f"{value:.2f}×"
        color = POSITIVE if value > 1.3 else (NEGATIVE if value < 0.7 else "var(--sub)")
        return f'<span class="num" style="color:{color};font-weight:600">{text}</span>'
    if key == "ext":
        value = to_float(row.get("Ext_Pct"))
        color = "#966316" if math.isfinite(value) and value > 20 else signed_color(value)
        return f'<span class="num" style="color:{color};font-weight:600">{fmt_pct(value)}</span>'
    if key == "range":
        return range_track(row.get("Low_52W"), row.get("Close"), row.get("High_52W"))
    if key == "r3m":
        value = row.get("R3M")
        return (
            f'<span class="num" style="color:{signed_color(to_float(value) )};font-weight:600">'
            f"{fmt_return(value)}</span>"
        )

    # --- v2.2 ---------------------------------------------------------------
    if key == "rsline":
        # The divergence is the point, not the ratio's magnitude: a raw
        # Close/Index number means nothing to a reader on its own.
        if bool(row.get("RS_Line_NH_Before_Price")):
            return (
                f'<span style="color:{POSITIVE};font-weight:700">Leading</span>'
                '<div class="ws-sub">new high before price</div>'
            )
        if bool(row.get("RS_Line_At_High")):
            return '<span style="color:var(--ink);font-weight:600">At high</span>'
        if math.isnan(to_float(row.get("RS_Line"))):
            return f'<span style="color:var(--faint)">{DASH}</span>'
        return '<span style="color:var(--sub)">—</span>'
    if key == "contraction":
        value = to_float(row.get("Contraction_Ratio"))
        if math.isnan(value):
            return f'<span style="color:var(--faint)">{DASH}</span>'
        color = POSITIVE if value <= 0.60 else ("var(--sub)" if value < 1.0 else NEGATIVE)
        return f'<span class="num" style="color:{color};font-weight:600">{value:.2f}×</span>'
    if key == "dryup":
        value = to_float(row.get("Volume_DryUp"))
        if math.isnan(value):
            return f'<span style="color:var(--faint)">{DASH}</span>'
        color = POSITIVE if value <= 0.80 else ("var(--sub)" if value < 1.2 else NEGATIVE)
        return f'<span class="num" style="color:{color};font-weight:600">{value:.2f}×</span>'
    if key == "pivot":
        value = to_float(row.get("Pct_To_Pivot"))
        if math.isnan(value):
            return f'<span style="color:var(--faint)">{DASH}</span>'
        if value <= 0:
            return f'<span class="num" style="color:{POSITIVE};font-weight:600">through</span>'
        color = POSITIVE if value <= 3.0 else "var(--sub)"
        return f'<span class="num" style="color:{color};font-weight:600">+{value:.1f}%</span>'
    if key == "template":
        value = to_float(row.get("Trend_Template_Score"))
        if math.isnan(value):
            return f'<span style="color:var(--faint)">{DASH}</span>'
        color = POSITIVE if value == 8 else ("var(--ink)" if value >= 6 else "var(--sub)")
        return f'<span class="num" style="color:{color};font-weight:600">{int(value)}/8</span>'
    if key == "evidence":
        value = to_float(row.get("Setup_Evidence"))
        if math.isnan(value):
            return f'<span style="color:var(--faint)">{DASH}</span>'
        filled = int(value)
        # Bars rather than the readiness dots: both are counts and they sit in
        # the same row, so they must not be mistaken for one another.
        bars = "".join(
            f'<span style="display:inline-block;width:4px;height:12px;margin-right:2px;'
            f'border-radius:1px;background:{POSITIVE if i < filled else "var(--line)"}"></span>'
            for i in range(len(SETUP_CONDITIONS))
        )
        color = POSITIVE if filled >= 2 else "var(--sub)"
        return (
            f'<span class="num" style="font-weight:600;color:{color}" '
            f'title="{filled} of {len(SETUP_CONDITIONS)} setup conditions met">'
            f'{bars} {filled}</span>'
        )
    if key == "readiness":
        value = to_float(row.get("Stage1_Readiness"))
        if math.isnan(value):
            # Unavailable outside Stage 1, which is not the same as zero.
            return f'<span style="color:var(--faint)">{DASH}</span>'
        filled = int(value)
        dots = "".join(
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            f'margin-right:3px;background:{POSITIVE if i < filled else "var(--line)"}"></span>'
            for i in range(5)
        )
        return f'<span class="num" style="font-weight:600">{dots} {filled}/5</span>'
    if key == "atr":
        value = to_float(row.get("ATR_Pct"))
        if math.isnan(value):
            return f'<span style="color:var(--faint)">{DASH}</span>'
        return f'<span class="num" style="color:var(--sub);font-weight:600">{value:.1f}%</span>'
    return DASH


def screener_table(
    frame: pd.DataFrame,
    trends: dict[str, Sequence[float]] | None = None,
    columns: Sequence[str] | None = None,
    sorted_by: str | None = None,
    ascending: bool = False,
    caption: str = "Stocks in the validated snapshot",
) -> str:
    """Render the dense stock table.

    ``trends`` maps symbol to a short close series for the sparkline column; a
    symbol without one shows an em dash rather than a fabricated line.

    ``ascending`` points the sort marker the way the sort actually runs. It was
    previously drawn as ▼ on every sorted column, so "RS (low to high)" was
    marked as descending.

    ``caption`` names the table for assistive technology and labels the scroll
    region. The region is focusable so a keyboard user can scroll a table that
    still overflows at their width.
    """
    keys = list(columns or MOMENTUM_COLUMNS)
    marker = " ▲" if ascending else " ▼"
    header = "".join(
        '<th scope="col" class="{cls}">{label}</th>'.format(
            cls=" ".join(
                filter(
                    None,
                    [
                        "right" if SCREENER_COLUMNS[k][1] == "right" else "",
                        "col-hide-sm" if SCREENER_COLUMNS[k][2] else "",
                        "active" if sorted_by == k else "",
                    ],
                )
            ),
            label=esc(SCREENER_COLUMNS[k][0]) + (marker if sorted_by == k else ""),
        )
        for k in keys
    )

    body_rows = []
    for position, (_, row) in enumerate(frame.iterrows()):
        trend = (trends or {}).get(str(row.get("Symbol")))
        cells = "".join(
            '<td class="{cls}">{html}</td>'.format(
                cls=" ".join(
                    filter(
                        None,
                        [
                            "right" if SCREENER_COLUMNS[k][1] == "right" else "",
                            "col-hide-sm" if SCREENER_COLUMNS[k][2] else "",
                        ],
                    )
                ),
                html=_cell(k, row, trend),
            )
            for k in keys
        )
        delay = min(position, 12) * 18
        body_rows.append(f'<tr class="rfade" style="animation-delay:{delay}ms">{cells}</tr>')

    if not body_rows:
        return missing_notice(
            "No stocks match these filters.",
            "Filters change presentation only — widen them to see more of the same validated snapshot.",
        )
    return (
        '<div class="ws-table-wrap"><div class="ws-scroll" tabindex="0" role="region" '
        f'aria-label="{esc(caption)}"><table class="ws-table">'
        f"<caption>{esc(caption)}</caption>"
        f"<thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody>"
        "</table></div></div>"
    )


def _plural(count: Any, noun: str) -> str:
    """'1 stock' / '12 stocks' — a count of one is not written as a plural."""
    value = to_float(count)
    if not math.isfinite(value):
        return f"{DASH} {noun}s"
    number = int(value)
    return f"{number:,} {noun}" if number == 1 else f"{number:,} {noun}s"


#: The industry map's diverging scale. Median RS is a percentile whose midpoint
#: carries the site's own meaning — 50 is the line between lagging and adequate —
#: so the reading is polarity, not magnitude: two hues meeting at a neutral,
#: never one hue getting darker and never a rainbow.
#:
#: The two poles are deliberately not mirror images in lightness. A saturated
#: red and a saturated green of equal luminance are the textbook red-green
#: confusion: measured against deuteranopic and protanopic vision, the site's
#: own POSITIVE and NEGATIVE separated by only ΔE 6.9 — inside the band where
#: colour alone cannot be relied on. A pale red against a mid green measures
#: ΔE 14.7, comfortably clear. Both poles are also light enough to carry ink
#: text at 4.5:1, so a tile's label never has to flip colour partway along the
#: ramp and land in the gap where neither ink nor paper reaches AA.
#:
#: The asymmetry is the accessibility fix and it is shown, not hidden: the
#: legend draws the actual ramp, so a reader can see the scale is not
#: symmetric, and every tile carries its own RS number, so the reading never
#: rests on colour alone.
RS_DIVERGING = {
    "low": (0xEF, 0xA9, 0xA3),
    "mid": (0xED, 0xEE, 0xF1),
    "high": (0x3E, 0x8E, 0x76),
    "centre": 50.0,
    "span": 30.0,
}

#: An industry whose median RS could not be computed. Neutral, not a pole.
RS_DIVERGING_UNAVAILABLE = "#E4E6EA"

#: One label colour for every tile on the ramp. See label_contrast().
_LABEL_INK = (0x14, 0x17, 0x1B)
LABEL_INK = "#14171B"


def _rs_diverging(rs: float) -> str:
    """Colour for a median RS on the diverging scale, clamped to +/- span."""
    scale = RS_DIVERGING
    offset = max(-1.0, min(1.0, (rs - scale["centre"]) / scale["span"]))
    pole = scale["high"] if offset >= 0 else scale["low"]
    weight = abs(offset)
    mid = scale["mid"]
    channels = [round(mid[i] + (pole[i] - mid[i]) * weight) for i in range(3)]
    return "#%02X%02X%02X" % tuple(channels)


def _relative_luminance(rgb: Sequence[int]) -> float:
    """WCAG 2.1 relative luminance for an 8-bit RGB triple."""
    channels = []
    for value in rgb:
        linear = value / 255
        channels.append(linear / 12.92 if linear <= 0.03928 else ((linear + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(a: Sequence[int], b: Sequence[int]) -> float:
    high, low = sorted((_relative_luminance(a), _relative_luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def label_contrast(hex_color: str) -> float:
    """Contrast of the tile label against that tile. Asserted on by the tests.

    Both poles of RS_DIVERGING are chosen light enough for one ink colour to
    clear 4.5:1 across the whole ramp. A ramp with a dark pole would need the
    label to flip to paper partway along, and every continuous ramp has a band
    near that crossover where neither ink nor paper reaches AA.
    """
    raw = hex_color.lstrip("#")
    tile = tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))
    return _contrast(_LABEL_INK, tile)


def _squarify(values: Sequence[float], x: float, y: float, width: float, height: float) -> list[tuple]:
    """Squarified treemap layout: rectangles in the order the values arrive.

    Values must be sorted descending. Returns (x, y, w, h) per value, in the
    same coordinate space as the container passed in. The algorithm is Bruls,
    Huizing and van Wijk's: fill the shorter side with a row, extending it while
    the worst aspect ratio in the row keeps improving.
    """
    rectangles: list[tuple] = []
    remaining = list(values)
    total = sum(remaining)
    if total <= 0 or width <= 0 or height <= 0:
        return [(x, y, 0.0, 0.0) for _ in remaining]
    # Work in area units so a row's thickness follows directly from its sum.
    scale = (width * height) / total
    areas = [value * scale for value in remaining]

    def worst(row: list[float], side: float) -> float:
        if not row or side <= 0:
            return float("inf")
        total_row = sum(row)
        if total_row <= 0:
            return float("inf")
        side_sq = side * side
        total_sq = total_row * total_row
        return max(side_sq * max(row) / total_sq, total_sq / (side_sq * min(row)))

    index = 0
    while index < len(areas):
        side = min(width, height)
        row: list[float] = []
        while index < len(areas):
            candidate = row + [areas[index]]
            if row and worst(candidate, side) > worst(row, side):
                break
            row = candidate
            index += 1
        thickness = sum(row) / side if side else 0.0
        offset = 0.0
        for area in row:
            length = area / thickness if thickness else 0.0
            if width >= height:
                rectangles.append((x, y + offset, thickness, length))
            else:
                rectangles.append((x + offset, y, length, thickness))
            offset += length
        if width >= height:
            x += thickness
            width -= thickness
        else:
            y += thickness
            height -= thickness
    return rectangles


def industry_map(frame: pd.DataFrame, min_stocks: int = 5, height: int = 400) -> str:
    """Industries as a map: area is constituent count, colour is median RS.

    A ranked list answers "which industry is first". It cannot answer "where is
    the weight", which is the question that made a one-stock industry sit ninth
    in a leadership table without anything on screen saying it was one stock.
    Area says so immediately.
    """
    if frame.empty or "Median_RS" not in frame.columns:
        return ""
    work = frame.copy()
    work["_size"] = pd.to_numeric(work.get("Stocks"), errors="coerce").fillna(0.0)
    work["_rs"] = pd.to_numeric(work["Median_RS"], errors="coerce")
    work = work[work["_size"] > 0].sort_values("_size", ascending=False)
    if work.empty:
        return ""

    boxes = _squarify(work["_size"].tolist(), 0.0, 0.0, 100.0, 100.0)
    tiles = []
    for (left, top, box_width, box_height), (_, row) in zip(boxes, work.iterrows()):
        rs = to_float(row.get("_rs"))
        color = _rs_diverging(rs) if math.isfinite(rs) else RS_DIVERGING_UNAVAILABLE
        stocks = int(to_float(row.get("_size")))
        name = str(row.get("Industry"))
        thin = stocks < min_stocks
        # Every tile carries its full label; the stylesheet drops the parts
        # that will not fit, using the tile's own rendered size as a container
        # query. How much a tile can hold is a question about pixels, and the
        # same percentage is a comfortable box at 1100px and a sliver at 390px,
        # so this is not a decision the server can make. A tile too small even
        # for a number keeps its colour and its tooltip, and the table beneath
        # names every industry in full.
        label = (
            f'<span class="ws-map-name">{esc(name)}</span>'
            f'<span class="ws-map-rs num">{fmt_rs(rs)}</span>'
            f'<span class="ws-map-n num">{stocks}</span>'
        )
        stage2 = to_float(row.get("Stage2"))
        stage2_text = (
            f" · {int(stage2)} in Stage 2" if math.isfinite(stage2) else ""
        )
        tooltip = (
            f"{name} — median RS {fmt_rs(rs)}{stage2_text} · "
            f"{_plural(stocks, 'stock')}"
            + (" · too few for a group median" if thin else "")
        )
        tiles.append(
            f'<a class="ws-map-tile" target="_self" '
            f'href="{query_href(view="Find", mode="Industries", industry=name)}" '
            f'title="{esc(tooltip)}" aria-label="{esc(tooltip)}" '
            f'style="left:{left:.4f}%;top:{top:.4f}%;width:{box_width:.4f}%;'
            f'height:{box_height:.4f}%;background:{color}'
            + (";opacity:.55" if thin else "")
            + f'">{label}</a>'
        )

    # The scale is continuous, so the legend is the scale itself with its
    # midpoint named — the reader has to know 50 is the meeting point, not a
    # colour they have to infer.
    low = _rs_diverging(RS_DIVERGING["centre"] - RS_DIVERGING["span"])
    high = _rs_diverging(RS_DIVERGING["centre"] + RS_DIVERGING["span"])
    mid = _rs_diverging(RS_DIVERGING["centre"])
    legend = (
        '<div class="ws-map-legend">'
        '<span class="ws-note">Area is constituent count · colour is median RS</span>'
        '<span class="ws-map-scale">'
        f'<span class="cap num">{RS_DIVERGING["centre"] - RS_DIVERGING["span"]:.0f}</span>'
        f'<span class="ramp" style="background:linear-gradient(90deg,{low},{mid},{high})"></span>'
        f'<span class="cap num">{RS_DIVERGING["centre"] + RS_DIVERGING["span"]:.0f}</span>'
        "</span></div>"
    )
    return card(
        '<div class="ws-card-title">Where the weight sits</div>'
        f'<div class="ws-map" style="height:{height}px" role="group" '
        'aria-label="Industries sized by constituent count and coloured by median relative strength">'
        f'{"".join(tiles)}</div>{legend}'
    )


def industry_table(frame: pd.DataFrame, min_stocks: int = 5) -> str:
    """Ranked industry rows: rank, name, median-RS bar, Stage 2 share, 3M.

    ``min_stocks`` marks the industries whose median rests on too few
    constituents to be read as a group reading. They stay in the table — they
    are real NSE groups — but the row says how thin the basis is instead of
    presenting a one-stock median as a peer of a 121-stock one.

    The Stage 2 count is shown because ``industry_leadership`` computes it and
    it is the column a reader actually acts on: how much of the industry is
    advancing, not only where its median sits.
    """
    if frame.empty:
        return missing_notice(
            "No industry data in this snapshot.",
            "Industry is the NSE constituent CSV's Industry field; it is not remapped.",
        )
    has_stage2 = "Stage2" in frame.columns
    head = (
        '<div class="ws-irow-head" role="row"><span class="ws-irank">#</span>'
        '<span class="ws-iname">Industry</span>'
        '<span class="ws-irs">Strength (median RS)</span>'
        + ('<span class="ws-inum col-hide-sm">Stage 2</span>' if has_stage2 else "")
        + '<span class="ws-inum col-hide-sm">Partic.</span>'
        '<span class="ws-inum">3M</span></div>'
    )
    rows = []
    for rank, (_, row) in enumerate(frame.iterrows(), start=1):
        rs = to_float(row.get("Median_RS"))
        width = min(100.0, max(0.0, rs)) if math.isfinite(rs) else 0.0
        color = POSITIVE if rs >= 80 else ("#2465DE" if rs >= 50 else "#68717F")
        participation = to_float(row.get("Participation_Pct"))
        stocks = to_float(row.get("Stocks"))
        thin = math.isfinite(stocks) and stocks < min_stocks
        basis = _plural(stocks, "stock")
        if thin:
            basis += " — too few for a group median"
        stage2_cell = ""
        if has_stage2:
            stage2 = to_float(row.get("Stage2"))
            stage2_text = f"{int(stage2):,}" if math.isfinite(stage2) else DASH
            stage2_cell = (
                '<span class="ws-inum num col-hide-sm" style="color:var(--sub)">'
                f"{stage2_text}</span>"
            )
        row_style = ' style="opacity:.62"' if thin else ""
        rows.append(
            f'<div class="ws-irow"{row_style}>'
            f'<span class="ws-irank num">{rank}</span>'
            f'<div class="ws-iname"><a target="_self" '
            f'href="{query_href(view="Industries", industry=row.get("Industry"))}">'
            f'{esc(row.get("Industry"))}</a>'
            f'<div class="sub num">{esc(basis)}</div></div>'
            f'<div class="ws-irs"><div class="ws-irs-track col-hide-sm">'
            f'<div class="ws-irs-fill bar-grow" style="width:{width:.1f}%;background:{color}"></div></div>'
            f'<span class="ws-irs-value num">{fmt_rs(rs)}</span></div>'
            f'{stage2_cell}'
            f'<span class="ws-inum num col-hide-sm" style="color:var(--sub)">'
            f'{fmt_pct(participation, digits=0, signed=False)}</span>'
            f'<span class="ws-inum num" style="color:{signed_color(to_float(row.get("Median_R3M")))};font-weight:600">'
            f'{fmt_return(row.get("Median_R3M"))}</span></div>'
        )
    return card(head + "".join(rows), extra_class="", style="padding:6px 16px 10px")


def transition_rows(frame: pd.DataFrame, kind: str = "flag") -> str:
    """Compact rows for a Movers group: symbol, change, RS, extension."""
    rows = []
    for _, row in frame.iterrows():
        if kind == "stage":
            middle = (
                f'<span>{esc(stage_display(row.get("Stage_From")))}</span>'
                f'<span style="color:var(--faint)">→</span>'
                f'<span style="color:{stage_color(row.get("Stage_To"))};font-weight:600">'
                f'{esc(stage_display(row.get("Stage_To")))}</span>'
            )
        elif kind == "action":
            middle = (
                f'<span>{esc(row.get("Action_From"))}</span>'
                f'<span style="color:var(--faint)">→</span>'
                f'<span style="color:{action_style(row.get("Action_To"))[0]};font-weight:700">'
                f'{esc(row.get("Action_To"))}</span>'
            )
        else:
            middle = f'<span>{esc(row.get("Industry"))}</span>'
        rows.append(
            f'<a class="ws-shelf" target="_self" href="{stock_href(row.get("Symbol"))}" '
            f'style="text-decoration:none;color:var(--ink)">'
            f'<span style="font-weight:700;font-size:14px;flex:0 0 auto;min-width:110px">'
            f'{esc(row.get("Symbol"))}</span>'
            f'<span style="font-size:12.5px;color:var(--sub);display:flex;align-items:center;'
            f'flex-wrap:wrap;gap:6px;flex:1 1 150px;min-width:0">{middle}</span>'
            f'<span class="num" style="font-size:13px;color:var(--sub);flex:0 0 auto">RS '
            f'<b style="color:var(--ink)">{fmt_rs(row.get("RS_Score"))}</b></span>'
            f'<span class="num" style="font-size:12.5px;color:var(--faint);flex:0 0 auto;'
            f'text-align:right">{fmt_pct(row.get("Ext_Pct"))} ext</span></a>'
        )
    return "".join(rows)


def price_chart_payload(frame: pd.DataFrame) -> list[dict]:
    """Serialize a trend frame for the charting library."""
    payload = []
    for stamp, row in frame.iterrows():
        entry = {"time": pd.Timestamp(stamp).strftime("%Y-%m-%d")}
        for key in ("Close", "MA_10W", "MA_30W"):
            value = to_float(row.get(key))
            if math.isfinite(value):
                entry[key] = value
        payload.append(entry)
    return payload
