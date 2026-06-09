"""Tests for CTOLens briefing pipeline orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from services.briefing_pipeline import (
    get_stored_ctolens_briefing,
    is_ctolens_briefing_enabled,
    run_ctolens_pipeline,
    store_ctolens_briefing,
)


class FakeSecureDb:
    def __init__(self):
        self.ws = {"name": "Test", "description": "", "settings": {}}

    def get_workspace(self, workspace_id):
        return self.ws if workspace_id == "ws1" else None

    def store_workspace(self, workspace_id, name, description, settings=None):
        self.ws["settings"] = settings or {}
        return True


class TestBriefingPipeline:
    def test_run_pipeline_from_sample(self):
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "samples/signals/input_context.json").read_text())
        result = run_ctolens_pipeline(
            "ws1",
            payload["assignments"],
            fetch_metrics=False,
            use_ai=False,
        )
        assert result["executive_briefing"]["executive_summary"]
        assert isinstance(result["signals"], list)
        assert isinstance(result["recommendations"], list)
        assert result["generation_mode"] == "deterministic"

    def test_store_and_load(self):
        db = FakeSecureDb()
        briefing = {"generated_at": "2026-06-08T00:00:00Z", "signals": []}
        assert store_ctolens_briefing(db, "ws1", briefing) is True
        loaded = get_stored_ctolens_briefing(db, "ws1")
        assert loaded["generated_at"] == "2026-06-08T00:00:00Z"

    def test_flag_helper(self):
        assert isinstance(is_ctolens_briefing_enabled(), bool)


class TestBriefingStaleness:
    def test_fingerprint_changes_when_burn_changes(self):
        from services.briefing_pipeline import assess_briefing_staleness, assignments_fingerprint

        base = [{"id": "A", "status": "active", "monthly_burn_rate": 1000}]
        briefing = {
            "generated_at": "2026-06-08T00:00:00Z",
            "source_fingerprint": assignments_fingerprint(base),
        }
        fresh = assess_briefing_staleness(briefing, base)
        assert fresh["is_stale"] is False

        changed = [{"id": "A", "status": "active", "monthly_burn_rate": 2000}]
        stale = assess_briefing_staleness(briefing, changed)
        assert stale["is_stale"] is True

    def test_missing_fingerprint_is_stale(self):
        from services.briefing_pipeline import assess_briefing_staleness

        stale = assess_briefing_staleness({"generated_at": "2026-06-08T00:00:00Z"}, [])
        assert stale["is_stale"] is True
