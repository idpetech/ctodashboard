"""Tests for assignment metrics cache (Load All Metrics persistence)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.assignment_metrics_store import (
    SETTINGS_KEY,
    assess_snapshot_staleness,
    build_metrics_response,
    get_stored_snapshot,
    is_metrics_cache_enabled,
    resolve_assignment_metrics,
    store_metrics_snapshot,
)


@pytest.fixture(autouse=True)
def metrics_cache_flag(monkeypatch):
    monkeypatch.setenv("ENABLE_ASSIGNMENT_METRICS_CACHE", "true")


def test_flag_enabled():
    assert is_metrics_cache_enabled() is True


def test_store_and_get_snapshot():
    mock_db = MagicMock()
    mock_db.get_workspace.return_value = {
        "name": "WS",
        "description": "",
        "settings": {},
    }
    mock_db.store_workspace.return_value = True

    assignment = {
        "id": "a1",
        "metrics_config": {"github": {"enabled": True}},
    }
    payload = {"github": [{"repo_name": "r1", "commits_last_30_days": 3}]}

    assert store_metrics_snapshot(mock_db, "ws1", "a1", assignment, payload, duration_seconds=12.5)

    stored_call = mock_db.store_workspace.call_args
    settings = stored_call.kwargs["settings"]
    entry = settings[SETTINGS_KEY]["a1"]
    assert entry["payload"]["github"][0]["repo_name"] == "r1"
    assert entry["metrics_fetched"] is True
    assert entry["connectors_ok"] == ["github"]

    mock_db.get_workspace.return_value = {
        "name": "WS",
        "description": "",
        "settings": settings,
    }
    snap = get_stored_snapshot(mock_db, "ws1", "a1")
    assert snap is not None
    assert snap["payload"]["github"][0]["commits_last_30_days"] == 3


def test_resolve_returns_stored_without_live_fetch():
    assignment = {"id": "a1", "metrics_config": {"github": {"enabled": True}}}
    snapshot = {
        "fetched_at": "2026-07-06T12:00:00Z",
        "metrics_fetched": True,
        "source_fingerprint": "abc",
        "payload": {"github": [{"repo_name": "cached"}]},
        "connectors_ok": ["github"],
        "connectors_failed": [],
    }

    with patch(
        "services.assignment_metrics_store.get_stored_snapshot",
        return_value=snapshot,
    ):
        with patch(
            "services.assignment_metrics_store.assess_snapshot_staleness",
            return_value={"is_stale": False, "stale_reason": None},
        ):
            collect = MagicMock()
            body, status = resolve_assignment_metrics("ws1", "a1", assignment, collect)

    assert status == 200
    assert body["source"] == "stored"
    assert body["github"][0]["repo_name"] == "cached"
    collect.assert_not_called()


def test_resolve_live_refresh_calls_collect_and_store():
    assignment = {"id": "a1", "metrics_config": {"jira": {"enabled": True}}}
    payload = {"jira": {"open_issues_count": 5}}

    def collect(ws, aid, asn):
        return payload

    mock_db = MagicMock()
    mock_db.get_workspace.return_value = {"name": "WS", "description": "", "settings": {}}
    mock_db.store_workspace.return_value = True

    with patch("services.assignment_metrics_store.resolve_workspace_db", return_value=mock_db):
        body, status = resolve_assignment_metrics(
            "ws1",
            "a1",
            assignment,
            collect,
            refresh=True,
        )

    assert status == 200
    assert body["source"] == "live"
    assert body["jira"]["open_issues_count"] == 5
    mock_db.store_workspace.assert_called_once()


def test_resolve_stored_missing_returns_404():
    assignment = {"id": "a1", "metrics_config": {}}
    collect = MagicMock()

    with patch("services.assignment_metrics_store.get_stored_snapshot", return_value=None):
        body, status = resolve_assignment_metrics(
            "ws1",
            "a1",
            assignment,
            collect,
            source="stored",
        )

    assert status == 404
    assert body["error"] == "no_stored_metrics"
    collect.assert_not_called()


def test_flag_off_always_live(monkeypatch):
    monkeypatch.setenv("ENABLE_ASSIGNMENT_METRICS_CACHE", "false")
    assignment = {"id": "a1"}
    collect = MagicMock(return_value={"github": []})

    body, status = resolve_assignment_metrics("ws1", "a1", assignment, collect, source="stored")

    assert status == 200
    assert body == {"github": []}
    collect.assert_called_once()


def test_staleness_when_fingerprint_changes():
    assignment = {"id": "a1", "metrics_config": {"aws": {"enabled": True}}}
    snapshot = {
        "fetched_at": "2026-07-06T12:00:00Z",
        "source_fingerprint": "oldfp",
    }
    result = assess_snapshot_staleness(snapshot, assignment)
    assert result["is_stale"] is True
    assert "changed" in (result["stale_reason"] or "")


def test_build_metrics_response_includes_metadata():
    snapshot = {
        "fetched_at": "2026-07-06T12:00:00Z",
        "metrics_fetched": True,
        "payload": {"github": []},
        "connectors_ok": [],
        "connectors_failed": ["aws"],
    }
    body = build_metrics_response(
        source="stored",
        workspace_id="ws1",
        assignment_id="a1",
        snapshot=snapshot,
        staleness={"is_stale": False, "stale_reason": None},
    )
    assert body["source"] == "stored"
    assert body["connectors_failed"] == ["aws"]
    assert isinstance(body["github"], list)
