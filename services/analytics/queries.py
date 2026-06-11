"""Analytics aggregate and retention queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from services.analytics.store import get_store


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _since_days(days: int) -> datetime:
    return _utc_now() - timedelta(days=days)


def get_platform_summary(days: int = 7) -> Dict[str, Any]:
    """Admin dashboard metrics for the last N days."""
    store = get_store()
    since = _since_days(days)
    active_users = store.count_distinct_users_with_events_since(since)
    total_events = store.count_events_since(since)
    avg_duration = store.avg_session_duration_since(since)
    total_profiles = store.count_user_profiles()
    activated = store.count_activated_users()
    activation_rate = round(activated / total_profiles, 4) if total_profiles else 0.0
    returning_users = store.count_returning_users_since(since)
    top_events = store.top_events_since(since, limit=10)

    return {
        "period_days": days,
        "active_users": active_users,
        "total_events": total_events,
        "avg_session_duration_seconds": avg_duration,
        "activation_rate": activation_rate,
        "activated_users": activated,
        "tracked_users": total_profiles,
        "returning_users": returning_users,
        "top_events": top_events,
    }


def get_retention_snapshot(cohort_days: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Day-N return counts: users whose first_seen was at least N days ago
    and who had an event on day N after first_seen (calendar-day buckets).
    """
    cohort_days = cohort_days or [1, 7, 30]
    store = get_store()
    cohorts: Dict[str, Any] = {}
    for day in cohort_days:
        cohorts[f"day_{day}"] = store.retention_count_for_day(day)
    return {"cohorts": cohorts, "computed_at": _utc_now().isoformat().replace("+00:00", "Z")}
