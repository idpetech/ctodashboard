"""Connector credential isolation — no platform env leak on staging/prod."""

from unittest.mock import patch

import pytest

from services.assignment_metrics_config import (
    connector_credentials_ready,
    missing_connector_message,
)
from services.auth.credential_service import (
    CredentialService,
    allow_connector_env_fallback,
)


@pytest.fixture(autouse=True)
def clear_env_fallback(monkeypatch):
    monkeypatch.delenv("ALLOW_CONNECTOR_ENV_FALLBACK", raising=False)


def test_env_fallback_disabled_by_default():
    assert allow_connector_env_fallback() is False


def test_env_fallback_enabled_when_flag_set(monkeypatch):
    monkeypatch.setenv("ALLOW_CONNECTOR_ENV_FALLBACK", "true")
    assert allow_connector_env_fallback() is True


@patch("services.auth.credential_service.secure_db.get_assignment_credentials")
def test_credential_service_does_not_use_env_without_flag(mock_get, monkeypatch):
    mock_get.return_value = {}
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_platform_token_should_not_leak")
    monkeypatch.setenv("GITHUB_ORG", "platform-org")

    creds = CredentialService().get_github_credentials("ws1", "a1")
    assert creds["token"] is None
    assert creds["org"] is None


@patch("services.auth.credential_service.secure_db.get_assignment_credentials")
def test_credential_service_uses_env_when_flag_enabled(mock_get, monkeypatch):
    mock_get.return_value = {}
    monkeypatch.setenv("ALLOW_CONNECTOR_ENV_FALLBACK", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_local_dev_token")
    monkeypatch.setenv("GITHUB_ORG", "my-org")

    creds = CredentialService().get_github_credentials("ws1", "a1")
    assert creds["token"] == "ghp_local_dev_token"
    assert creds["org"] == "my-org"


@patch("services.assignment_metrics_config.stored_connector_credentials")
def test_connector_not_ready_without_stored_creds(mock_stored):
    mock_stored.return_value = {}
    assert connector_credentials_ready("ws1", "a1", "aws") is False
    assert connector_credentials_ready("ws1", "a1", "github") is False


@patch("services.assignment_metrics_config.stored_connector_credentials")
def test_connector_ready_with_stored_creds(mock_stored):
    mock_stored.return_value = {
        "aws_access_key": "AKIA...",
        "aws_secret_key": "secret",
    }
    assert connector_credentials_ready("ws1", "a1", "aws") is True


@patch("services.assignment_metrics_config.connector_credentials_ready")
@patch("routes.api.deps.get_workspace_connectors")
def test_collect_metrics_skips_aws_without_creds(mock_connectors, mock_ready):
    from routes.api.deps import collect_assignment_metrics

    mock_ready.side_effect = lambda ws, aid, ctype: ctype != "aws"
    mock_connectors.return_value = {"aws": None, "github": None, "jira": None}

    assignment = {
        "metrics_config": {
            "aws": {"enabled": True},
            "github": {"enabled": False},
        }
    }
    result = collect_assignment_metrics("ws1", "a1", assignment)
    assert "aws" in result
    assert "not configured" in result["aws"]["error"].lower()
    assert "github" not in result


def test_missing_connector_message_is_actionable():
    msg = missing_connector_message("aws")
    assert "AWS" in msg
    assert "Setup" in msg
