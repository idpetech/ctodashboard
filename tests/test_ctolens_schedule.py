"""CTOLens scheduled enrichment due-time filtering (Act 3 Phase A)."""

from datetime import datetime, timezone

from services.ctolens_run_metadata import should_run_enriched_now


def _dt(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


def test_manual_only_never_runs():
    due, reason = should_run_enriched_now(
        {"enabled": True, "frequency": "manual_only", "time_utc": "06:00"},
        None,
        now_utc=_dt(2026, 6, 12, 7),
    )
    assert due is False
    assert reason == "schedule_disabled"


def test_daily_before_scheduled_time_skips():
    due, reason = should_run_enriched_now(
        {"enabled": True, "frequency": "daily", "time_utc": "06:00"},
        None,
        now_utc=_dt(2026, 6, 12, 5, 30),
    )
    assert due is False
    assert reason == "before_scheduled_time"


def test_daily_due_after_scheduled_time():
    due, reason = should_run_enriched_now(
        {"enabled": True, "frequency": "daily", "time_utc": "06:00"},
        None,
        now_utc=_dt(2026, 6, 12, 6, 15),
    )
    assert due is True
    assert reason == "due"


def test_daily_idempotent_same_window():
    due, reason = should_run_enriched_now(
        {"enabled": True, "frequency": "daily", "time_utc": "06:00"},
        "2026-06-12T06:30:00Z",
        now_utc=_dt(2026, 6, 12, 7),
    )
    assert due is False
    assert reason == "already_ran_this_window"


def test_weekly_wrong_day_skips():
    due, reason = should_run_enriched_now(
        {
            "enabled": True,
            "frequency": "weekly",
            "time_utc": "06:00",
            "day_of_week": "monday",
        },
        None,
        now_utc=_dt(2026, 6, 12, 7),
    )
    assert due is False
    assert reason == "wrong_weekday"


def test_weekly_runs_on_matching_day():
    due, reason = should_run_enriched_now(
        {
            "enabled": True,
            "frequency": "weekly",
            "time_utc": "06:00",
            "day_of_week": "friday",
        },
        None,
        now_utc=_dt(2026, 6, 12, 6, 30),
    )
    assert due is True
    assert reason == "due"
