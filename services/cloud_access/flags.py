"""Feature flags for Cloud Access Framework (AWS cross-account role first)."""

from __future__ import annotations

import os


def _flag(name: str) -> bool:
    return os.getenv(name, "false").lower() == "true"


def aws_cross_account_role_enabled() -> bool:
    return _flag("ENABLE_AWS_CROSS_ACCOUNT_ROLE")


def aws_role_connector_ui_enabled() -> bool:
    return _flag("ENABLE_AWS_ROLE_CONNECTOR_UI")


def aws_access_keys_disabled() -> bool:
    return _flag("DISABLE_AWS_ACCESS_KEYS")


def cloud_access_capabilities() -> dict:
    ctolens_account = (os.getenv("CTOLENS_AWS_ACCOUNT_ID") or "").strip()
    ui = aws_role_connector_ui_enabled()
    role_mode = aws_cross_account_role_enabled()
    return {
        "aws_cross_account_role": role_mode,
        "aws_role_connector_ui": ui,
        "disable_aws_access_keys": aws_access_keys_disabled(),
        "aws_role_onboarding_available": role_mode and ui and bool(ctolens_account),
        "ctolens_aws_account_id": ctolens_account or None,
    }
