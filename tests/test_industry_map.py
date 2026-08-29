"""The industry map: layout that conserves area, and colour that is checkable.

The map encodes two measures at once — area for constituent count, colour for
median RS — so both encodings need to hold under test. A treemap that loses
area is silently lying about weight, and a diverging ramp whose label cannot be
read is a chart only some readers can use.
"""

import pandas as pd
import pytest

from rs_stages.ui.components import (
    RS_DIVERGING,
    RS_DIVERGING_UNAVAILABLE,
    _rs_diverging,
    _squarify,
    industry_map,
    label_contrast,
)

#: WCAG AA for normal-size text.
AA_NORMAL = 4.5


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Industry": ["Financial Services", "Capital Goods", "Healthcare", "Forest Materials"],
            "Stocks": [121, 113, 70, 1],
            "Median_RS": [54.0, 63.0, 67.0, 54.0],
            "Median_R3M": [0.05, 0.01, 0.07, 0.03],
            "Stage2": [65, 79, 56, 1],
            "Participation_Pct": [64.4, 73.4, 81.4, 100.0],
        }
    )


# --- layout -----------------------------------------------------------------


def test_squarify_conserves_area_in_proportion_to_the_values():
    values = [121.0, 113.0, 70.0, 24.0, 12.0, 1.0]
    boxes = _squarify(values, 0.0, 0.0, 100.0, 100.0)
    total = sum(values)
    for value, (_, _, width, height) in zip(values, boxes):
        assert width * height == pytest.approx(value / total * 10_000, rel=1e-6)


def test_squarify_fills_the_container_without_overlapping():
    values = [40.0, 30.0, 20.0, 10.0]
    boxes = _squarify(values, 0.0, 0.0, 100.0, 100.0)
    assert sum(w * h for _, _, w, h in boxes) == pytest.approx(10_000, rel=1e-6)
    for x, y, width, height in boxes:
        assert x >= -1e-9 and y >= -1e-9
        assert x + width <= 100.0 + 1e-6
        assert y + height <= 100.0 + 1e-6


def test_squarify_survives_degenerate_input():
    assert _squarify([], 0, 0, 100, 100) == []
    assert all(w == 0 and h == 0 for _, _, w, h in _squarify([0.0, 0.0], 0, 0, 100, 100))
    assert all(w == 0 and h == 0 for _, _, w, h in _squarify([5.0], 0, 0, 0, 100))


# --- colour -----------------------------------------------------------------


def test_the_ramp_diverges_around_the_documented_centre():
    centre = RS_DIVERGING["centre"]
    assert _rs_diverging(centre) == "#%02X%02X%02X" % RS_DIVERGING["mid"]
    assert _rs_diverging(centre - RS_DIVERGING["span"]) == "#%02X%02X%02X" % RS_DIVERGING["low"]
    assert _rs_diverging(centre + RS_DIVERGING["span"]) == "#%02X%02X%02X" % RS_DIVERGING["high"]


def test_the_ramp_clamps_rather_than_running_off_its_poles():
    assert _rs_diverging(0) == _rs_diverging(RS_DIVERGING["centre"] - RS_DIVERGING["span"])
    assert _rs_diverging(99) == _rs_diverging(RS_DIVERGING["centre"] + RS_DIVERGING["span"])


def test_every_tile_on_the_ramp_can_carry_its_label():
    """One ink colour must clear AA across the whole ramp.

    A ramp with one dark pole forces the label to flip to paper partway along,
    and every continuous ramp has a band around that crossover where neither
    ink nor paper reaches 4.5:1. The poles are chosen to avoid that band.
    """
    for score in range(0, 101):
        contrast = label_contrast(_rs_diverging(score))
        assert contrast >= AA_NORMAL, f"RS {score} labels at {contrast:.2f}:1"
    assert label_contrast(RS_DIVERGING_UNAVAILABLE) >= AA_NORMAL


# --- rendering --------------------------------------------------------------


def test_the_map_names_every_industry_it_draws():
    markup = industry_map(_frame())
    for name in _frame()["Industry"]:
        assert name in markup


def test_a_thin_industry_is_marked_rather_than_dropped():
    markup = industry_map(_frame(), min_stocks=5)
    assert "Forest Materials" in markup
    assert "too few for a group median" in markup


def test_every_tile_carries_its_reading_in_text_not_only_in_colour():
    """Colour is never the sole encoding: the RS number is on the tile."""
    markup = industry_map(_frame())
    for score in ("54", "63", "67"):
        assert score in markup


def test_the_map_degrades_to_nothing_rather_than_an_empty_box():
    assert industry_map(pd.DataFrame()) == ""
    assert industry_map(pd.DataFrame({"Industry": ["X"], "Stocks": [0], "Median_RS": [50.0]})) == ""
