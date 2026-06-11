"""Postgres persistence for product analytics."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AnalyticsStore:
    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    def insert_event(
        self,
        *,
        user_id: str,
        session_id: str,
        event_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        occurred_at: Optional[datetime] = None,
    ) -> str:
        event_id = uuid.uuid4().hex
        when = occurred_at or _utc_now()
        meta_json = json.dumps(metadata or {})
        self.adapter.execute_update(
            """
            INSERT INTO analytics_events
                (id, user_id, session_id, event_name, occurred_at, metadata)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            """,
            (event_id, user_id, session_id, event_name, when, meta_json),
        )
        return event_id

    def create_session(self, user_id: str, started_at: Optional[datetime] = None) -> str:
        session_id = str(uuid.uuid4())
        when = started_at or _utc_now()
        self.adapter.execute_update(
            """
            INSERT INTO analytics_sessions
                (session_id, user_id, started_at, last_event_at, event_count)
            VALUES (%s, %s, %s, %s, 0)
            """,
            (session_id, user_id, when, when),
        )
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        rows = self.adapter.execute_query(
            """
            SELECT session_id, user_id, started_at, ended_at, duration_seconds,
                   event_count, last_event_at
            FROM analytics_sessions
            WHERE session_id = %s
            """,
            (session_id,),
        )
        return dict(rows[0]) if rows else None

    def get_open_session_for_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        rows = self.adapter.execute_query(
            """
            SELECT session_id, user_id, started_at, ended_at, duration_seconds,
                   event_count, last_event_at
            FROM analytics_sessions
            WHERE user_id = %s AND ended_at IS NULL
            ORDER BY last_event_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        return dict(rows[0]) if rows else None

    def touch_session(self, session_id: str, occurred_at: Optional[datetime] = None) -> None:
        when = occurred_at or _utc_now()
        self.adapter.execute_update(
            """
            UPDATE analytics_sessions
            SET event_count = event_count + 1,
                last_event_at = %s
            WHERE session_id = %s
            """,
            (when, session_id),
        )

    def end_session(self, session_id: str, ended_at: Optional[datetime] = None) -> None:
        when = ended_at or _utc_now()
        row = self.get_session(session_id)
        if not row or row.get("ended_at"):
            return
        started = row.get("started_at")
        duration = 0
        if started:
            if hasattr(started, "tzinfo") and started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            duration = max(0, int((when - started).total_seconds()))
        self.adapter.execute_update(
            """
            UPDATE analytics_sessions
            SET ended_at = %s,
                duration_seconds = %s
            WHERE session_id = %s AND ended_at IS NULL
            """,
            (when, duration, session_id),
        )

    def upsert_user_profile(
        self,
        user_id: str,
        *,
        seen_at: Optional[datetime] = None,
        activate: bool = False,
        activation_at: Optional[datetime] = None,
    ) -> None:
        when = seen_at or _utc_now()
        if activate:
            self.adapter.execute_update(
                """
                INSERT INTO analytics_user_profiles
                    (user_id, first_seen, last_seen, has_activated, first_activation_time)
                VALUES (%s, %s, %s, TRUE, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    last_seen = EXCLUDED.last_seen,
                    has_activated = CASE
                        WHEN analytics_user_profiles.has_activated THEN TRUE
                        ELSE TRUE
                    END,
                    first_activation_time = COALESCE(
                        analytics_user_profiles.first_activation_time,
                        EXCLUDED.first_activation_time
                    )
                """,
                (user_id, when, when, activation_at or when),
            )
            return

        self.adapter.execute_update(
            """
            INSERT INTO analytics_user_profiles (user_id, first_seen, last_seen)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                last_seen = EXCLUDED.last_seen
            """,
            (user_id, when, when),
        )

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        rows = self.adapter.execute_query(
            """
            SELECT user_id, first_seen, last_seen, has_activated, first_activation_time
            FROM analytics_user_profiles
            WHERE user_id = %s
            """,
            (user_id,),
        )
        return dict(rows[0]) if rows else None

    def count_user_events(self, user_id: str) -> int:
        rows = self.adapter.execute_query(
            "SELECT COUNT(*) AS count FROM analytics_events WHERE user_id = %s",
            (user_id,),
        )
        return int(rows[0]["count"]) if rows else 0

    def count_user_sessions(self, user_id: str) -> int:
        rows = self.adapter.execute_query(
            "SELECT COUNT(*) AS count FROM analytics_sessions WHERE user_id = %s",
            (user_id,),
        )
        return int(rows[0]["count"]) if rows else 0

    def get_last_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        rows = self.adapter.execute_query(
            """
            SELECT session_id, user_id, started_at, ended_at, duration_seconds,
                   event_count, last_event_at
            FROM analytics_sessions
            WHERE user_id = %s
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        return dict(rows[0]) if rows else None

    def count_distinct_users_with_events_since(self, since: datetime) -> int:
        rows = self.adapter.execute_query(
            """
            SELECT COUNT(DISTINCT user_id) AS count
            FROM analytics_events
            WHERE occurred_at >= %s AND user_id NOT LIKE 'anon:%%'
            """,
            (since,),
        )
        return int(rows[0]["count"]) if rows else 0

    def count_events_since(self, since: datetime) -> int:
        rows = self.adapter.execute_query(
            "SELECT COUNT(*) AS count FROM analytics_events WHERE occurred_at >= %s",
            (since,),
        )
        return int(rows[0]["count"]) if rows else 0

    def avg_session_duration_since(self, since: datetime) -> Optional[float]:
        rows = self.adapter.execute_query(
            """
            SELECT AVG(duration_seconds) AS avg_duration
            FROM analytics_sessions
            WHERE started_at >= %s AND duration_seconds IS NOT NULL
            """,
            (since,),
        )
        if not rows or rows[0].get("avg_duration") is None:
            return None
        return round(float(rows[0]["avg_duration"]), 1)

    def count_user_profiles(self) -> int:
        rows = self.adapter.execute_query(
            "SELECT COUNT(*) AS count FROM analytics_user_profiles WHERE user_id NOT LIKE 'anon:%%'"
        )
        return int(rows[0]["count"]) if rows else 0

    def count_activated_users(self) -> int:
        rows = self.adapter.execute_query(
            """
            SELECT COUNT(*) AS count FROM analytics_user_profiles
            WHERE has_activated = TRUE AND user_id NOT LIKE 'anon:%%'
            """
        )
        return int(rows[0]["count"]) if rows else 0

    def count_returning_users_since(self, since: datetime) -> int:
        rows = self.adapter.execute_query(
            """
            SELECT COUNT(*) AS count FROM (
                SELECT user_id
                FROM analytics_events
                WHERE occurred_at >= %s AND user_id NOT LIKE 'anon:%%'
                GROUP BY user_id
                HAVING COUNT(DISTINCT DATE(occurred_at)) >= 2
            ) returning_users
            """,
            (since,),
        )
        return int(rows[0]["count"]) if rows else 0

    def top_events_since(self, since: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        rows = self.adapter.execute_query(
            """
            SELECT event_name, COUNT(*) AS count
            FROM analytics_events
            WHERE occurred_at >= %s
            GROUP BY event_name
            ORDER BY count DESC
            LIMIT %s
            """,
            (since, limit),
        )
        return [{"event_name": r["event_name"], "count": int(r["count"])} for r in rows or []]

    def retention_count_for_day(self, day: int) -> Dict[str, int]:
        rows = self.adapter.execute_query(
            """
            SELECT
                COUNT(*) AS cohort_size,
                COUNT(*) FILTER (
                    WHERE EXISTS (
                        SELECT 1 FROM analytics_events e
                        WHERE e.user_id = p.user_id
                          AND e.occurred_at >= p.first_seen + (%s * INTERVAL '1 day')
                          AND e.occurred_at < p.first_seen + (%s * INTERVAL '1 day')
                    )
                ) AS returned
            FROM analytics_user_profiles p
            WHERE p.first_seen <= NOW() - (%s * INTERVAL '1 day')
              AND p.user_id NOT LIKE 'anon:%%'
            """,
            (day, day + 1, day),
        )
        row = rows[0] if rows else {}
        cohort = int(row.get("cohort_size") or 0)
        returned = int(row.get("returned") or 0)
        return {
            "cohort_size": cohort,
            "returned": returned,
            "rate": round(returned / cohort, 4) if cohort else 0.0,
        }


def get_store() -> AnalyticsStore:
    from services.security.secure_database import secure_db

    return AnalyticsStore(secure_db.adapter)
