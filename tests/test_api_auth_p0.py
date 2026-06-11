"""P0 auth hardening smoke tests for sensitive API routes."""

from __future__ import annotations


def test_workspace_settings_requires_auth():
    from integrated_dashboard import app

    client = app.test_client()
    resp = client.get("/api/workspaces/default_workspace/settings")
    assert resp.status_code == 401


def test_chatbot_requires_auth():
    from integrated_dashboard import app

    client = app.test_client()
    resp = client.post("/api/chatbot/ask", json={"question": "hello"})
    assert resp.status_code == 401


def test_admin_db_health_requires_admin_auth():
    from integrated_dashboard import app

    client = app.test_client()
    resp = client.get("/admin/db/health")
    assert resp.status_code == 401


def test_legacy_github_metrics_requires_auth():
    from integrated_dashboard import app

    client = app.test_client()
    resp = client.get("/api/github-metrics/demo-assignment")
    assert resp.status_code == 401


def test_import_validate_requires_auth():
    from integrated_dashboard import app

    client = app.test_client()
    resp = client.post("/api/import/validate", json={"assignments": []})
    assert resp.status_code == 401
