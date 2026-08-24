"""Day-over-day structural changes between two validated snapshots.

Every group here is a set difference between two already-reconciled snapshots.
Nothing is recomputed and no state is inferred: a stock appears in a group only
because a locked field held one value at the previous decision date and a
different value at the current one.

Both snapshots must come from the same pipeline version. Diffing a snapshot
against one produced before a field existed would report the field's *arrival*
as a market change, so :func:`transitions` refuses to compare a field that is
missing from either side.
"""
from __future__ import annotations

import pandas as pd

#: Boolean-field transitions, as (field, direction, group label, description).
#: ``direction`` is True for False→True and False for True→False.
FLAG_TRANSITIONS = (
    ("Breakout", True, "New breakout setup", "Stage 2, within 3% of the 52-week high, on volume > 1.5×."),
    ("Breakout_Confirmed", True, "Newly confirmed breakout", "Breakout setup that now also has U/D > 1.3."),
    ("Breakout_Confirmed", False, "Lost breakout confirmation", "Confirmation conditions no longer hold."),
    ("Above_MA_10W", True, "Reclaimed the 10-week line", "Close moved back above the 10-calendar-week average."),
    ("Above_MA_10W", False, "Lost the 10-week line", "Close moved below the 10-calendar-week average."),
    ("Near_52W_High", True, "Moved within 3% of the 52-week high", "Close is now inside the locked 3% proximity band."),
    ("Extended_20Pct", True, "Newly extended beyond 20%", "Close is now more than 20% above the 30-week line."),
    ("Distribution", True, "New distribution warning", "U/D fell below 0.7."),
    ("Distribution", False, "Distribution warning cleared", "U/D recovered to 0.7 or above."),
)


def _stage(series: pd.Series) -> pd.Series:
    return series.astype(str).str.split(" — ", n=1).str[0]


def _aligned(current: pd.DataFrame, previous: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restrict both snapshots to the symbols present in each."""
    cur = current.set_index("Symbol") if "Symbol" in current.columns else current.copy()
    prev = previous.set_index("Symbol") if "Symbol" in previous.columns else previous.copy()
    shared = cur.index.intersection(prev.index)
    return cur.loc[shared], prev.loc[shared]


def _rows(cur: pd.DataFrame, symbols: pd.Index) -> pd.DataFrame:
    columns = [
        c
        for c in ("RS_Score", "Stage", "Industry", "Company Name", "Ext_Pct", "Close", "Action")
        if c in cur.columns
    ]
    out = cur.loc[symbols, columns].copy()
    out.insert(0, "Symbol", out.index.astype(str))
    sort_key = "RS_Score" if "RS_Score" in out.columns else out.columns[-1]
    return out.sort_values(sort_key, ascending=False).reset_index(drop=True)


def stage_changes(current: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    """Return every symbol whose Stage label differs between the two snapshots."""
    cur, prev = _aligned(current, previous)
    if "Stage" not in cur.columns or "Stage" not in prev.columns:
        return pd.DataFrame()
    now, before = _stage(cur["Stage"]), _stage(prev["Stage"])
    changed = now.ne(before) & now.notna() & before.notna() & now.ne("nan") & before.ne("nan")
    if not changed.any():
        return pd.DataFrame()
    out = _rows(cur, cur.index[changed])
    out["Stage_From"] = before.loc[out["Symbol"]].to_numpy()
    out["Stage_To"] = now.loc[out["Symbol"]].to_numpy()
    return out


def transitions(current: pd.DataFrame, previous: pd.DataFrame) -> dict[str, dict]:
    """Group day-over-day changes into named, explainable buckets.

    Returns a mapping of group label to ``{"description", "rows"}``. Groups with
    no members are omitted so the presentation layer never renders an empty
    shelf. Fields absent from either snapshot are skipped entirely rather than
    treated as False, which would manufacture a transition.
    """
    cur, prev = _aligned(current, previous)
    groups: dict[str, dict] = {}
    if cur.empty:
        return groups

    stage_frame = stage_changes(current, previous)
    if not stage_frame.empty:
        for label, mask in (
            ("Entered Stage 2 — Advancing", stage_frame["Stage_To"].eq("Stage 2")),
            ("Left Stage 2 — Advancing", stage_frame["Stage_From"].eq("Stage 2")),
            ("Entered Stage 4 — Declining", stage_frame["Stage_To"].eq("Stage 4")),
        ):
            subset = stage_frame[mask]
            if not subset.empty:
                groups[label] = {
                    "description": "Stage is the locked 30-week structure; the label changed between the two decision dates.",
                    "rows": subset.reset_index(drop=True),
                }

    for field, to_true, label, description in FLAG_TRANSITIONS:
        if field not in cur.columns or field not in prev.columns:
            continue
        now = cur[field].fillna(False).astype(bool)
        before = prev[field].fillna(False).astype(bool)
        mask = (now & ~before) if to_true else (~now & before)
        if not mask.any():
            continue
        groups[label] = {"description": description, "rows": _rows(cur, cur.index[mask])}

    if "Action" in cur.columns and "Action" in prev.columns:
        changed = cur["Action"].astype(str).ne(prev["Action"].astype(str))
        if changed.any():
            rows = _rows(cur, cur.index[changed])
            rows["Action_From"] = prev.loc[rows["Symbol"], "Action"].astype(str).to_numpy()
            rows["Action_To"] = cur.loc[rows["Symbol"], "Action"].astype(str).to_numpy()
            groups["Action changed"] = {
                "description": "The guide interpretation label moved because its underlying evidence moved.",
                "rows": rows,
            }
    return groups


def rs_movers(current: pd.DataFrame, previous: pd.DataFrame, count: int = 15) -> pd.DataFrame:
    """Return the largest cross-sectional RS rank changes.

    RS is a percentile rank, so a change is a change in standing relative to the
    universe, not a return. A stock can rise in RS on a down day.
    """
    cur, prev = _aligned(current, previous)
    if "RS_Score" not in cur.columns or "RS_Score" not in prev.columns:
        return pd.DataFrame()
    now = pd.to_numeric(cur["RS_Score"], errors="coerce")
    before = pd.to_numeric(prev["RS_Score"], errors="coerce")
    delta = (now - before).dropna()
    if delta.empty:
        return pd.DataFrame()
    ordered = delta.reindex(delta.abs().sort_values(ascending=False).index).head(count)
    out = _rows(cur, ordered.index)
    out["RS_Change"] = ordered.loc[out["Symbol"]].to_numpy()
    out["RS_Previous"] = before.loc[out["Symbol"]].to_numpy()
    return out.sort_values("RS_Change", ascending=False).reset_index(drop=True)


def summary(current: pd.DataFrame, previous: pd.DataFrame) -> dict[str, int]:
    """Counts for the one-line 'what changed' sentence."""
    groups = transitions(current, previous)
    return {label: int(len(payload["rows"])) for label, payload in groups.items()}
