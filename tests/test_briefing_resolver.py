"""Tests for briefing resolver / export normalization."""

from __future__ import annotations

import json
from pathlib import Path

from services.briefing_resolver import is_ctolens_briefing, normalize_briefing_for_export


class TestBriefingResolver:
    def test_normalize_ctolens_sample(self):
        root = Path(__file__).resolve().parents[1]
        sample = json.loads((root / "samples/executive_briefing/sample_output.json").read_text())
        briefing = {
            "generated_at": "2026-06-08T00:00:00Z",
            "executive_briefing": sample,
            "signals": [],
            "portfolio_metrics": {"health_score": {"overall_score": 56, "band": "critical"}},
        }
        assert is_ctolens_briefing(briefing)
        view = normalize_briefing_for_export(briefing)
        assert view["risk_signals"]
        assert view["recommended_actions"]
        assert view["cto_narrative"]
        assert view["top_recommendations_export"]


class TestReportShareContext:
    def test_build_report_includes_all_ctolens_sections(self):
        from services.report_share_service import build_report_template_context

        root = Path(__file__).resolve().parents[1]
        sample = json.loads((root / "samples/executive_briefing/sample_output.json").read_text())
        briefing = {
            "generated_at": "2026-06-08T00:00:00Z",
            "generation_mode": "deterministic",
            "executive_briefing": sample,
            "signals": [{"severity": "critical", "project_name": "Alpha", "description": "Over budget"}],
            "portfolio_metrics": {"health_score": {"overall_score": 56, "band": "critical"}, "summary": {}},
        }
        ctx = build_report_template_context({"briefing": briefing, "portfolio_name": "Demo"})
        assert ctx["narrative"]
        assert ctx["all_risks"]
        assert ctx["all_opportunities"]
        assert ctx["recommended_actions"]
        assert ctx["projects_requiring_attention"]
        assert ctx["confidence_assessment"]["narrative"]
