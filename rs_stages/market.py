"""Market-breadth aggregation over the validated snapshot.

Breadth is a count of locked per-stock fields. It introduces no new
methodology: every measure here is the sum of a boolean that the screener
already produced and that the audit already reconciled independently.

Breadth is descriptive of participation. It is not a forecast and it is not an
input to any stock-level signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

#: Regime bands over the share of the universe above its 30-week line.
#: These are presentation bands for a single already-locked count, not a signal.
REGIME_BANDS = (
    (60.0, "Broad", "Most of the universe is above its 30-week line."),
    (40.0, "Mixed", "Participation is split around the 30-week line."),
    (0.0, "Narrow", "Most of the universe is below its 30-week line."),
)


def _count(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns:
        return 0
    return int(frame[column].fillna(False).astype(bool).sum())


def _stage_labels(frame: pd.DataFrame) -> pd.Series:
    if "Stage" not in frame.columns:
        return pd.Series("", index=frame.index, dtype=str)
    return frame["Stage"].astype(str).str.split(" — ", n=1).str[0]


def above_ma_30w(frame: pd.DataFrame) -> pd.Series:
    """Boolean series for 'close is above the 30-week line'.

    When the snapshot carries the explicit field it is used directly. Otherwise
    the value is read from Stage, which is not an inference: the locked
    classification defines Stage 2 and Stage 3 as exactly ``Close > MA_30W`` and
    Stage 1 and Stage 4 as exactly ``Close <= MA_30W``. A stock whose Stage could
    not be classified is neither above nor below, and is excluded from the
    denominator by :func:`classified_count`.
    """
    if "Above_MA_30W" in frame.columns:
        return frame["Above_MA_30W"].fillna(False).astype(bool)
    return _stage_labels(frame).isin(["Stage 2", "Stage 3"])


def classified_count(frame: pd.DataFrame) -> int:
    """Stocks with a usable Stage — the honest denominator for participation."""
    return int(_stage_labels(frame).isin(["Stage 1", "Stage 2", "Stage 3", "Stage 4"]).sum())


def _share(count: int, total: int) -> float:
    return float(count) / float(total) * 100.0 if total else float("nan")


def regime_label(pct_above_30w: float) -> tuple[str, str]:
    """Return the (label, plain-language description) for a breadth percentage."""
    if not np.isfinite(pct_above_30w):
        return "Unavailable", "Breadth cannot be measured from this snapshot."
    for threshold, label, description in REGIME_BANDS:
        if pct_above_30w >= threshold:
            return label, description
    return "Unavailable", "Breadth cannot be measured from this snapshot."


def breadth_snapshot(frame: pd.DataFrame) -> dict:
    """Aggregate participation counts from one validated research snapshot.

    ``Above_MA_10W`` and the 52-week proximity counts are only meaningful when
    the corresponding per-stock fields exist; when a field is absent the count
    is reported as unavailable rather than as zero.
    """
    total = int(len(frame))
    stage = _stage_labels(frame)
    classified = classified_count(frame)
    above_30w = int(above_ma_30w(frame).sum())
    above_10w = _count(frame, "Above_MA_10W")
    has_10w = "Above_MA_10W" in frame.columns

    # Participation is measured against the stocks that could actually be
    # classified, so insufficient history dilutes neither numerator nor
    # denominator.
    pct_30w = _share(above_30w, classified)
    label, description = regime_label(pct_30w)

    out = {
        "symbols": total,
        "classified": classified,
        "above_ma_30w": above_30w,
        "above_ma_10w": above_10w,
        "pct_above_ma_30w": pct_30w,
        "pct_above_ma_10w": _share(above_10w, classified) if has_10w else float("nan"),
        "near_52w_high": _count(frame, "Near_52W_High"),
        "breakout": _count(frame, "Breakout"),
        "breakout_confirmed": _count(frame, "Breakout_Confirmed"),
        "distribution": _count(frame, "Distribution"),
        "regime": label,
        "regime_description": description,
        "stages": {
            f"Stage {n}": int((stage == f"Stage {n}").sum()) for n in (1, 2, 3, 4)
        },
        "has_ma_10w": has_10w,
        "above_ma_30w_source": "field" if "Above_MA_30W" in frame.columns else "stage",
    }
    if "RS_Score" in frame.columns:
        rs = pd.to_numeric(frame["RS_Score"], errors="coerce")
        out["valid_rs"] = int(rs.notna().sum())
        out["rs_leaders"] = int((rs >= 80).sum())
        out["rs_lagging"] = int((rs < 50).sum())
    return out


def breadth_history_from_trends(
    trends: dict[str, pd.DataFrame], sessions: int = 120
) -> pd.DataFrame:
    """Build a participation time series from per-symbol trend frames.

    For every session in the trailing window this counts how many symbols closed
    above their own 10-week and 30-week lines *as of that session*. Each symbol's
    moving averages were evaluated at that session with no forward information,
    so the series carries no look-ahead: it is a stack of point-in-time counts,
    not a single snapshot projected backwards.

    Sessions where a symbol has no valid moving average are excluded from both
    the numerator and that session's denominator, so the percentage always
    describes the symbols that could actually be measured.
    """
    if not trends:
        return pd.DataFrame(columns=["Date", "Symbols", "Above_MA_30W", "Above_MA_10W"])

    above_30w: list[pd.Series] = []
    above_10w: list[pd.Series] = []
    measured_30w: list[pd.Series] = []
    measured_10w: list[pd.Series] = []

    for frame in trends.values():
        tail = frame.tail(sessions)
        close = tail["Close"]
        for ma_column, hits, measured in (
            ("MA_30W", above_30w, measured_30w),
            ("MA_10W", above_10w, measured_10w),
        ):
            if ma_column not in tail.columns:
                continue
            ma = tail[ma_column]
            valid = close.notna() & ma.notna()
            measured.append(valid.astype(int))
            hits.append((valid & (close > ma)).astype(int))

    def _sum(parts: list[pd.Series]) -> pd.Series:
        if not parts:
            return pd.Series(dtype=int)
        return pd.concat(parts, axis=1).fillna(0).sum(axis=1).astype(int)

    history = pd.DataFrame(
        {
            "Symbols": _sum(measured_30w),
            "Above_MA_30W": _sum(above_30w),
            "Symbols_MA_10W": _sum(measured_10w),
            "Above_MA_10W": _sum(above_10w),
        }
    ).sort_index()
    history = history[history["Symbols"] > 0]
    history["Pct_Above_MA_30W"] = history["Above_MA_30W"] / history["Symbols"] * 100.0
    history["Pct_Above_MA_10W"] = np.where(
        history["Symbols_MA_10W"] > 0,
        history["Above_MA_10W"] / history["Symbols_MA_10W"].replace(0, np.nan) * 100.0,
        np.nan,
    )
    history.index.name = "Date"
    return history.reset_index()


def industry_leadership(frame: pd.DataFrame, industry_column: str = "Industry") -> pd.DataFrame:
    """Aggregate the snapshot by NSE industry.

    Median RS is used rather than mean so a single extreme constituent cannot
    define an industry's reading. Participation is the share of the industry's
    stocks above their own 30-week line — the same measure as market breadth,
    scoped to the industry.
    """
    if industry_column not in frame.columns or frame.empty:
        return pd.DataFrame()

    work = frame.copy()
    work[industry_column] = work[industry_column].fillna("Unclassified").astype(str)
    stage = work["Stage"].astype(str).str.split(" — ", n=1).str[0] if "Stage" in work else None

    grouped = work.groupby(industry_column, dropna=False)
    out = pd.DataFrame(
        {
            "Stocks": grouped["Symbol"].count() if "Symbol" in work.columns else grouped.size(),
            "Median_RS": grouped["RS_Score"].median(),
            "Median_R3M": grouped["R3M"].median() if "R3M" in work.columns else np.nan,
        }
    )
    if stage is not None:
        work["_stage"] = stage
        out["Stage2"] = work.groupby(industry_column)["_stage"].apply(lambda s: int((s == "Stage 2").sum()))
    participation = above_ma_30w(work)
    out["Participation"] = participation.groupby(work[industry_column]).sum().astype(int)
    for source, name in (("Breakout_Confirmed", "Confirmed"), ("Near_52W_High", "Near_High")):
        if source in work.columns:
            flags = work[source].fillna(False).astype(bool)
            out[name] = flags.groupby(work[industry_column]).sum().astype(int)
    classified_by_industry = (
        _stage_labels(work)
        .isin(["Stage 1", "Stage 2", "Stage 3", "Stage 4"])
        .groupby(work[industry_column])
        .sum()
    )
    out["Participation_Pct"] = np.where(
        classified_by_industry > 0, out["Participation"] / classified_by_industry * 100.0, np.nan
    )
    out = out.reset_index().rename(columns={industry_column: "Industry"})
    return out.sort_values(["Median_RS", "Stocks"], ascending=[False, False]).reset_index(drop=True)
