import pandas as pd

from research.stage_fidelity_experiment import research_stage, scenarios


def test_research_candidate_handles_clear_trends_and_weaving_cases():
    for case in scenarios():
        got = research_stage(
            pd.Series(case.close, dtype=float),
            pd.Series(case.ma, dtype=float),
            pd.Series(case.slope_pct, dtype=float),
        )
        assert got == case.expected_research, case.name
