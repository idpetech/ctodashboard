"""Product analytics constants and event names."""

from __future__ import annotations

import os

ACTIVATION_EVENT = "report_generated"

EVENT_USER_SIGNUP = "user_signup"
EVENT_USER_LOGIN = "user_login"
EVENT_DASHBOARD_VIEW = "dashboard_view"
EVENT_PAGE_VIEW = "page_view"
EVENT_FEATURE_USED = "feature_used"
EVENT_REPORT_GENERATED = "report_generated"
EVENT_INSIGHT_VIEWED = "insight_viewed"
EVENT_INTEGRATION_CONNECTED = "integration_connected"

DEFAULT_SESSION_TIMEOUT_MINUTES = 30


def is_analytics_enabled() -> bool:
    return os.getenv("ENABLE_PRODUCT_ANALYTICS", "false").lower() == "true"


def session_timeout_minutes() -> int:
    raw = os.getenv("ANALYTICS_SESSION_TIMEOUT_MINUTES", str(DEFAULT_SESSION_TIMEOUT_MINUTES))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_SESSION_TIMEOUT_MINUTES
