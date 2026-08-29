"""Regression coverage for Streamlit interaction/rerun failures.

A plain HTTP health check only proves that the initial script can boot. This test
explicitly changes the navigation widget and reruns the real production entrypoint,
which is the execution pattern that previously exposed the white-page crash.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

# AppTest resolves a relative path against the file that calls it, which would
# look for tests/app.py. The entrypoint under test is the repository's own.
ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app.py")

VIEWS = ["Today", "Find", "Stock", "Method"]

#: Every section name the site has published, and the section that now serves
#: it. A bookmark from before the four-section merge must still land somewhere
#: real rather than silently falling back to the home page.
LEGACY = {
    "Dashboard": "Today",
    "Market": "Today",
    "Movers": "Today",
    "Screener": "Find",
    "Setups": "Find",
    "Industries": "Find",
    "Methodology": "Method",
}


def test_production_navigation_survives_repeated_reruns():
    at = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    assert not at.exception

    # st.segmented_control is represented as a button_group by AppTest.
    nav = at.button_group[0]
    assert nav.value == "Today"

    # Exercise every production view and then cycle back through the first two.
    # Each set_value(...).run() is an explicit simulated user interaction/rerun.
    for view in VIEWS[1:] + ["Today", "Find"]:
        nav.set_value(view)
        at.run(timeout=30)
        assert not at.exception
        assert at.button_group[0].value == view
        nav = at.button_group[0]


def test_every_retired_section_name_still_resolves():
    """Links published before the merge must not land on a fallback by accident."""
    for legacy, expected in LEGACY.items():
        at = AppTest.from_file(ENTRYPOINT, default_timeout=60)
        at.query_params["view"] = legacy
        at.run()
        assert not at.exception, f"?view={legacy} raised"
        assert at.button_group[0].value == expected, (
            f"?view={legacy} opened {at.button_group[0].value}, not {expected}"
        )


def test_an_unknown_section_falls_back_to_today():
    at = AppTest.from_file(ENTRYPOINT, default_timeout=60)
    at.query_params["view"] = "NotASection"
    at.run()
    assert not at.exception
    assert at.button_group[0].value == "Today"
