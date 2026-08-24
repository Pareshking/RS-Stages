import numpy as np
import pandas as pd

from rs_stages.quant import rs_score


def independent_expected(blend: pd.Series) -> pd.Series:
    valid = blend.dropna()
    # Independent implementation of rank(method='min', pct=True), not rs_score().
    ordered = sorted(valid.items(), key=lambda item: item[1])
    n = len(ordered)
    out = pd.Series(np.nan, index=blend.index, dtype=float)
    i = 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][1] == ordered[i][1]:
            j += 1
        min_rank = i + 1
        score = np.rint((min_rank / n) * 98.0 + 1.0)
        for k in range(i, j):
            out.loc[ordered[k][0]] = score
        i = j
    return out


def test_rs_score_matches_independent_reference_with_ties_and_missing():
    blend = pd.Series(
        [0.10, 0.10, 0.20, 0.35, np.nan, -0.05],
        index=["A", "B", "C", "D", "MISSING", "E"],
    )
    got = rs_score(blend)
    expected = independent_expected(blend)
    pd.testing.assert_series_equal(got, expected)


def test_rs_score_missing_values_do_not_change_valid_ranks():
    with_missing = pd.Series([0.10, np.nan, 0.20, 0.30], index=list("ABCD"))
    without_missing = pd.Series([0.10, 0.20, 0.30], index=list("ACD"))
    got = rs_score(with_missing).drop("B")
    expected = rs_score(without_missing)
    pd.testing.assert_series_equal(got, expected)


def test_rs_score_is_integer_1_to_99_for_valid_values():
    blend = pd.Series(np.linspace(-1.0, 1.0, 101))
    got = rs_score(blend).dropna()
    assert np.all(np.equal(got, np.floor(got)))
    assert got.min() >= 1.0
    assert got.max() <= 99.0
