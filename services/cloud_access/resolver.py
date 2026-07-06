"""Resolve AWS connection config and ephemeral sessions for connectors."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from services.auth.credential_service import allow_connector_env_fallback
from services.cloud_access.aws_sts_broker import (
    AWS_ACCESS_KEY_AUTH,
    AWS_ASSUME_ROLE_AUTH,
    aws_auth_method,
    get_aws_sts_broker,
)
from services.cloud_access.session import CloudAccessSession


def resolve_aws_config(
    stored: Dict[str, Any], *, workspace_id: str, assignment_id: str
) -> Dict[str, Any]:
    """Return AWS auth config from stored assignment credentials (no session tokens)."""
    method = aws_auth_method(stored)
    region = stored.get("aws_region") or "us-east-1"

    if method == AWS_ASSUME_ROLE_AUTH:
        return {
            "auth_method": AWS_ASSUME_ROLE_AUTH,
            "role_arn": stored.get("aws_role_arn"),
            "external_id": stored.get("aws_external_id") or stored.get("external_id"),
            "account_id": stored.get("aws_account_id"),
            "region": region,
            "stored": stored,
            "workspace_id": workspace_id,
            "assignment_id": assignment_id,
        }

    access_key = stored.get("aws_access_key") or stored.get("access_key")
    secret_key = stored.get("aws_secret_key") or stored.get("secret_key")
    if not access_key and allow_connector_env_fallback():
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", region)

    return {
        "auth_method": AWS_ACCESS_KEY_AUTH,
        "access_key": access_key,
        "secret_key": secret_key,
        "region": region,
    }


def get_aws_session(
    stored: Dict[str, Any],
    *,
    workspace_id: str,
    assignment_id: str,
    region: Optional[str] = None,
) -> Optional[CloudAccessSession]:
    """Return ephemeral AWS session for API calls. Tokens are never persisted."""
    config = resolve_aws_config(stored, workspace_id=workspace_id, assignment_id=assignment_id)
    if config["auth_method"] == AWS_ASSUME_ROLE_AUTH:
        return get_aws_sts_broker().get_session(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            stored=stored,
            region=region or config.get("region"),
        )
    access_key = config.get("access_key")
    secret_key = config.get("secret_key")
    if not access_key or not secret_key:
        return None
    import time

    return CloudAccessSession(
        provider="aws",
        access_key_id=access_key,
        secret_access_key=secret_key,
        session_token=None,
        region=region or config.get("region") or "us-east-1",
        expires_at=time.time() + 86400,
        auth_method=AWS_ACCESS_KEY_AUTH,
    )
