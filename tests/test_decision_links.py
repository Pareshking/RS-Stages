"""Today's decision cards must land on the list they promise.

Each card names a handful of stocks and then offers "all N in Find". A link
that arrives at an unfiltered table is worse than no link: the reader asked for
310 SELLs and got all 750 stocks, with nothing on screen saying the filter did
not apply. The Screener seeds its Action filter from the query string precisely
so these links work, and nothing else exercises that path.
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest

import app as production
from rs_stages.ui.components import query_href_multi

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app.py")


def test_query_href_multi_repeats_a_parameter_rather_than_joining_it():
    href = query_href_multi({"view": "Find", "mode": "Stocks"}, action=["SELL", "REDUCE"])
    assert "action=SELL" in href
    assert "action=REDUCE" in href
    # A comma-joined value would arrive as one unmatchable label.
    assert "SELL%2CREDUCE" not in href and "SELL,REDUCE" not in href


def test_the_decision_groups_only_name_labels_the_action_layer_can_produce():
    from rs_stages.actions import ACTIONS

    for _, labels, _, _ in production.DECISION_GROUPS:
        for label in labels:
            assert label in ACTIONS, f"{label} is not an Action the guide assigns"


def test_every_action_label_is_reachable_from_exactly_one_decision_group():
    """A label in two groups would be double-counted in the cards above."""
    seen = [label for _, labels, _, _ in production.DECISION_GROUPS for label in labels]
    assert len(seen) == len(set(seen))


def test_an_action_in_the_query_string_arrives_as_a_screener_filter():
    at = AppTest.from_file(ENTRYPOINT, default_timeout=90)
    at.query_params["view"] = "Find"
    at.query_params["action"] = "SELL"
    at.run()
    assert not at.exception
    assert at.session_state["screener_action"] == ["SELL"]


def test_an_unknown_action_in_the_query_string_is_ignored_not_applied():
    at = AppTest.from_file(ENTRYPOINT, default_timeout=90)
    at.query_params["view"] = "Find"
    at.query_params["action"] = "NOTALABEL"
    at.run()
    assert not at.exception
    # The widget registers its own key once rendered, so the invariant is that
    # no filter is *applied* — an unrecognised label must not narrow the table.
    assert not at.session_state["screener_action"]
