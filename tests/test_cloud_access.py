"""Cloud Access Framework — AWS cross-account role readiness."""

import pytest

from services.cloud_access.aws_sts_broker import (
    AWS_ASSUME_ROLE_AUTH,
    aws_auth_method,
    aws_credentials_ready,
    suggested_external_id,
)
from services.cloud_access.flags import cloud_access_capabilities


@pytest.fixture(autouse=True)
def clear_flags(monkeypatch):
    for name in (
        "ENABLE_AWS_CROSS_ACCOUNT_ROLE",
        "ENABLE_AWS_ROLE_CONNECTOR_UI",
        "DISABLE_AWS_ACCESS_KEYS",
        "CTOLENS_AWS_ACCOUNT_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def test_cloud_access_capabilities_default():
    caps = cloud_access_capabilities()
    assert caps["aws_cross_account_role"] is False
    assert caps["aws_role_onboarding_available"] is False


def test_cloud_access_capabilities_when_ready(monkeypatch):
    monkeypatch.setenv("ENABLE_AWS_CROSS_ACCOUNT_ROLE", "true")
    monkeypatch.setenv("ENABLE_AWS_ROLE_CONNECTOR_UI", "true")
    monkeypatch.setenv("CTOLENS_AWS_ACCOUNT_ID", "111122223333")
    caps = cloud_access_capabilities()
    assert caps["aws_role_onboarding_available"] is True
    assert caps["ctolens_aws_account_id"] == "111122223333"


def test_aws_role_config_ready():
    stored = {
        "auth_method": AWS_ASSUME_ROLE_AUTH,
        "aws_role_arn": "arn:aws:iam::123456789012:role/CTOLensReadOnlyRole",
        "aws_account_id": "123456789012",
        "aws_external_id": "ctolens-ws-a1",
    }
    assert aws_auth_method(stored) == AWS_ASSUME_ROLE_AUTH
    assert aws_credentials_ready(stored) is True


def test_aws_access_key_still_supported():
    stored = {"aws_access_key": "AKIA...", "aws_secret_key": "secret"}
    assert aws_auth_method(stored) == "aws_access_key"
    assert aws_credentials_ready(stored) is True


def test_suggested_external_id_is_tenant_scoped():
    ext = suggested_external_id("workspace-1", "assignment-1")
    assert "workspace-1" in ext
    assert "assignment-1" in ext
