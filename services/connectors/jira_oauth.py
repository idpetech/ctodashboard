"""Atlassian OAuth 2.0 (3LO) for Jira Cloud."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

from services.embedded.jira_metrics import normalize_jira_base_url

logger = logging.getLogger(__name__)

ATLASSIAN_AUTH_URL = "https://auth.atlassian.com/authorize"
ATLASSIAN_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ATLASSIAN_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"

DEFAULT_SCOPES = "read:jira-work read:jira-user offline_access"


class JiraOAuthConfigError(Exception):
    """Jira OAuth is not configured."""


def jira_oauth_configured() -> bool:
    return bool(os.getenv("JIRA_OAUTH_CLIENT_ID") and os.getenv("JIRA_OAUTH_CLIENT_SECRET"))


def jira_oauth_client_id() -> str:
    client_id = (os.getenv("JIRA_OAUTH_CLIENT_ID") or "").strip()
    if not client_id:
        raise JiraOAuthConfigError("JIRA_OAUTH_CLIENT_ID is not configured")
    return client_id


def jira_oauth_client_secret() -> str:
    secret = (os.getenv("JIRA_OAUTH_CLIENT_SECRET") or "").strip()
    if not secret:
        raise JiraOAuthConfigError("JIRA_OAUTH_CLIENT_SECRET is not configured")
    return secret


def jira_oauth_scopes() -> str:
    return (os.getenv("JIRA_OAUTH_SCOPES") or DEFAULT_SCOPES).strip()


def build_authorize_url(*, redirect_uri: str, state: str) -> str:
    params = {
        "audience": "api.atlassian.com",
        "client_id": jira_oauth_client_id(),
        "scope": jira_oauth_scopes(),
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"{ATLASSIAN_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(*, code: str, redirect_uri: str) -> Dict[str, Any]:
    response = requests.post(
        ATLASSIAN_TOKEN_URL,
        json={
            "grant_type": "authorization_code",
            "client_id": jira_oauth_client_id(),
            "client_secret": jira_oauth_client_secret(),
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    if response.status_code >= 400:
        body = (response.text or "")[:200]
        raise JiraOAuthConfigError(f"Jira token exchange failed: {response.status_code} {body}")
    return response.json()


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    response = requests.post(
        ATLASSIAN_TOKEN_URL,
        json={
            "grant_type": "refresh_token",
            "client_id": jira_oauth_client_id(),
            "client_secret": jira_oauth_client_secret(),
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    if response.status_code >= 400:
        body = (response.text or "")[:200]
        raise JiraOAuthConfigError(f"Jira token refresh failed: {response.status_code} {body}")
    return response.json()


def list_accessible_resources(access_token: str) -> List[Dict[str, Any]]:
    response = requests.get(
        ATLASSIAN_RESOURCES_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=20,
    )
    if response.status_code >= 400:
        body = (response.text or "")[:200]
        raise JiraOAuthConfigError(f"Jira accessible resources failed: {response.status_code} {body}")
    data = response.json()
    return data if isinstance(data, list) else []


def pick_jira_resource(resources: List[Dict[str, Any]], preferred_url: Optional[str] = None) -> Dict[str, Any]:
    if not resources:
        raise JiraOAuthConfigError("No accessible Jira sites returned for this account")
    if preferred_url:
        normalized = normalize_jira_base_url(preferred_url)
        for resource in resources:
            if normalize_jira_base_url(resource.get("url") or "") == normalized:
                return resource
    for resource in resources:
        if "jira" in (resource.get("scopes") or []):
            return resource
    return resources[0]


def token_expiry_epoch(token_payload: Dict[str, Any]) -> float:
    expires_in = token_payload.get("expires_in")
    if expires_in is None:
        return time.time() + 3300
    try:
        return time.time() + max(0, int(expires_in) - 30)
    except (TypeError, ValueError):
        return time.time() + 3300


def ensure_fresh_access_token(stored: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Return a valid access token and any updated stored fields (refresh token rotation).
    """
    access_token = stored.get("jira_access_token")
    expires_at = stored.get("jira_token_expires_at")
    refresh_token = stored.get("jira_refresh_token")

    if access_token and expires_at:
        try:
            if float(expires_at) > time.time() + 30:
                return access_token, {}
        except (TypeError, ValueError):
            pass

    if not refresh_token:
        raise JiraOAuthConfigError("Jira OAuth refresh token missing — reconnect Jira")

    refreshed = refresh_access_token(refresh_token)
    new_access = refreshed.get("access_token")
    if not new_access:
        raise JiraOAuthConfigError("Jira OAuth refresh did not return access_token")

    updates = {
        "jira_access_token": new_access,
        "jira_token_expires_at": str(token_expiry_epoch(refreshed)),
    }
    if refreshed.get("refresh_token"):
        updates["jira_refresh_token"] = refreshed["refresh_token"]
    return new_access, updates


def jira_api_base(cloud_id: str) -> str:
    return f"https://api.atlassian.com/ex/jira/{cloud_id}"


def validate_oauth_connection(stored: Dict[str, Any]) -> Dict[str, Any]:
    access_token, _updates = ensure_fresh_access_token(stored)
    cloud_id = stored.get("jira_cloud_id")
    if not cloud_id:
        return {"valid": False, "error": "Jira cloud_id missing — reconnect Jira"}

    response = requests.get(
        f"{jira_api_base(cloud_id)}/rest/api/3/myself",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=15,
    )
    if response.status_code == 401:
        return {"valid": False, "error": "Jira OAuth access token rejected — reconnect Jira"}
    if response.status_code >= 400:
        return {"valid": False, "error": f"Jira API error: {response.status_code}"}
    user = response.json()
    return {
        "valid": True,
        "user": user.get("emailAddress") or user.get("displayName"),
        "displayName": user.get("displayName"),
        "accountId": user.get("accountId"),
        "auth_method": "jira_oauth",
    }
