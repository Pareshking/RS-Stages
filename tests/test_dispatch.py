"""The manual-trigger control must never crash the page it sits on, and its
rate limit must hold across every visitor, not just repeat clicks in one
browser session.

The site is public with no login, so a button that fires a real GitHub
Actions run and a real git push is a real abuse surface. These tests drive
rs_stages.ui.dispatch directly, with a fake secrets object and a mocked
urllib, so they exercise the actual decision logic without a live token or
a real network call.
"""
import json
import urllib.error
from unittest.mock import patch

import pytest

from rs_stages.ui import dispatch


class _FakeSecrets(dict):
    """Mimics st.secrets' .get() surface without needing a real secrets.toml."""


def _http_response(payload: dict, status: int = 200):
    class _Resp:
        def __enter__(self_):
            return self_

        def __exit__(self_, *a):
            return False

        def read(self_):
            return json.dumps(payload).encode("utf-8")

    resp = _Resp()
    resp.status = status
    return resp


def test_no_token_degrades_to_not_configured_without_any_network_call():
    with patch("urllib.request.urlopen") as mock_open:
        status = dispatch.check_status(_FakeSecrets())
    assert status.configured is False
    assert status.can_dispatch is False
    mock_open.assert_not_called()


def test_a_secrets_object_that_raises_degrades_instead_of_propagating():
    class _Explosive:
        def get(self, key):
            raise RuntimeError("no secrets.toml on this deployment")

    status = dispatch.check_status(_Explosive())
    assert status.configured is False
    assert status.can_dispatch is False


def test_a_run_inside_the_cooldown_blocks_dispatch():
    from datetime import datetime, timedelta, timezone

    recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"workflow_runs": [{"created_at": recent}]}
    with patch("urllib.request.urlopen", return_value=_http_response(payload)):
        status = dispatch.check_status(_FakeSecrets(GITHUB_DISPATCH_TOKEN="tok"))
    assert status.configured is True
    assert status.can_dispatch is False
    assert "minutes" in status.message


def test_a_run_outside_the_cooldown_allows_dispatch():
    from datetime import datetime, timedelta, timezone

    old = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"workflow_runs": [{"created_at": old}]}
    with patch("urllib.request.urlopen", return_value=_http_response(payload)):
        status = dispatch.check_status(_FakeSecrets(GITHUB_DISPATCH_TOKEN="tok"))
    assert status.can_dispatch is True


def test_no_prior_runs_at_all_allows_dispatch():
    with patch("urllib.request.urlopen", return_value=_http_response({"workflow_runs": []})):
        status = dispatch.check_status(_FakeSecrets(GITHUB_DISPATCH_TOKEN="tok"))
    assert status.can_dispatch is True


def test_a_network_failure_disables_dispatch_rather_than_crashing():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route")):
        status = dispatch.check_status(_FakeSecrets(GITHUB_DISPATCH_TOKEN="tok"))
    assert status.configured is True
    assert status.can_dispatch is False
    assert "GitHub" in status.message


def test_trigger_without_a_token_never_calls_the_network():
    with patch("urllib.request.urlopen") as mock_open:
        ok, message = dispatch.trigger_audit(_FakeSecrets())
    assert ok is False
    mock_open.assert_not_called()


def test_a_successful_trigger_reports_success():
    with patch("urllib.request.urlopen", return_value=_http_response({}, status=204)):
        ok, message = dispatch.trigger_audit(_FakeSecrets(GITHUB_DISPATCH_TOKEN="tok"))
    assert ok is True
    assert "three minutes" in message


def test_a_rejected_trigger_surfaces_githubs_own_reason():
    import io

    body = io.BytesIO(b'{"message": "Bad credentials"}')

    def _raise(*a, **kw):
        raise urllib.error.HTTPError("https://api.github.com/x", 401, "Unauthorized", {}, body)

    with patch("urllib.request.urlopen", side_effect=_raise):
        ok, message = dispatch.trigger_audit(_FakeSecrets(GITHUB_DISPATCH_TOKEN="bad-token"))
    assert ok is False
    assert "401" in message


def test_the_dispatch_request_targets_this_repository_and_the_audit_workflow():
    """A copy-paste error here would silently trigger the wrong repo or workflow."""
    assert dispatch.REPO_OWNER == "Pareshking"
    assert dispatch.REPO_NAME == "RS-Stages"
    assert dispatch.WORKFLOW_FILE == "real_data_audit.yml"
    assert dispatch.API_ROOT == "https://api.github.com/repos/Pareshking/RS-Stages"
