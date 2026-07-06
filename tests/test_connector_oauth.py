"""Tests for connector OAuth flags, state, and credential readiness."""

import time
from unittest.mock import patch

import jwt
import pytest

from services.connectors.oauth_flags import oauth_capabilities
from services.connectors.oauth_state import OAuthStateError, build_oauth_state, parse_oauth_state
from services.connectors.token_resolver import (
    github_credentials_ready,
    jira_credentials_ready,
    should_use_github_oauth,
    should_use_jira_oauth,
)


@pytest.fixture(autouse=True)
def oauth_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-oauth-state-secret")
    for name in (
        "ENABLE_GITHUB_APP_CONNECTOR",
        "ENABLE_JIRA_OAUTH_CONNECTOR",
        "ENABLE_CONNECTOR_OAUTH_UI",
        "PREFER_OAUTH_CONNECTORS",
        "DISABLE_MANUAL_TOKENS",
        "GITHUB_APP_ID",
        "JIRA_OAUTH_CLIENT_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def test_oauth_capabilities_default_off():
    caps = oauth_capabilities()
    assert caps["github_app_connector"] is False
    assert caps["jira_oauth_connector"] is False
    assert caps["github_oauth_available"] is False


def test_oauth_capabilities_when_configured(monkeypatch):
    monkeypatch.setenv("ENABLE_GITHUB_APP_CONNECTOR", "true")
    monkeypatch.setenv("ENABLE_CONNECTOR_OAUTH_UI", "true")
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    caps = oauth_capabilities()
    assert caps["github_oauth_available"] is True


def test_oauth_state_round_trip():
    token = build_oauth_state(
        connector="github",
        workspace_id="ws1",
        assignment_id="a1",
    )
    ctx = parse_oauth_state(token, expected_connector="github")
    assert ctx["workspace_id"] == "ws1"
    assert ctx["assignment_id"] == "a1"


def test_oauth_state_rejects_wrong_connector():
    token = build_oauth_state(connector="jira", workspace_id="ws1", assignment_id="a1")
    with pytest.raises(OAuthStateError):
        parse_oauth_state(token, expected_connector="github")


def test_oauth_state_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-oauth-state-secret")
    payload = {
        "purpose": "connector_oauth",
        "connector": "github",
        "workspace_id": "ws1",
        "assignment_id": "a1",
        "exp": int(time.time()) - 10,
    }
    token = jwt.encode(payload, "test-oauth-state-secret", algorithm="HS256")
    with pytest.raises(OAuthStateError):
        parse_oauth_state(token, expected_connector="github")


def test_github_oauth_ready_with_installation():
    stored = {
        "auth_method": "github_app",
        "github_installation_id": "999",
        "github_org": "my-org",
    }
    assert should_use_github_oauth(stored) is True
    assert github_credentials_ready(stored) is True


def test_github_manual_ready_with_pat():
    stored = {"github_token": "ghp_test", "github_org": "my-org"}
    assert should_use_github_oauth(stored) is False
    assert github_credentials_ready(stored) is True


def test_jira_oauth_ready_with_refresh_and_cloud():
    stored = {
        "auth_method": "jira_oauth",
        "jira_refresh_token": "refresh",
        "jira_cloud_id": "cloud-1",
        "jira_url": "https://example.atlassian.net",
    }
    assert should_use_jira_oauth(stored) is True
    assert jira_credentials_ready(stored) is True


def test_jira_manual_ready_with_api_token():
    stored = {
        "jira_token": "atlassian_token",
        "jira_email": "user@example.com",
        "jira_url": "https://example.atlassian.net",
    }
    assert should_use_jira_oauth(stored) is False
    assert jira_credentials_ready(stored) is True


@patch("services.connectors.github_app_auth.requests.post")
@patch("services.connectors.github_app_auth.create_app_jwt")
def test_installation_access_token_cached(mock_jwt, mock_post):
    from services.connectors import github_app_auth

    github_app_auth._INSTALL_TOKEN_CACHE.clear()
    mock_jwt.return_value = "app-jwt"
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = {
        "token": "ghs_installation_token",
        "expires_at": "2099-01-01T00:00:00Z",
    }

    token1 = github_app_auth.get_installation_access_token("42")
    token2 = github_app_auth.get_installation_access_token("42")
    assert token1 == "ghs_installation_token"
    assert token2 == token1
    assert mock_post.call_count == 1
