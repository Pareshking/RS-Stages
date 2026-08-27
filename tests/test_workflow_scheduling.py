"""Scheduling and publishing invariants for the workflows that write to main.

Two scheduled workflows commit to the repository: the weekday research audit
and the Friday universe refresh. They must never share a fire-minute — the
audit runs for about three minutes and the refresh for about twenty seconds,
so if the constituent list changed and the two collided, the refresh would
land first and the audit's push would be rejected non-fast-forward at its
final step. The audit replaces the price panel on the release *before* it
commits, so that failure leaves a panel one session ahead of the committed
snapshot: exactly the drift the loader refuses to draw through, i.e. a live
terminal with no charts until someone re-runs by hand.

The audit runs the morning after each session (01:00 UTC / 6:30 IST, D-2.2.12)
rather than the same evening, giving the price provider a longer buffer after
the 15:30 IST close; the refresh still runs Friday evening. The two schedules
no longer share a calendar day at all, which removes the collision risk by
construction rather than by a tight margin — these tests still pin it
explicitly rather than trusting that construction to hold as either schedule
changes in the future.

These tests pin the two properties that prevent it: the schedules are ordered
and disjoint, and neither push can die on a race it could rebase past.

Parsed with the standard library only. PyYAML is not in requirements.txt and is
absent from the resolved production environment, so importing it here would
pass locally and fail in CI.
"""
from __future__ import annotations

import pathlib
import re

WORKFLOWS = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows"

#: Minutes in a week, keyed from Monday 00:00 UTC, so two schedules can be
#: compared as sets rather than by eyeballing two cron strings.
WEEK_MINUTES = 7 * 24 * 60


def _field(spec: str, low: int, high: int) -> set[int]:
    """Expand one cron field into the values it matches."""
    values: set[int] = set()
    for part in spec.split(","):
        step = 1
        if "/" in part:
            part, _, raw_step = part.partition("/")
            step = int(raw_step)
        if part == "*":
            start, end = low, high
        elif "-" in part:
            start_raw, _, end_raw = part.partition("-")
            start, end = int(start_raw), int(end_raw)
        else:
            start = end = int(part)
        values.update(range(start, end + 1, step))
    assert values <= set(range(low, high + 1)), f"out-of-range cron field {spec!r}"
    return values


def fire_minutes(cron: str) -> set[int]:
    """Minutes-into-the-week at which a five-field cron fires.

    Only day-of-week is honoured for the day, which is all these schedules use;
    a day-of-month restriction would make the answer depend on the calendar and
    is rejected rather than silently ignored.
    """
    minute, hour, dom, month, dow = cron.split()
    assert dom == "*" and month == "*", f"unsupported day-of-month/month in {cron!r}"
    # cron day-of-week is Sunday-based; the week here starts on Monday.
    days = {(day + 6) % 7 for day in _field(dow, 0, 6)}
    return {
        day * 24 * 60 + hour_value * 60 + minute_value
        for day in days
        for hour_value in _field(hour, 0, 23)
        for minute_value in _field(minute, 0, 59)
    }


def _workflows() -> dict[str, str]:
    return {path.name: path.read_text() for path in sorted(WORKFLOWS.glob("*.yml"))}


def _pushing_workflows() -> dict[str, str]:
    """Workflows that write commits back to the repository."""
    return {name: text for name, text in _workflows().items() if "git push" in text}


def _crons(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"-\s*cron:\s*['\"](.+?)['\"]", text)]


def test_the_two_publishing_workflows_are_the_ones_expected():
    """A third workflow that pushes would need its own place in this ordering."""
    assert set(_pushing_workflows()) == {"real_data_audit.yml", "update_nse_universe.yml"}


def test_no_two_publishing_workflows_share_a_fire_minute():
    """Concurrent runs race for the push; the loser is rejected non-fast-forward."""
    schedules = {
        name: set().union(*(fire_minutes(c) for c in _crons(text))) if _crons(text) else set()
        for name, text in _pushing_workflows().items()
    }
    names = sorted(schedules)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            overlap = schedules[first] & schedules[second]
            assert not overlap, (
                f"{first} and {second} both fire at minute(s) {sorted(overlap)} of the week; "
                "both push to main, so one push is rejected."
            )


def test_the_universe_refresh_is_seen_by_the_very_next_audit_run():
    """Whichever audit run comes right after the refresh must be able to see it.

    The audit checks the repository out when it starts, so a universe published
    after that start is invisible to it until the following run. This does not
    assume the two land on the same calendar day: when the audit moved to the
    morning after each session (D-2.2.12), its Friday slot shifted to catching
    Thursday's close, and it is the *Saturday* run that now lands after the
    Friday refresh — the relationship is "the next audit run in the week",
    wrapping past Sunday if needed, not a fixed weekday.
    """
    audit = sorted(set().union(*(fire_minutes(c) for c in _crons(_workflows()["real_data_audit.yml"]))))
    universe = set().union(
        *(fire_minutes(c) for c in _crons(_workflows()["update_nse_universe.yml"]))
    )
    assert audit, "the audit is expected to have a schedule"
    assert universe, "the universe refresh is expected to have a schedule"
    refresh_minute = max(universe)
    after = sorted(m for m in audit if m > refresh_minute)
    next_audit = after[0] if after else audit[0] + WEEK_MINUTES
    gap = next_audit - refresh_minute
    # The refresh takes about 20 seconds; the margin is for a slow runner, not
    # for the job itself.
    assert gap >= 15, f"only {gap} minutes between the refresh and the next audit run"


def test_every_publishing_push_can_survive_a_moved_main():
    """A bare `git push` discards the whole run when main moved underneath it."""
    for name, text in _pushing_workflows().items():
        assert "git pull --rebase origin main" in text, (
            f"{name} pushes without a rebase path: a concurrent commit kills the run."
        )
        # The rebase must be a retry, not a single second attempt.
        assert re.search(r"for attempt in .*\n(?:.*\n)*?.*git push", text), (
            f"{name} does not retry its push."
        )


def test_publishing_workflows_check_out_enough_history_to_rebase():
    """`git pull --rebase` needs a merge base; the default checkout is depth 1."""
    for name, text in _pushing_workflows().items():
        assert "fetch-depth: 0" in text, (
            f"{name} rebases on a shallow clone, which has no merge base to rebase onto."
        )
