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


@patch("services.assignment_metrics_config.stored_connector_credentials")
def test_railway_ready_with_token_and_project(mock_stored):
    mock_stored.return_value = {
        "railway_token": "rw_token",
        "railway_project_id": "proj-123",
    }
    assert connector_credentials_ready("ws1", "a1", "railway") is True


@patch("services.assignment_metrics_config.stored_connector_credentials")
def test_vercel_ready_with_token_and_project(mock_stored):
    mock_stored.return_value = {
        "vercel_token": "vc_token",
        "vercel_project_id": "prj_abc",
    }
    assert connector_credentials_ready("ws1", "a1", "vercel") is True


def test_missing_connector_message_railway_and_vercel():
    assert "Railway" in missing_connector_message("railway")
    assert "Vercel" in missing_connector_message("vercel")


@patch("services.assignment_metrics_config.stored_connector_credentials")
def test_azure_ready_with_service_principal(mock_stored):
    mock_stored.return_value = {
        "azure_tenant_id": "tenant-1",
        "azure_client_id": "client-1",
        "azure_client_secret": "secret-1",
        "azure_subscription_id": "sub-1",
    }
    assert connector_credentials_ready("ws1", "a1", "azure") is True


def test_missing_connector_message_azure():
    assert "Azure" in missing_connector_message("azure")


@patch("requests.post")
def test_railway_validation_uses_graphql_v2_endpoint(mock_post):
    from services.embedded.railway_metrics import RAILWAY_GRAPHQL_V2, validate_railway_connection

    mock_resp = mock_post.return_value
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"me": {"id": "u1", "email": "a@b.com", "name": "A"}}}

    result = validate_railway_connection("rw-token-123")
    assert result["valid"] is True
    assert mock_post.call_args[0][0] == RAILWAY_GRAPHQL_V2
    assert "Bearer rw-token-123" in mock_post.call_args[1]["headers"]["Authorization"]


@patch("requests.post")
def test_railway_project_token_validation(mock_post):
    from services.embedded.railway_metrics import validate_railway_connection

    account_resp = mock_post.return_value
    account_resp.status_code = 200
    account_resp.json.return_value = {
        "errors": [{"message": "Not Authorized"}],
        "data": {"me": None},
    }

    project_resp = type("R", (), {})()
    project_resp.status_code = 200
    project_resp.json = lambda: {
        "data": {"projectToken": {"projectId": "proj-1", "environmentId": "env-1"}}
    }
    mock_post.side_effect = [account_resp, project_resp]

    result = validate_railway_connection("project-token", project_id="proj-1")
    assert result["valid"] is True
    assert result["token_type"] == "project"
