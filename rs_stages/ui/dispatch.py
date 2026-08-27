"""Remote-trigger the GitHub Actions audit from the deployed terminal.

The site is public with no login, so this is a real abuse surface: anyone
visiting can click the button. Two guards keep that safe. First, dispatching
requires a personal access token in `st.secrets` that only the site's owner
can set — with it absent, the feature degrades to a clear, non-crashing
notice rather than a button that silently does nothing. Second, the button
is disabled whenever the workflow's own run history shows a run inside the
cooldown window, checked against GitHub's run list rather than any local or
per-browser state, so the limit holds across every visitor at once, not just
repeat clicks from the same session.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

REPO_OWNER = "Pareshking"
REPO_NAME = "RS-Stages"
WORKFLOW_FILE = "real_data_audit.yml"
API_ROOT = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

#: Minimum minutes between dispatches, checked against the workflow's own run
#: history rather than any per-visitor state. A real audit run takes about
#: three minutes; this is sized to comfortably outlast one, not to throttle
#: legitimate re-checks after a genuine miss.
COOLDOWN_MINUTES = 20

REQUEST_TIMEOUT_SECONDS = 10


@dataclass
class DispatchStatus:
    """What the button should show, decided before it is ever clicked."""

    configured: bool
    can_dispatch: bool
    message: str
    last_run_at: datetime | None = None


def _token(secrets) -> str | None:
    try:
        value = secrets.get("GITHUB_DISPATCH_TOKEN")
    except Exception:
        return None
    return value or None


def _api_request(path: str, token: str, method: str = "GET", body: dict | None = None):
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}, response.status


def check_status(secrets) -> DispatchStatus:
    """Read-only: is dispatching configured, and is the cooldown clear?

    Never raises. A network failure here must degrade the button to
    disabled-with-a-reason, not crash the Dashboard page that hosts it.
    """
    token = _token(secrets)
    if token is None:
        return DispatchStatus(
            configured=False,
            can_dispatch=False,
            message="Manual trigger is not configured on this deployment.",
        )
    try:
        runs, _ = _api_request(
            f"/actions/workflows/{WORKFLOW_FILE}/runs?per_page=1", token
        )
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError) as exc:
        return DispatchStatus(
            configured=True,
            can_dispatch=False,
            message=f"Could not reach GitHub to check run history ({type(exc).__name__}).",
        )
    entries = runs.get("workflow_runs") or []
    if not entries:
        return DispatchStatus(configured=True, can_dispatch=True, message="")
    created = entries[0].get("created_at")
    try:
        last_run = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return DispatchStatus(configured=True, can_dispatch=True, message="")
    elapsed_minutes = (datetime.now(timezone.utc) - last_run).total_seconds() / 60.0
    if elapsed_minutes < COOLDOWN_MINUTES:
        wait = COOLDOWN_MINUTES - elapsed_minutes
        return DispatchStatus(
            configured=True,
            can_dispatch=False,
            message=f"A run started {elapsed_minutes:.0f} minutes ago — try again in {wait:.0f} minutes.",
            last_run_at=last_run,
        )
    return DispatchStatus(configured=True, can_dispatch=True, message="", last_run_at=last_run)


def trigger_audit(secrets) -> tuple[bool, str]:
    """Fire the audit now. Callers must have already checked check_status()."""
    token = _token(secrets)
    if token is None:
        return False, "Manual trigger is not configured on this deployment."
    try:
        _api_request(
            f"/actions/workflows/{WORKFLOW_FILE}/dispatches",
            token,
            method="POST",
            body={"ref": "main"},
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return False, f"GitHub rejected the trigger (HTTP {exc.code}): {detail}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return False, f"Could not reach GitHub ({type(exc).__name__})."
    return True, "Triggered. The audit takes about three minutes; refresh after that to see it."
