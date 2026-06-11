"""Unit tests for Executive Briefing Generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.executive_briefing.assembler import pre_sort_facts
from services.executive_briefing.feedback import record_recommendation_feedback
from services.executive_briefing.generator import ExecutiveBriefingGenerator
from services.executive_briefing.prompts import SYSTEM_PROMPT
from services.executive_briefing.schema import BriefingInput


class FakeSecureDb:
    def __init__(self):
        self.ws = {"name": "Test", "description": "", "settings": {}}

    def get_workspace(self, workspace_id):
        return self.ws if workspace_id == "ws1" else None

    def store_workspace(self, workspace_id, name, description, settings=None):
        self.ws["settings"] = settings or {}
        return True


class TestAssembler:
    def test_pre_sort_projects_attention_excludes_info_only(self):
        payload = {
            "portfolio_metrics": {},
            "signals": [
                {
                    "signal_type": "UNDER_BUDGET",
                    "severity": "info",
                    "project_name": "A",
                    "description": "under",
                    "confidence": 0.9,
                },
                {
                    "signal_type": "OVER_BUDGET",
                    "severity": "critical",
                    "project_name": "B",
                    "description": "over",
                    "confidence": 0.95,
                },
            ],
            "recommendations": [],
            "data_completeness": {"overall_level": "medium"},
        }
        pre = pre_sort_facts(BriefingInput(**payload))
        names = [p["project_name"] for p in pre["projects_requiring_attention"]]
        assert "B" in names
        assert "A" not in names

    def test_recommended_actions_sorted_by_impact(self):
        payload = {
            "portfolio_metrics": {},
            "signals": [],
            "recommendations": [
                {
                    "recommendation_id": "r1",
                    "title": "Low",
                    "description": "d",
                    "priority": "low",
                    "impact_score": 3,
                    "priority_score": 1,
                    "project_name": "X",
                },
                {
                    "recommendation_id": "r2",
                    "title": "High",
                    "description": "d",
                    "priority": "high",
                    "impact_score": 9,
                    "priority_score": 20,
                    "project_name": "Y",
                },
            ],
            "data_completeness": {},
        }
        pre = pre_sort_facts(BriefingInput(**payload))
        assert pre["recommended_actions"][0]["recommendation_id"] == "r2"


class TestGenerator:
    def test_deterministic_all_sections(self):
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "samples/signals/input_context.json").read_text())
        gen = ExecutiveBriefingGenerator()
        out = gen.generate_from_assignments(
            payload["assignments"],
            delivery_metrics=payload.get("delivery_metrics"),
            connector_metrics=payload.get("connector_metrics"),
            use_ai=False,
        )
        data = out.to_dict()
        assert data["executive_summary"]
        assert isinstance(data["top_risks"], list)
        assert isinstance(data["opportunities"], list)
        assert isinstance(data["recommended_actions"], list)
        assert isinstance(data["projects_requiring_attention"], list)
        assert data["confidence_assessment"]["narrative"]
        assert data["generation_mode"] == "deterministic"

    def test_sample_briefing_output_written(self):
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "samples/signals/input_context.json").read_text())
        out = ExecutiveBriefingGenerator().generate_from_assignments(
            payload["assignments"],
            delivery_metrics=payload.get("delivery_metrics"),
            connector_metrics=payload.get("connector_metrics"),
            use_ai=False,
        )
        out_path = root / "samples/executive_briefing/sample_output.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out.to_dict(), indent=2) + "\n", encoding="utf-8")
        assert out_path.exists()


class TestPromptGuardrails:
    def test_system_prompt_rules(self):
        assert "Do NOT calculate" in SYSTEM_PROMPT
        assert "Do NOT create new recommendations" in SYSTEM_PROMPT
        assert "Use ONLY facts" in SYSTEM_PROMPT


class TestFeedbackLoop:
    def test_record_accept_and_dismiss(self):
        db = FakeSecureDb()
        accepted = record_recommendation_feedback(
            db,
            "ws1",
            recommendation_id="rec:P1:UNDER_BUDGET",
            title="Review unused capacity",
            status="accepted",
        )
        dismissed = record_recommendation_feedback(
            db,
            "ws1",
            recommendation_id="rec:P2:CONNECTOR_FAILURE",
            title="Contact client immediately",
            status="dismissed",
            reason="Client already notified",
        )
        history = db.ws["settings"]["recommendation_feedback"]
        assert len(history) == 2
        assert accepted["status"] == "accepted"
        assert dismissed["reason"] == "Client already notified"

    def test_invalid_status(self):
        db = FakeSecureDb()
        with pytest.raises(ValueError):
            record_recommendation_feedback(
                db,
                "ws1",
                recommendation_id="r1",
                title="T",
                status="maybe",
            )
