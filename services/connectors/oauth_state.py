"""Signed OAuth state tokens (CSRF protection for connector installs)."""

from __future__ import annotations

import os
import secrets
from typing import Any, Dict

import jwt


class OAuthStateError(Exception):
    """Invalid or expired OAuth state."""


def _state_secret() -> str:
    secret = os.getenv("OAUTH_STATE_SECRET") or os.getenv("JWT_SECRET")
    if not secret:
        raise OAuthStateError("OAUTH_STATE_SECRET or JWT_SECRET is required for connector OAuth")
    return secret


def build_oauth_state(
    *,
    connector: str,
    workspace_id: str,
    assignment_id: str,
    return_to: str = "dashboard",
    ttl_seconds: int = 900,
) -> str:
    import time

    payload = {
        "purpose": "connector_oauth",
        "connector": connector,
        "workspace_id": workspace_id,
        "assignment_id": assignment_id,
        "return_to": return_to,
        "nonce": secrets.token_urlsafe(16),
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl_seconds,
    }
    return jwt.encode(payload, _state_secret(), algorithm="HS256")


def parse_oauth_state(token: str, *, expected_connector: str) -> Dict[str, Any]:
    if not token:
        raise OAuthStateError("Missing OAuth state")
    try:
        payload = jwt.decode(token, _state_secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise OAuthStateError("Invalid or expired OAuth state") from exc

    if payload.get("purpose") != "connector_oauth":
        raise OAuthStateError("Unexpected OAuth state purpose")
    if payload.get("connector") != expected_connector:
        raise OAuthStateError("OAuth state connector mismatch")
    workspace_id = payload.get("workspace_id")
    assignment_id = payload.get("assignment_id")
    if not workspace_id or not assignment_id:
        raise OAuthStateError("OAuth state missing workspace context")
    return {
        "workspace_id": workspace_id,
        "assignment_id": assignment_id,
        "return_to": payload.get("return_to") or "dashboard",
    }
