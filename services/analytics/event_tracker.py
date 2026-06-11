"""Track product analytics events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config.logging_config import get_logger
from services.analytics.models import ACTIVATION_EVENT, is_analytics_enabled
from services.analytics.session_manager import end_session, get_or_create_session
from services.analytics.store import AnalyticsStore, get_store

logger = get_logger(__name__)


def track_event(
    user_id: str,
    event_name: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    store: Optional[AnalyticsStore] = None,
) -> Optional[Dict[str, Any]]:
    """
    Record an analytics event. Returns session_id and event_name when written.
    No-op when ENABLE_PRODUCT_ANALYTICS is false.
    """
    if not is_analytics_enabled():
        return None
    if not user_id or not event_name:
        return None

    store = store or get_store()
    try:
        sid = get_or_create_session(user_id, session_id=session_id, store=store)
        now = datetime.now(timezone.utc)
        store.insert_event(
            user_id=user_id,
            session_id=sid,
            event_name=event_name,
            metadata=metadata,
            occurred_at=now,
        )
        store.touch_session(sid, occurred_at=now)
        activate = event_name == ACTIVATION_EVENT
        store.upsert_user_profile(
            user_id,
            seen_at=now,
            activate=activate,
            activation_at=now if activate else None,
        )
        return {"session_id": sid, "event_name": event_name}
    except Exception as exc:
        logger.warning(
            "analytics track_event failed",
            extra={
                "user_id": user_id,
                "event_name": event_name,
                "error": str(exc),
            },
        )
        return None


def track_event_safe(
    user_id: Optional[str],
    event_name: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None
    return track_event(user_id, event_name, session_id=session_id, metadata=metadata)


def track_from_flask(
    event_name: str,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve user/session from Flask request context and track."""
    try:
        from flask import has_request_context
        from flask import session as flask_session

        if not has_request_context():
            return track_event_safe(user_id, event_name, metadata=metadata)

        uid = user_id or flask_session.get("user_email")
        if not uid:
            return None
        sid = flask_session.get("analytics_session_id")
        result = track_event(uid, event_name, session_id=sid, metadata=metadata)
        if result and result.get("session_id"):
            flask_session["analytics_session_id"] = result["session_id"]
        return result
    except Exception as exc:
        logger.warning("analytics track_from_flask failed: %s", exc)
        return None


def get_user_activity_summary(user_id: str) -> Dict[str, Any]:
    store = get_store()
    profile = store.get_user_profile(user_id) or {}
    last_session = store.get_last_session(user_id) or {}
    duration = last_session.get("duration_seconds")
    if duration is None and last_session.get("started_at") and not last_session.get("ended_at"):
        started = last_session["started_at"]
        if hasattr(started, "tzinfo") and started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        duration = max(
            0,
            int((datetime.now(timezone.utc) - started).total_seconds()),
        )
    return {
        "user_id": user_id,
        "total_sessions": store.count_user_sessions(user_id),
        "total_events": store.count_user_events(user_id),
        "last_session_duration_seconds": duration,
        "has_activated": bool(profile.get("has_activated")),
        "first_activation_time": profile.get("first_activation_time"),
        "last_seen": profile.get("last_seen"),
        "first_seen": profile.get("first_seen"),
    }


def track_report_generated(user_id: Optional[str], **metadata: Any) -> None:
    track_event_safe(user_id, ACTIVATION_EVENT, metadata=metadata or None)


def end_flask_session(user_id: Optional[str] = None) -> None:
    try:
        from flask import has_request_context
        from flask import session as flask_session

        if not has_request_context() or not is_analytics_enabled():
            return
        sid = flask_session.get("analytics_session_id")
        if sid:
            end_session(sid)
            flask_session.pop("analytics_session_id", None)
    except Exception as exc:
        logger.warning("analytics end_flask_session failed: %s", exc)


def track_anonymous_page_view(path: str, anonymous_id: Optional[str] = None) -> None:
    """Track public homepage/marketing page views."""
    if not is_analytics_enabled() or not path:
        return
    anon = (anonymous_id or uuid.uuid4().hex[:16]).strip()
    user_id = f"anon:{anon}"
    track_event(user_id, "page_view", metadata={"path": path, "anonymous": True})
