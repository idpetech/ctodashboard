"""Feature flags for connector OAuth (GitHub App + Jira 3LO)."""

from __future__ import annotations

import os


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() == "true"


def github_app_connector_enabled() -> bool:
    return _flag("ENABLE_GITHUB_APP_CONNECTOR")


def jira_oauth_connector_enabled() -> bool:
    return _flag("ENABLE_JIRA_OAUTH_CONNECTOR")


def connector_oauth_ui_enabled() -> bool:
    return _flag("ENABLE_CONNECTOR_OAUTH_UI")


def prefer_oauth_connectors() -> bool:
    return _flag("PREFER_OAUTH_CONNECTORS")


def manual_connector_tokens_disabled() -> bool:
    return _flag("DISABLE_MANUAL_TOKENS")


def oauth_capabilities() -> dict:
    """Public-safe capability map for UI and /api/feature-flags."""
    gh_app = github_app_connector_enabled()
    jira_oauth = jira_oauth_connector_enabled()
    ui = connector_oauth_ui_enabled()
    return {
        "github_app_connector": gh_app,
        "jira_oauth_connector": jira_oauth,
        "connector_oauth_ui": ui,
        "prefer_oauth_connectors": prefer_oauth_connectors(),
        "disable_manual_tokens": manual_connector_tokens_disabled(),
        "github_oauth_ui": gh_app and ui,
        "jira_oauth_ui": jira_oauth and ui,
        "github_oauth_available": gh_app and ui and bool(os.getenv("GITHUB_APP_ID")),
        "jira_oauth_available": jira_oauth and ui and bool(os.getenv("JIRA_OAUTH_CLIENT_ID")),
    }
