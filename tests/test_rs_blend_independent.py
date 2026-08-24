import numpy as np

from rs_stages.quant import rs_blend


def test_rs_blend_matches_locked_weights_independently():
    vectors = [
        {3: 0.10, 6: 0.20, 9: 0.30, 12: 0.40},
        {3: -0.25, 6: 0.15, 9: 0.80, 12: -0.10},
        {3: 1.20, 6: -0.40, 9: 0.05, 12: 0.90},
    ]
    for returns in vectors:
        expected = (
            0.40 * returns[3]
            + 0.20 * returns[6]
            + 0.20 * returns[9]
            + 0.20 * returns[12]
        )
        assert np.isclose(rs_blend(returns), expected, rtol=0, atol=1e-12)
