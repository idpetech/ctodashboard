"""CTO Lens product analytics (MVP)."""

from services.analytics.event_tracker import (
    get_user_activity_summary,
    track_event,
    track_event_safe,
    track_from_flask,
    track_report_generated,
)
from services.analytics.models import ACTIVATION_EVENT, is_analytics_enabled
from services.analytics.queries import get_platform_summary, get_retention_snapshot
from services.analytics.session_manager import (
    end_session,
    get_current_session,
    start_session,
)

__all__ = [
    "ACTIVATION_EVENT",
    "end_session",
    "get_current_session",
    "get_platform_summary",
    "get_retention_snapshot",
    "get_user_activity_summary",
    "is_analytics_enabled",
    "start_session",
    "track_event",
    "track_event_safe",
    "track_from_flask",
    "track_report_generated",
]
