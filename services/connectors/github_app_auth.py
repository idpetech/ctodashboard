"""GitHub App installation token exchange."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Tuple

import jwt
import requests

logger = logging.getLogger(__name__)

_INSTALL_TOKEN_CACHE: Dict[str, Tuple[str, float]] = {}


class GitHubAppConfigError(Exception):
    """GitHub App is not configured."""


def _load_private_key() -> str:
    raw = (os.getenv("GITHUB_APP_PRIVATE_KEY") or "").strip().strip('"').strip("'")
    if not raw:
        raise GitHubAppConfigError("GITHUB_APP_PRIVATE_KEY is not configured")
    key = raw.replace("\\n", "\n").replace("\r", "")
    if "BEGIN" not in key:
        # Paste often omits PEM wrappers — GitHub App keys are RSA PKCS#1.
        body = "".join(line.strip() for line in key.splitlines() if line.strip())
        key = f"-----BEGIN RSA PRIVATE KEY-----\n{body}\n-----END RSA PRIVATE KEY-----"
    return key


def github_app_configured() -> bool:
    return bool(os.getenv("GITHUB_APP_ID") and os.getenv("GITHUB_APP_PRIVATE_KEY"))


def github_app_slug() -> str:
    return (os.getenv("GITHUB_APP_SLUG") or "").strip()


def create_app_jwt() -> str:
    app_id = (os.getenv("GITHUB_APP_ID") or "").strip()
    if not app_id:
        raise GitHubAppConfigError("GITHUB_APP_ID is not configured")
    private_key = _load_private_key()
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": app_id}
    return jwt.encode(payload, private_key, algorithm="RS256")


def _app_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {create_app_jwt()}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "CTOLens-GitHubApp/1.0",
    }


def get_installation(installation_id: str) -> Dict[str, Any]:
    response = requests.get(
        f"https://api.github.com/app/installations/{installation_id}",
        headers=_app_headers(),
        timeout=15,
    )
    if response.status_code == 404:
        raise GitHubAppConfigError(f"GitHub installation {installation_id} not found")
    if response.status_code >= 400:
        body = (response.text or "")[:200]
        raise GitHubAppConfigError(f"GitHub installation lookup failed: {response.status_code} {body}")
    return response.json()


def get_installation_access_token(installation_id: str) -> str:
    cache_key = str(installation_id)
    cached = _INSTALL_TOKEN_CACHE.get(cache_key)
    if cached and cached[1] > time.time() + 60:
        return cached[0]

    response = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=_app_headers(),
        timeout=15,
    )
    if response.status_code >= 400:
        body = (response.text or "")[:200]
        raise GitHubAppConfigError(
            f"GitHub installation token exchange failed: {response.status_code} {body}"
        )
    data = response.json()
    token = data.get("token")
    if not token:
        raise GitHubAppConfigError("GitHub installation token missing from response")

    expires_at = data.get("expires_at")
    expiry_ts = time.time() + 3300
    if expires_at:
        try:
            from datetime import datetime

            expiry_ts = datetime.fromisoformat(expires_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            logger.debug("Could not parse GitHub token expiry: %s", expires_at)

    _INSTALL_TOKEN_CACHE[cache_key] = (token, expiry_ts)
    return token


def installation_account_login(installation: Dict[str, Any]) -> str:
    account = installation.get("account") or {}
    login = account.get("login")
    if not login:
        raise GitHubAppConfigError("GitHub installation account login missing")
    return str(login)


def validate_installation_token(installation_id: str) -> Dict[str, Any]:
    """Test installation by fetching a short-lived token and /installation/repositories."""
    token = get_installation_access_token(installation_id)
    response = requests.get(
        "https://api.github.com/installation/repositories",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "CTOLens-GitHubApp/1.0",
        },
        params={"per_page": 1},
        timeout=15,
    )
    if response.status_code == 401:
        return {"valid": False, "error": "GitHub installation token rejected"}
    if response.status_code >= 400:
        return {"valid": False, "error": f"GitHub API error: {response.status_code}"}
    installation = get_installation(installation_id)
    account = installation.get("account") or {}
    return {
        "valid": True,
        "installation_id": installation_id,
        "account_login": account.get("login"),
        "account_type": account.get("type"),
    }
