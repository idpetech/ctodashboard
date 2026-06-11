"""Tests for CTOLens run metadata helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.ctolens_run_metadata import (
    append_run_log,
    assess_extended_staleness,
    build_diagnostics_payload,
    filter_signals_for_run_mode,
    normalize_schedule,
    strip_briefing_for_export,
    validate_schedule,
)
from services.signals.models import Signal, SignalCategory, SignalSeverity


class TestScheduleNormalization:
    def test_manual_only_disables_enabled_flag(self):
        schedule = normalize_schedule(
            {"enabled": True, "frequency": "manual_only", "on_import": True}
        )
        assert schedule["enabled"] is False
        assert schedule["frequency"] == "manual_only"
        assert schedule["on_import"] is True

    def test_validate_schedule_rejects_bad_frequency(self):
        try:
            validate_schedule({"frequency": "hourly", "day_of_week": "monday"})
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "frequency" in str(exc)


class TestRunLog:
    def test_append_run_log_caps_at_ten(self):
        settings = {"ctolens_run_log": [{"run_id": str(i)} for i in range(12)]}
        log = append_run_log(settings, {"run_id": "new"})
        assert len(log) == 10
        assert log[0]["run_id"] == "new"


class TestExportStrip:
    def test_strip_briefing_for_export_removes_internal_keys(self):
        briefing = {
            "generated_at": "2026-06-08T00:00:00Z",
            "executive_briefing": {"top_risks": []},
            "signals": [{"severity": "critical"}],
            "diagnostics": {"run_id": "abc"},
            "run_id": "abc",
            "connector_runs": [],
            "signals_evaluated_count": 1,
            "signals_shown_count": 0,
        }
        stripped = strip_briefing_for_export(briefing)
        assert "signals" not in stripped
        assert "diagnostics" not in stripped
        assert "run_id" not in stripped
        assert stripped["executive_briefing"]


class TestSignalFiltering:
    def test_filter_signals_drops_delivery_without_metrics(self):
        from services.signals.models import SignalType

        delivery = Signal(
            signal_id="p1:NO_COMMITS_7_DAYS",
            category=SignalCategory.DELIVERY,
            severity=SignalSeverity.WARNING,
            confidence=0.9,
            project_id="p1",
            project_name="Alpha",
            title="No commits",
            description="Slow delivery",
            metric_value=None,
            threshold=None,
            generated_at="2026-06-08T00:00:00Z",
            signal_type=SignalType.NO_COMMITS_7_DAYS,
        )
        financial = Signal(
            signal_id="p1:OVER_BUDGET",
            category=SignalCategory.FINANCIAL,
            severity=SignalSeverity.CRITICAL,
            confidence=0.95,
            project_id="p1",
            project_name="Alpha",
            title="Over budget",
            description="Over budget",
            metric_value=120.0,
            threshold=100.0,
            generated_at="2026-06-08T00:00:00Z",
            signal_type=SignalType.OVER_BUDGET,
        )
        filtered = filter_signals_for_run_mode([delivery, financial], fetch_metrics=False)
        assert len(filtered) == 1
        assert filtered[0].category == SignalCategory.FINANCIAL


class TestExtendedStaleness:
    def test_metrics_stale_after_seven_days(self):
        old = (datetime.now(timezone.utc) - timedelta(days=8)).replace(microsecond=0)
        iso = old.isoformat().replace("+00:00", "Z")
        briefing = {"generated_at": iso, "metrics_fetched": True}
        run_status = {"last_enriched_run_at": iso}
        result = assess_extended_staleness(briefing, [], run_status)
        assert result["metrics_stale"] is True
        assert result["is_stale"] is True


class TestDiagnosticsPayload:
    def test_build_diagnostics_payload_counts(self):
        briefing = {
            "run_id": "run1",
            "signals": [{"id": "s1"}, {"id": "s2"}],
            "executive_briefing": {
                "top_risks": [{"severity": "critical"}],
                "opportunities": [{"summary": "ship faster"}],
            },
        }
        payload = build_diagnostics_payload(briefing, {"last_run_id": "run1"}, [])
        assert payload["signals_evaluated_count"] == 2
        assert payload["signals_shown_count"] == 2
        assert payload["run_id"] == "run1"
