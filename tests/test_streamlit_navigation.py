"""Regression coverage for Streamlit interaction/rerun failures.

A plain HTTP health check only proves that the initial script can boot. This test
explicitly changes the navigation widget and reruns the real production entrypoint,
which is the execution pattern that previously exposed the white-page crash.
"""

from streamlit.testing.v1 import AppTest


VIEWS = ["Dashboard", "Screener", "Industries", "Market", "Movers", "Stock", "Methodology"]


def test_production_navigation_survives_repeated_reruns():
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception

    # st.segmented_control is represented as a button_group by AppTest.
    nav = at.button_group[0]
    assert nav.value == "Dashboard"

    # Exercise every production view and then cycle back through the first two.
    # Each set_value(...).run() is an explicit simulated user interaction/rerun.
    for view in VIEWS[1:] + ["Dashboard", "Screener"]:
        nav.set_value(view)
        at.run(timeout=30)
        assert not at.exception
        assert at.button_group[0].value == view
        nav = at.button_group[0]
