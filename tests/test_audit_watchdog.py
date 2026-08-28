"""The watchdog must check strictly after the audit's own schedule, on the
same days, and must fail loudly rather than silently no-op when its
retrigger token is missing.

Parsed with the standard library only, matching test_workflow_scheduling.py
-- PyYAML is absent from the resolved production environment.
"""
from __future__ import annotations

import pathlib
import re

WORKFLOWS = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows"
WATCHDOG = WORKFLOWS / "audit_watchdog.yml"
AUDIT = WORKFLOWS / "real_data_audit.yml"


def _field(spec: str, low: int, high: int) -> set[int]:
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
    return values


def _crons(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"-\s*cron:\s*['\"](.+?)['\"]", text)]


def _one_cron(path: pathlib.Path) -> str:
    crons = _crons(path.read_text())
    assert len(crons) == 1, f"{path.name} expected exactly one cron schedule, found {crons}"
    return crons[0]


def _hour_minute_days(cron: str) -> tuple[int, int, set[int]]:
    minute, hour, dom, month, dow = cron.split()
    assert dom == "*" and month == "*", f"unsupported day-of-month/month in {cron!r}"
    return int(minute), int(hour), _field(dow, 0, 6)


def test_the_watchdog_file_exists():
    assert WATCHDOG.exists(), "audit_watchdog.yml is missing"


def test_the_watchdog_runs_on_exactly_the_audit_s_own_days():
    """Checking on a day the audit has no run scheduled wastes a run and
    proves nothing."""
    _, _, watchdog_days = _hour_minute_days(_one_cron(WATCHDOG))
    _, _, audit_days = _hour_minute_days(_one_cron(AUDIT))
    assert watchdog_days == audit_days


def test_the_watchdog_fires_strictly_after_the_audit_each_day():
    watchdog_minute, watchdog_hour, _ = _hour_minute_days(_one_cron(WATCHDOG))
    audit_minute, audit_hour, _ = _hour_minute_days(_one_cron(AUDIT))
    watchdog_total = watchdog_hour * 60 + watchdog_minute
    audit_total = audit_hour * 60 + audit_minute
    gap = watchdog_total - audit_total
    assert gap > 0, "the watchdog must check after the audit's own target time, not before"
    # The audit itself takes about 3 minutes; this is buffer for scheduling
    # jitter (observed up to ~110 minutes late), not for the job itself.
    assert gap >= 30, f"only {gap} minutes between the audit's target time and the watchdog check"


def test_the_watchdog_does_not_push_and_is_excluded_from_the_push_race_tests():
    text = WATCHDOG.read_text()
    assert "git push" not in text, (
        "the watchdog should only read run history and dispatch a run, never commit"
    )


def test_a_missing_retrigger_token_fails_loudly_rather_than_silently_skipping():
    text = WATCHDOG.read_text()
    assert "::error::" in text, "a missing token must be a visible failure, not a silent no-op"
    assert "exit 1" in text


def test_the_retrigger_step_uses_a_distinct_secret_from_the_automatic_token():
    """The automatic GITHUB_TOKEN cannot dispatch another workflow run --
    conflating the two would make the retrigger step fail every time."""
    text = WATCHDOG.read_text()
    assert "secrets.WORKFLOW_TRIGGER_PAT" in text
    assert "github.token" in text  # still used for the read-only check


def test_the_watchdog_targets_the_real_audit_workflow_file():
    text = WATCHDOG.read_text()
    assert "real_data_audit.yml" in text


def test_the_freshness_check_is_anchored_to_today_not_a_rolling_window():
    """A rolling window let a manual run from the evening before satisfy the
    check at the watchdog's own time the next morning, without that run
    being today's actual scheduled attempt at all. Found live on 28 Aug
    2026: a 23:05 UTC manual dispatch sat inside a 6-hours-ago window at the
    watchdog's 02:00 UTC check the next day, masking the real miss."""
    text = WATCHDOG.read_text()
    assert "hours ago" not in text, "a rolling lookback window reintroduces the exact bug found on 28 Aug 2026"
    audit_minute, audit_hour, _ = _hour_minute_days(_one_cron(AUDIT))
    anchor = f"{audit_hour:02d}:{audit_minute:02d}:00Z"
    assert anchor in text, (
        f"the freshness check must anchor to the audit's own target time ({anchor}), "
        "not an arbitrary window"
    )
