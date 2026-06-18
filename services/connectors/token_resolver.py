"""Resolve effective connector credentials (manual PAT vs OAuth)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from services.connectors.github_app_auth import get_installation_access_token
from services.connectors.jira_oauth import ensure_fresh_access_token, jira_api_base
from services.connectors.oauth_flags import prefer_oauth_connectors

logger = logging.getLogger(__name__)

GITHUB_APP_AUTH = "github_app"
JIRA_OAUTH_AUTH = "jira_oauth"
MANUAL_AUTH = "manual"


def _auth_method(stored: Dict[str, Any], connector: str) -> str:
    explicit = (stored.get("auth_method") or "").strip().lower()
    if explicit:
        return explicit
    if connector == "github" and stored.get("github_installation_id"):
        return GITHUB_APP_AUTH
    if connector == "jira" and stored.get("jira_refresh_token"):
        return JIRA_OAUTH_AUTH
    return MANUAL_AUTH


def github_auth_method(stored: Dict[str, Any]) -> str:
    return _auth_method(stored, "github")


def jira_auth_method(stored: Dict[str, Any]) -> str:
    return _auth_method(stored, "jira")


def should_use_github_oauth(stored: Dict[str, Any]) -> bool:
    method = github_auth_method(stored)
    if method == GITHUB_APP_AUTH:
        return True
    if method == MANUAL_AUTH:
        return False
    return prefer_oauth_connectors() and bool(stored.get("github_installation_id"))


def should_use_jira_oauth(stored: Dict[str, Any]) -> bool:
    method = jira_auth_method(stored)
    if method == JIRA_OAUTH_AUTH:
        return True
    if method == MANUAL_AUTH:
        return False
    return prefer_oauth_connectors() and bool(stored.get("jira_refresh_token"))


def resolve_github_token(stored: Dict[str, Any]) -> Optional[str]:
    if should_use_github_oauth(stored):
        installation_id = stored.get("github_installation_id")
        if not installation_id:
            return None
        try:
            return get_installation_access_token(str(installation_id))
        except Exception as exc:
            logger.warning("GitHub App token resolution failed: %s", exc)
            return None
    token = stored.get("github_token") or stored.get("token")
    return str(token).strip() if token else None


def resolve_jira_credentials(stored: Dict[str, Any]) -> Dict[str, Optional[str]]:
    if should_use_jira_oauth(stored):
        try:
            access_token, _updates = ensure_fresh_access_token(stored)
            cloud_id = stored.get("jira_cloud_id")
            site_url = stored.get("jira_url") or stored.get("url")
            api_base = jira_api_base(cloud_id) if cloud_id else None
            return {
                "token": access_token,
                "email": None,
                "url": site_url,
                "cloud_id": cloud_id,
                "api_base": api_base,
                "auth_method": JIRA_OAUTH_AUTH,
            }
        except Exception as exc:
            logger.warning("Jira OAuth token resolution failed: %s", exc)
            return {
                "token": None,
                "email": None,
                "url": stored.get("jira_url"),
                "cloud_id": stored.get("jira_cloud_id"),
                "api_base": None,
                "auth_method": JIRA_OAUTH_AUTH,
            }

    return {
        "token": (stored.get("jira_token") or stored.get("token") or "").strip() or None,
        "email": (stored.get("jira_email") or stored.get("email") or "").strip() or None,
        "url": (stored.get("jira_url") or stored.get("url") or "").strip() or None,
        "cloud_id": None,
        "api_base": None,
        "auth_method": MANUAL_AUTH,
    }


def github_credentials_ready(stored: Dict[str, Any]) -> bool:
    org = (stored.get("github_org") or stored.get("org") or "").strip()
    if should_use_github_oauth(stored):
        return bool(stored.get("github_installation_id") and org)
    token = stored.get("github_token") or stored.get("token")
    return bool(token and org)


def jira_credentials_ready(stored: Dict[str, Any]) -> bool:
    if should_use_jira_oauth(stored):
        return bool(stored.get("jira_refresh_token") and stored.get("jira_cloud_id"))
    token = stored.get("jira_token") or stored.get("token")
    email = stored.get("jira_email") or stored.get("email")
    url = stored.get("jira_url") or stored.get("url")
    return bool(token and email and url)
