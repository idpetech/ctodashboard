"""Ephemeral cloud access sessions (never persisted)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CloudAccessSession:
    """Short-lived credentials obtained from a cloud provider broker."""

    provider: str
    access_key_id: str
    secret_access_key: str
    session_token: Optional[str]
    region: str
    expires_at: float
    auth_method: str
    account_id: Optional[str] = None
    role_arn: Optional[str] = None
