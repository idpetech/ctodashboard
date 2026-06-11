"""Tests for product analytics MVP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from services.analytics import event_tracker as et
from services.analytics.models import ACTIVATION_EVENT, is_analytics_enabled
from services.analytics.session_manager import get_or_create_session


class TestAnalyticsFlag:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("ENABLE_PRODUCT_ANALYTICS", raising=False)
        assert is_analytics_enabled() is False

    def test_enabled_when_env_true(self, monkeypatch):
        monkeypatch.setenv("ENABLE_PRODUCT_ANALYTICS", "true")
        assert is_analytics_enabled() is True


class TestTrackEvent:
    def test_noop_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_PRODUCT_ANALYTICS", "false")
        assert et.track_event("user@example.com", "user_login") is None

    def test_writes_event_and_session(self, monkeypatch):
        monkeypatch.setenv("ENABLE_PRODUCT_ANALYTICS", "true")
        store = MagicMock()
        store.create_session.return_value = "sess-1"
        store.get_session.return_value = None
        store.get_open_session_for_user.return_value = None

        result = et.track_event("user@example.com", "user_login", store=store)
        assert result == {"session_id": "sess-1", "event_name": "user_login"}
        store.insert_event.assert_called_once()
        store.touch_session.assert_called_once()
        store.upsert_user_profile.assert_called_once()

    def test_activation_sets_profile_flag(self, monkeypatch):
        monkeypatch.setenv("ENABLE_PRODUCT_ANALYTICS", "true")
        store = MagicMock()
        store.create_session.return_value = "sess-2"
        store.get_session.return_value = None
        store.get_open_session_for_user.return_value = None

        et.track_event("user@example.com", ACTIVATION_EVENT, store=store)
        assert store.upsert_user_profile.call_args.kwargs["activate"] is True


class TestSessionManager:
    def test_reuses_open_session(self, monkeypatch):
        store = MagicMock()
        now = datetime.now(timezone.utc)
        store.get_open_session_for_user.return_value = {
            "session_id": "open-1",
            "user_id": "user@example.com",
            "last_event_at": now,
        }
        sid = get_or_create_session("user@example.com", store=store)
        assert sid == "open-1"
        store.create_session.assert_not_called()

    def test_expired_session_creates_new(self, monkeypatch):
        monkeypatch.setenv("ANALYTICS_SESSION_TIMEOUT_MINUTES", "30")
        store = MagicMock()
        old = datetime.now(timezone.utc) - timedelta(minutes=45)
        store.get_open_session_for_user.return_value = {
            "session_id": "old-1",
            "user_id": "user@example.com",
            "last_event_at": old,
        }
        store.create_session.return_value = "new-1"
        sid = get_or_create_session("user@example.com", store=store)
        assert sid == "new-1"
        store.end_session.assert_called_once()


class TestActivitySummary:
    def test_summary_shape(self):
        store = MagicMock()
        store.get_user_profile.return_value = {
            "has_activated": True,
            "first_activation_time": datetime(2026, 6, 1, tzinfo=timezone.utc),
            "last_seen": datetime(2026, 6, 5, tzinfo=timezone.utc),
            "first_seen": datetime(2026, 6, 1, tzinfo=timezone.utc),
        }
        store.get_last_session.return_value = {
            "duration_seconds": 120,
            "started_at": datetime(2026, 6, 5, tzinfo=timezone.utc),
            "ended_at": datetime(2026, 6, 5, tzinfo=timezone.utc),
        }
        store.count_user_events.return_value = 10
        store.count_user_sessions.return_value = 3

        et.get_store = lambda: store
        summary = et.get_user_activity_summary("user@example.com")
        assert summary["total_events"] == 10
        assert summary["total_sessions"] == 3
        assert summary["has_activated"] is True
        assert summary["last_session_duration_seconds"] == 120


class TestPlatformQueries:
    def test_platform_summary_aggregates(self, monkeypatch):
        monkeypatch.setenv("ENABLE_PRODUCT_ANALYTICS", "true")
        store = MagicMock()
        store.count_distinct_users_with_events_since.return_value = 5
        store.count_events_since.return_value = 42
        store.avg_session_duration_since.return_value = 180.5
        store.count_user_profiles.return_value = 10
        store.count_activated_users.return_value = 4
        store.count_returning_users_since.return_value = 2
        store.top_events_since.return_value = [{"event_name": "dashboard_view", "count": 12}]

        from services.analytics import queries as q

        q.get_store = lambda: store
        summary = q.get_platform_summary(days=7)
        assert summary["active_users"] == 5
        assert summary["total_events"] == 42
        assert summary["activation_rate"] == 0.4
        assert summary["top_events"][0]["event_name"] == "dashboard_view"

    def test_retention_snapshot_shape(self, monkeypatch):
        monkeypatch.setenv("ENABLE_PRODUCT_ANALYTICS", "true")
        store = MagicMock()
        store.retention_count_for_day.side_effect = lambda day: {
            "cohort_size": 10,
            "returned": 3 if day == 7 else 1,
        }

        from services.analytics import queries as q

        q.get_store = lambda: store
        snap = q.get_retention_snapshot(cohort_days=[1, 7])
        assert "day_1" in snap["cohorts"]
        assert snap["cohorts"]["day_7"]["returned"] == 3


class TestAnonymousPageView:
    def test_track_anonymous_page_view(self, monkeypatch):
        monkeypatch.setenv("ENABLE_PRODUCT_ANALYTICS", "true")
        store = MagicMock()
        store.create_session.return_value = "sess-anon"
        store.get_session.return_value = None
        store.get_open_session_for_user.return_value = None
        monkeypatch.setattr(et, "get_store", lambda: store)

        et.track_anonymous_page_view("/pricing", anonymous_id="abc123")
        store.insert_event.assert_called_once()
        call = store.insert_event.call_args
        assert call.kwargs["event_name"] == "page_view"
        assert call.kwargs["metadata"]["path"] == "/pricing"
        assert call.kwargs["user_id"] == "anon:abc123"

    def test_anonymous_page_view_noop_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_PRODUCT_ANALYTICS", "false")
        store = MagicMock()
        monkeypatch.setattr(et, "get_store", lambda: store)
        et.track_anonymous_page_view("/", anonymous_id="x")
        store.insert_event.assert_not_called()
