"""Session lifecycle for product analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from services.analytics.models import session_timeout_minutes
from services.analytics.store import AnalyticsStore, get_store


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _session_expired(last_event_at: datetime, now: datetime) -> bool:
    timeout = timedelta(minutes=session_timeout_minutes())
    return now - _as_utc(last_event_at) > timeout


def start_session(user_id: str, store: Optional[AnalyticsStore] = None) -> str:
    store = store or get_store()
    return store.create_session(user_id)


def end_session(session_id: str, store: Optional[AnalyticsStore] = None) -> None:
    store = store or get_store()
    store.end_session(session_id)


def get_current_session(
    user_id: str,
    store: Optional[AnalyticsStore] = None,
) -> Optional[Dict[str, Any]]:
    store = store or get_store()
    row = store.get_open_session_for_user(user_id)
    if not row:
        return None
    last_event_at = row.get("last_event_at")
    if not last_event_at:
        return row
    now = datetime.now(timezone.utc)
    if _session_expired(last_event_at, now):
        store.end_session(row["session_id"], ended_at=now)
        return None
    return row


def get_or_create_session(
    user_id: str,
    session_id: Optional[str] = None,
    store: Optional[AnalyticsStore] = None,
) -> str:
    store = store or get_store()
    if session_id:
        row = store.get_session(session_id)
        if row and row.get("user_id") == user_id and not row.get("ended_at"):
            last_event_at = row.get("last_event_at")
            if last_event_at and _session_expired(last_event_at, datetime.now(timezone.utc)):
                store.end_session(session_id)
            else:
                return session_id

    current = get_current_session(user_id, store=store)
    if current:
        return current["session_id"]
    return start_session(user_id, store=store)
