"""v2.2 pre-breakout structure: RS line, trend template, contraction, pivot.

Each calculation is checked against a second implementation written in plain
Python rather than against the pandas expression that produced it, so an error
in the vectorised form cannot be confirmed by itself.

Two tests here exist to catch conflations rather than arithmetic mistakes:
a session-based average must not equal the calendar-week average it superficially
resembles, and the dry-up must move opposite to the volume ratio. Both would
otherwise pass every numeric check while quietly measuring the wrong thing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rs_stages import quant

END = pd.Timestamp("2026-08-24")


def _frame(periods: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=END, periods=periods)
    close = pd.Series(300.0 + rng.normal(0.2, 4.0, periods).cumsum(), index=idx).clip(lower=10.0)
    return pd.DataFrame(
        {
            "Close": close,
            "High": close * 1.015,
            "Low": close * 0.985,
            "Volume": pd.Series(rng.uniform(5e5, 4e6, periods), index=idx),
        }
    )


# --- session averages --------------------------------------------------------

@pytest.mark.parametrize("sessions", [50, 150, 200])
def test_sma_matches_an_independent_mean(sessions):
    data = _frame()
    values = list(data["Close"])
    expected = sum(values[-sessions:]) / sessions
    assert quant.sma(data["Close"], END, sessions) == pytest.approx(expected, rel=1e-12)


def test_the_150_session_average_is_not_the_30_calendar_week_average():
    """§5.1's guard: they resemble each other and are not the same quantity.

    Thirty calendar weeks spans about 150 *calendar* days of sessions, not 150
    sessions. Substituting one for the other would restate Minervini's criteria
    in Weinstein's units while still calling them Minervini's.
    """
    data = _frame()
    session_based = quant.sma(data["Close"], END, 150)
    calendar_based = quant.ma_30w(data["Close"], END)
    assert session_based != pytest.approx(calendar_based, rel=1e-6)
    # And the window sizes genuinely differ, which is why the values do.
    assert len(quant.calendar_window(data["Close"], END, 30)) != 150


def test_sma_rising_reads_the_direction_over_the_stated_window():
    idx = pd.bdate_range(end=END, periods=260)
    rising = pd.Series(np.linspace(100.0, 200.0, 260), index=idx)
    falling = pd.Series(np.linspace(200.0, 100.0, 260), index=idx)
    assert quant.sma_rising(rising, END, 200, quant.TREND_TEMPLATE_RISING_SESSIONS)
    assert not quant.sma_rising(falling, END, 200, quant.TREND_TEMPLATE_RISING_SESSIONS)


def test_a_session_average_skips_missing_closes_rather_than_short_counting():
    """§5.1 — N sessions means N closes that exist.

    Averaging whatever survives inside a fixed N-slot slice reports the mean of
    N-1 observations as an N-session average, and the shortfall is invisible.
    This is what failed audit run 22: a NaN close 180 sessions back sat inside
    the 200-session window and outside the 150-session one, so SMA_200
    disagreed with an independent recalculation while SMA_150 agreed.
    """
    idx = pd.bdate_range(end=END, periods=300)
    series = pd.Series(np.arange(100.0, 400.0), index=idx)
    series.iloc[-180] = np.nan

    valid = [v for v in series if not np.isnan(v)]
    assert quant.sma(series, END, 150) == pytest.approx(sum(valid[-150:]) / 150, rel=1e-12)
    assert quant.sma(series, END, 200) == pytest.approx(sum(valid[-200:]) / 200, rel=1e-12)

    # The gap is outside the 150 window, so only the 200 average moves.
    clean = series.dropna()
    assert quant.sma(series, END, 150) == pytest.approx(quant.sma(clean, END, 150))
    assert quant.sma(series, END, 200) == pytest.approx(quant.sma(clean, END, 200))


def test_short_history_refuses_rather_than_averaging_what_it_has():
    data = _frame(periods=40)
    with pytest.raises(ValueError):
        quant.sma(data["Close"], END, 200)


# --- trend template ----------------------------------------------------------

def _passing_template() -> dict:
    return dict(
        close=200.0, sma_50=190.0, sma_150=180.0, sma_200=170.0,
        sma_200_rising=True, low_52w=100.0, high_52w=210.0, rs=85.0,
    )


def test_trend_template_passes_when_every_criterion_holds():
    result = quant.trend_template(**_passing_template())
    assert result["Trend_Template_Score"] == 8
    assert result["Trend_Template_Pass"] is True


@pytest.mark.parametrize(
    "field,value,criterion",
    [
        ("sma_150", 250.0, "TT1_Above_150_200"),
        ("sma_200_rising", False, "TT3_200_Rising"),
        ("sma_50", 160.0, "TT4_50_Above_150_200"),
        ("low_52w", 190.0, "TT6_Above_52W_Low"),
        ("high_52w", 400.0, "TT7_Near_52W_High"),
        ("rs", 42.0, "TT8_RS"),
    ],
)
def test_each_criterion_fails_independently(field, value, criterion):
    """A score alone cannot separate one failure from six; the booleans must."""
    args = _passing_template() | {field: value}
    result = quant.trend_template(**args)
    assert result[criterion] is False
    assert result["Trend_Template_Pass"] is False
    assert result["Trend_Template_Score"] < 8


def test_the_transcribed_thresholds_are_the_documented_ones():
    """§5.1 records these as transcribed from a source and verifiable there."""
    assert quant.TREND_TEMPLATE_LOW_MULTIPLE == 1.30
    assert quant.TREND_TEMPLATE_HIGH_FRACTION == 0.75
    assert quant.TREND_TEMPLATE_MIN_RS == 70.0
    # Exactly at each boundary must pass, since the source states "at least".
    boundary = _passing_template() | {"close": 130.0, "low_52w": 100.0, "high_52w": 210.0}
    assert quant.trend_template(**boundary)["TT6_Above_52W_Low"] is True
    assert quant.trend_template(**(_passing_template() | {"rs": 70.0}))["TT8_RS"] is True


def test_a_missing_input_fails_only_its_own_criterion():
    result = quant.trend_template(**(_passing_template() | {"rs": float("nan")}))
    assert result["TT8_RS"] is False
    assert result["Trend_Template_Score"] == 7


# --- RS line -----------------------------------------------------------------

def test_rs_line_is_the_ratio_on_shared_sessions_only():
    idx = pd.bdate_range(end=END, periods=10)
    close = pd.Series(np.arange(100.0, 110.0), index=idx)
    benchmark = pd.Series(np.arange(50.0, 60.0), index=idx).drop(idx[3])
    line = quant.rs_line(close, benchmark)
    assert idx[3] not in line.index, "a session the benchmark lacks must be dropped"
    assert len(line) == 9
    for stamp in line.index:
        assert line[stamp] == pytest.approx(close[stamp] / benchmark[stamp])


def test_rs_line_never_fills_a_missing_benchmark_session():
    idx = pd.bdate_range(end=END, periods=6)
    close = pd.Series([10.0] * 6, index=idx)
    benchmark = pd.Series([5.0, np.nan, 5.0, 0.0, 5.0, 5.0], index=idx)
    line = quant.rs_line(close, benchmark)
    # NaN and zero benchmarks are dropped, not carried forward or divided by.
    assert len(line) == 4
    assert line.notna().all() and np.isfinite(line).all()


def test_rs_line_high_requires_real_overlap():
    idx = pd.bdate_range(end=END, periods=60)
    line = pd.Series(np.linspace(1.0, 2.0, 60), index=idx)
    with pytest.raises(ValueError):
        quant.rs_line_high_52w(line, END)


def test_the_divergence_needs_strength_high_and_price_not():
    high = 2.0
    # RS line at its high, price well off its own high -> the leading tell.
    assert quant.rs_line_nh_before_price(2.0, high, -12.0) is True
    # RS line at its high but price also at its high -> a breakout, not the tell.
    assert quant.rs_line_nh_before_price(2.0, high, -1.0) is False
    # Price off its high but strength is not leading -> nothing.
    assert quant.rs_line_nh_before_price(1.2, high, -12.0) is False


def test_the_high_tolerance_admits_a_near_miss_but_not_a_wide_one():
    assert quant.rs_line_at_high(2.0 * (1 - 0.004), 2.0) is True
    assert quant.rs_line_at_high(2.0 * (1 - 0.02), 2.0) is False


# --- volatility, contraction, dry-up ----------------------------------------

def test_atr_pct_matches_an_independently_computed_true_range():
    data = _frame()
    h, l, c = list(data["High"]), list(data["Low"]), list(data["Close"])
    ranges = [
        max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        for i in range(1, len(c))
    ]
    expected = sum(ranges[-quant.ATR_SESSIONS:]) / quant.ATR_SESSIONS / c[-1] * 100.0
    assert quant.atr_pct(data["High"], data["Low"], data["Close"], END) == pytest.approx(
        expected, rel=1e-10
    )


def test_range_blocks_are_five_ten_session_windows_oldest_first():
    data = _frame()
    blocks = quant.range_blocks(data["High"], data["Low"], data["Close"], END)
    assert len(blocks) == quant.VCP_BLOCKS
    h, l, c = list(data["High"]), list(data["Low"]), list(data["Close"])
    for i in range(quant.VCP_BLOCKS):
        lo = len(c) - quant.VCP_BASE_SESSIONS + i * 10
        expected = (max(h[lo : lo + 10]) - min(l[lo : lo + 10])) / (
            sum(c[lo : lo + 10]) / 10
        ) * 100.0
        assert blocks[i] == pytest.approx(expected, rel=1e-10)


def test_a_tightening_base_contracts_and_a_widening_one_does_not():
    """Built so the answer is known by construction, not by reading the output."""
    idx = pd.bdate_range(end=END, periods=50)
    widths = np.concatenate([np.full(10, w) for w in (20.0, 16.0, 12.0, 8.0, 4.0)])
    close = pd.Series(100.0, index=idx)
    tightening = quant.range_blocks(close + widths / 2, close - widths / 2, close, END)
    assert quant.vcp_contractions(tightening) == 4
    assert quant.contraction_ratio(tightening) == pytest.approx(4.0 / 20.0)
    assert quant.contraction_ratio(tightening) < 1.0

    widening = quant.range_blocks(close + widths[::-1] / 2, close - widths[::-1] / 2, close, END)
    assert quant.vcp_contractions(widening) == 0
    assert quant.contraction_ratio(widening) > 1.0


def test_volume_dryup_is_the_opposite_instrument_to_volume_ratio():
    """§10.5 — the ratio catches the spike, the dry-up catches the drought.

    One series, both measures. A final-session spike on a drying base must raise
    the ratio while leaving the dry-up low; reading either as the other would
    invert the meaning of the setup.
    """
    idx = pd.bdate_range(end=END, periods=80)
    volume = pd.Series([1_000_000.0] * 70 + [300_000.0] * 10, index=idx)
    dryup = quant.volume_dryup(volume, END)
    assert dryup == pytest.approx(0.3, rel=1e-9)

    spiked = volume.copy()
    spiked.iloc[-1] = 5_000_000.0
    assert quant.volume_ratio(spiked, END) > 1.5      # the spike is visible
    assert quant.volume_dryup(spiked, END) < 0.80     # the base is still dry


#: A structure that passes on every price measurement, so each test below
#: isolates exactly one gate.
GOOD = dict(ratio=0.5, dryup=0.7, contractions=3, stage="Stage 2 \u2014 Advancing", depth_pct=20.0)


def test_vcp_setup_requires_all_three_price_conditions():
    assert quant.vcp_setup(**GOOD) is True
    assert quant.vcp_setup(**(GOOD | {"ratio": 0.9})) is False    # range not tight enough
    assert quant.vcp_setup(**(GOOD | {"dryup": 0.95})) is False   # volume not drying
    assert quant.vcp_setup(**(GOOD | {"contractions": 1})) is False  # one step is not a pattern
    assert quant.vcp_setup(**(GOOD | {"ratio": float("nan")})) is False


def test_a_contracting_base_outside_stage_2_is_not_a_setup():
    """§10.5.1 — the structure looks identical; the context inverts its meaning.

    The source will not buy a base inside a downtrend, however well formed.
    Without this gate 42% of the live screen was stocks that were not in Stage 2,
    33 of them in confirmed decline, presented as bases about to resolve upward.
    """
    for stage in ("Stage 1 \u2014 Basing", "Stage 3 \u2014 Topping", "Stage 4 \u2014 Declining"):
        assert quant.vcp_setup(**(GOOD | {"stage": stage})) is False, stage
    assert quant.vcp_setup(**(GOOD | {"stage": None})) is False
    assert quant.vcp_setup(**(GOOD | {"stage": float("nan")})) is False
    # And the price measurements themselves stay stage-blind: only the composite
    # judgement is gated, so the underlying structure is still described.
    assert quant.contraction_ratio([20.0, 16.0, 12.0, 8.0, 4.0]) == pytest.approx(0.2)


def test_a_base_that_cut_too_deep_is_not_a_setup():
    """§10.5.1 — overhead supply above a deep correction caps the advance."""
    assert quant.vcp_setup(**(GOOD | {"depth_pct": 35.0})) is True    # at the bound
    assert quant.vcp_setup(**(GOOD | {"depth_pct": 35.1})) is False
    assert quant.vcp_setup(**(GOOD | {"depth_pct": 51.7})) is False   # worst seen live
    assert quant.vcp_setup(**(GOOD | {"depth_pct": float("nan")})) is False
    assert quant.VCP_REJECT_BASE_DEPTH_PCT == 60.0


def test_base_depth_is_peak_to_trough_not_distance_from_the_52_week_high():
    """They are different quantities and the source gates on the former."""
    idx = pd.bdate_range(end=END, periods=60)
    # Base peaks at 100 and troughs at 75 -> a 25% correction.
    high = pd.Series([100.0] * 30 + [80.0] * 30, index=idx)
    low = pd.Series([90.0] * 30 + [75.0] * 30, index=idx)
    assert quant.base_depth_pct(high, low, END) == pytest.approx(25.0)

    short = pd.bdate_range(end=END, periods=20)
    with pytest.raises(ValueError):
        quant.base_depth_pct(
            pd.Series(1.0, index=short), pd.Series(1.0, index=short), END
        )


# --- pivot and readiness -----------------------------------------------------

def test_pivot_is_the_base_high_and_the_distance_signs_correctly():
    data = _frame()
    pivot = quant.vcp_pivot(data["High"], END)
    assert pivot == pytest.approx(max(list(data["High"])[-quant.VCP_BASE_SESSIONS:]))
    assert quant.pct_to_pivot(pivot, pivot) == pytest.approx(0.0)
    assert quant.pct_to_pivot(pivot * 0.9, pivot) > 0     # still below the pivot
    assert quant.pct_to_pivot(pivot * 1.1, pivot) < 0     # already through it


def test_pivot_and_near_52w_high_are_different_references():
    """§10.6 — a stock can sit on its base pivot while far below its 52-week high."""
    idx = pd.bdate_range(end=END, periods=300)
    # A high early in the year, then a long lower base the stock is topping out.
    high = pd.Series([400.0] * 100 + [200.0] * 200, index=idx)
    pivot = quant.vcp_pivot(high, END)
    assert pivot == pytest.approx(200.0)
    assert quant.pct_to_pivot(200.0, pivot) == pytest.approx(0.0)   # at the pivot
    assert quant.near_52w_high(200.0, 400.0) is False               # nowhere near


def test_stage1_readiness_counts_only_what_is_satisfied():
    assert quant.stage1_readiness(0.2, 70.0, 0.5, 0.7, 110.0, 100.0) == 5
    assert quant.stage1_readiness(-5.0, 20.0, 2.0, 1.5, 90.0, 100.0) == 0
    assert quant.stage1_readiness(0.2, 70.0, 0.5, 0.7, 90.0, 100.0) == 4
    # Unavailable inputs fail their own check rather than raising.
    assert quant.stage1_readiness(
        float("nan"), 70.0, float("nan"), 0.7, 110.0, 100.0
    ) == 3


# --- v2.3 swing detection ----------------------------------------------------
#
# These build a base whose contractions are known by construction and check the
# detector recovers them. That is a real gate on the arithmetic and on swing
# identification, but it is NOT validation against the source's charts: the
# worked examples are US stocks from 1995-2009 whose price history this project
# has no access to. A detector can pass every test here and still disagree with
# how the source read an actual chart.

def _base_with_depths(depths, bars_per_leg=9, start=100.0, recovery=0.8, noise_pct=0.0):
    """A price path whose peak-to-trough contractions are exactly `depths`.

    Each decline is followed by a rally recovering most of it, which is what a
    real base does: the source's own example fell 19 to 13 and then rallied back
    to nearly 17. An earlier version of this helper rallied only 6% off each
    low, and that unrealism is why the whole suite passed while the detector
    failed against real price history — a fixture that never presents the hard
    case cannot fail on it.
    """
    points = [(start, True)]
    peak = start
    for depth in depths:
        trough = peak * (1 - depth / 100.0)
        points.append((trough, False))
        peak = trough + (peak - trough) * recovery
        points.append((peak, True))
    points = points[:-1]

    prices = []
    for (a, _), (b, _) in zip(points, points[1:]):
        prices += list(np.linspace(a, b, bars_per_leg, endpoint=False))
    prices.append(points[-1][0])
    idx = pd.bdate_range(end=END, periods=len(prices))
    path = pd.Series(prices, index=idx)
    if noise_pct:
        # Real declines are not monotonic; they oscillate on the way down. That
        # oscillation is what a fine threshold mistakes for structure.
        rng = np.random.default_rng(11)
        path = path * (1 + rng.normal(0, noise_pct / 100.0, len(path)))
    return path * 1.0005, path * 0.9995


@pytest.mark.parametrize(
    "label,depths",
    [
        ("VIVO 31/17/8/3", [31.0, 17.0, 8.0, 3.0]),
        ("KCP 32/14/7/3", [32.0, 14.0, 7.0, 3.0]),
        ("New Oriental 22/8/2", [22.0, 8.0, 2.0]),
        ("FSII 18/5", [18.0, 5.0]),
    ],
)
def test_the_zigzag_recovers_a_contraction_sequence_it_was_built_from(label, depths):
    high, low = _base_with_depths(depths)
    recovered = [d for _, d in quant.contraction_depths(quant.swing_points(high, low))]
    assert len(recovered) == len(depths), f"{label}: found {recovered}"
    for got, want in zip(recovered, depths):
        # The High/Low straddle in the fixture shifts each depth ~0.1pp.
        assert got == pytest.approx(want, abs=0.5), f"{label}: {recovered} vs {depths}"


def test_the_final_contraction_is_reported_before_it_reverses():
    """The rightmost contraction forms the pivot, so it cannot wait for a flip.

    A zigzag that only emits confirmed swings would hide the tightest
    contraction — the one the pattern exists to find — until after the breakout.
    """
    high, low = _base_with_depths([20.0, 10.0, 4.0])
    depths = quant.contraction_depths(quant.swing_points(high, low))
    assert len(depths) == 3
    assert depths[-1][1] == pytest.approx(4.0, abs=0.5)


def test_noise_below_the_threshold_creates_no_swings():
    """§10.5.1's threshold exists to separate a pullback from jitter."""
    idx = pd.bdate_range(end=END, periods=120)
    rng = np.random.default_rng(4)
    flat = pd.Series(100 + rng.normal(0, 0.25, 120), index=idx)   # ~0.25% jitter
    assert len(quant.swing_points(flat * 1.001, flat * 0.999)) <= 2


def test_the_threshold_sits_below_the_tightest_contraction_in_the_source():
    """A 2% final contraction must remain visible, or the pivot is lost."""
    assert quant.SWING_REVERSAL_PCT < 2.0
    high, low = _base_with_depths([18.0, 6.0, 2.0])
    depths = [d for _, d in quant.contraction_depths(quant.swing_points(high, low))]
    assert len(depths) == 3, f"a 2% contraction went missing: {depths}"


def test_swings_strictly_alternate():
    high, low = _base_with_depths([25.0, 12.0, 5.0])
    kinds = [k for _, _, k in quant.swing_points(high, low)]
    assert all(a != b for a, b in zip(kinds, kinds[1:])), kinds


# --- v2.3 cascading contractions --------------------------------------------

@pytest.mark.parametrize(
    "label,depths",
    [
        ("VIVO", [31.0, 17.0, 8.0, 3.0]),
        ("KCP", [32.0, 14.0, 7.0, 3.0]),
        ("New Oriental", [22.0, 8.0, 2.0]),
        ("NFLX", [27.0, 14.0, 7.0]),
        ("MELI", [32.0, 14.0, 6.0]),
    ],
)
def test_the_cascade_recovers_the_sources_depth_sequences(label, depths):
    high, low = _base_with_depths(depths)
    got = [d for _, _, d in quant.cascading_contractions(high, low, END)]
    assert len(got) == len(depths), f"{label}: {[round(g) for g in got]} vs {depths}"
    for a, b in zip(got, depths):
        assert a == pytest.approx(b, abs=0.6), f"{label}: {[round(g) for g in got]}"


def test_no_single_fixed_threshold_can_read_this_pattern():
    """Why the cascade exists, pinned so it cannot be quietly reverted.

    A base whose first contraction is 27% and whose last is 7% defeats any one
    threshold: coarse enough to hold the first leg together, it steps over the
    last; fine enough to see the last, it shatters the first. Measured against
    the source's own footprints, every fixed value failed in a different way.
    """
    clean_high, clean_low = _base_with_depths([27.0, 14.0, 7.0])

    # Coarse: holds the deepest leg together but steps over the tightest.
    coarse = quant.contraction_depths(quant.swing_points(clean_high, clean_low, 15.0))
    assert len(coarse) < 3, "a 15% threshold should miss the tightest contraction"

    # Fine: over-counts, because a noisy path offers counter-moves it mistakes
    # for structure. Note this fixture shows the effect only mildly — a modest
    # over-count, not the collapse seen on real data, where the same threshold
    # read 26 contractions off NFLX against the source's 3. Synthetic noise is
    # too well behaved to reproduce that, and cranking it until it did would be
    # fitting the fixture to a conclusion. The severe case is evidenced by
    # scripts/validate_vcp_footprints.py against real price history; what this
    # test pins is the direction of the failure and the tension between the two
    # thresholds, which is what makes a single constant unworkable.
    noisy_high, noisy_low = _base_with_depths([27.0, 14.0, 7.0], noise_pct=1.6)
    fine = quant.contraction_depths(quant.swing_points(noisy_high, noisy_low, 1.5))
    assert len(fine) > 3, f"fine threshold should over-count, got {len(fine)}"

    # The cascade reads all three at their stated depths, noise and all.
    cascade = [d for _, _, d in quant.cascading_contractions(noisy_high, noisy_low, END)]
    assert len(cascade) == 3, [round(c) for c in cascade]
    # Tolerance derived from the fixture, not chosen to pass: 1.6% noise applied
    # to both the peak and the trough can inflate a nominal depth by ~3pp.
    assert max(cascade) == pytest.approx(27.0, abs=3.5)


def test_the_cascade_ratio_must_stay_below_the_halving_it_tracks():
    """The source describes each contraction as roughly half the previous.

    A search threshold at or above half the previous depth steps over the very
    contraction it is looking for. The value is calibrated, not derived, so this
    pins the relationship rather than the number.
    """
    assert quant.CASCADE_RATIO < 0.5
    high, low = _base_with_depths([22.0, 8.0, 2.0])
    tight = quant.cascading_contractions(high, low, END, ratio=0.5)
    assert len(tight) < 3, "ratio 0.5 should lose the 2% contraction"
    ok = quant.cascading_contractions(high, low, END)
    assert len(ok) == 3


def test_the_footprint_reports_the_final_contraction_as_the_pivot():
    high, low = _base_with_depths([30.0, 12.0, 5.0])
    fp = quant.vcp_footprint(high, low, END)
    assert fp["Contractions"] == 3
    assert fp["Deepest_Pct"] == pytest.approx(30.0, abs=0.6)
    assert fp["Tightest_Pct"] == pytest.approx(5.0, abs=0.6)
    # The pivot opens the last contraction, so it sits below the base's own top.
    assert fp["VCP_Pivot"] < float(high.max())


def test_a_base_outside_three_to_sixty_five_weeks_is_not_a_vcp():
    high, low = _base_with_depths([30.0, 12.0, 5.0], bars_per_leg=1)
    assert not pd.notna(quant.vcp_footprint(high, low, END)["Base_Weeks"])


def test_a_deeper_contraction_restarts_the_sequence():
    """§10.5.1 — contractions shrink; a deeper one is a new base, not a step.

    Without this the cascade degenerated: its threshold ratchets down after each
    contraction and never recovers, so late in a noisy base it behaved exactly
    like the fine fixed threshold it replaced. It read 44 contractions off NFLX
    against the source's 3. Enforcing the structure the source describes fixed
    what three rounds of parameter tuning could not.
    """
    # Shrinking, then a deeper correction, then shrinking again: only the final
    # decreasing run belongs to the base that is forming now.
    high, low = _base_with_depths([20.0, 9.0, 30.0, 12.0, 5.0])
    got = [d for _, _, d in quant.cascading_contractions(high, low, END)]
    assert len(got) == 3, [round(g) for g in got]
    assert got[0] == pytest.approx(30.0, abs=1.5)


def test_noise_no_longer_degenerates_the_cascade():
    """The failure mode that made attempt three worse than attempt two."""
    high, low = _base_with_depths([27.0, 14.0, 7.0], noise_pct=1.6)
    got = quant.cascading_contractions(high, low, END)
    assert len(got) <= quant.VCP_MAX_CONTRACTIONS, len(got)


def test_more_contractions_than_the_source_allows_is_not_a_vcp():
    """Forty-four contractions is not a bad reading; it is an absence."""
    assert quant.VCP_MAX_CONTRACTIONS == 6
    # A path with no shrinking structure at all should not yield a footprint.
    idx = pd.bdate_range(end=END, periods=300)
    rng = np.random.default_rng(3)
    walk = pd.Series(100 * np.exp(rng.normal(0, 0.02, 300).cumsum()), index=idx)
    fp = quant.vcp_footprint(walk * 1.005, walk * 0.995, END)
    if pd.notna(fp["Base_Weeks"]):
        assert fp["Contractions"] <= quant.VCP_MAX_CONTRACTIONS


def test_vcp_footprint_honours_the_parameters_it_accepts():
    """It accepted a threshold and silently ignored it, which made a sweep lie.

    Eleven sweep rows came back identical because the parameter never reached
    the detector. A signature that accepts a knob it does not use produces
    confident, meaningless output.
    """
    high, low = _base_with_depths([30.0, 12.0, 5.0])
    loose = quant.vcp_footprint(high, low, END, ratio=0.25)
    tight = quant.vcp_footprint(high, low, END, ratio=0.9)
    assert loose["Contractions"] != tight["Contractions"], (
        "changing the cascade ratio must change the reading"
    )
