"""Tests for executive success criteria (Layer 3 deterministic focus)."""

from __future__ import annotations

import json
from pathlib import Path

from services.executive_briefing.assembler import build_briefing_input, pre_sort_facts
from services.executive_briefing.generator import ExecutiveBriefingGenerator
from services.executive_briefing.success_criteria import build_executive_focus


class TestSuccessCriteria:
    def test_five_questions_from_sample(self):
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "samples/signals/input_context.json").read_text())
        out = ExecutiveBriefingGenerator().generate_from_assignments(
            payload["assignments"],
            delivery_metrics=payload.get("delivery_metrics"),
            connector_metrics=payload.get("connector_metrics"),
            use_ai=False,
        )
        focus = out.executive_focus
        assert focus.biggest_risk
        assert focus.biggest_opportunity
        assert focus.do_first
        assert focus.why_first_action
        assert focus.confidence_summary

    def test_actions_include_traceability(self):
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "samples/signals/input_context.json").read_text())
        out = ExecutiveBriefingGenerator().generate_from_assignments(
            payload["assignments"],
            delivery_metrics=payload.get("delivery_metrics"),
            connector_metrics=payload.get("connector_metrics"),
            use_ai=False,
        )
        assert out.recommended_actions
        top = out.recommended_actions[0]
        assert top.why
        assert top.source_signal_ids

    def test_pre_sort_includes_executive_focus(self):
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "samples/signals/input_context.json").read_text())
        from services.recommendations.engine import RecommendationEngine
        from services.signals.engine import SignalEngine

        signals = SignalEngine().evaluate_assignments(
            payload["assignments"],
            delivery_metrics=payload.get("delivery_metrics"),
            connector_metrics=payload.get("connector_metrics"),
        )
        recs = RecommendationEngine().recommend(signals)
        briefing_input = build_briefing_input(
            payload["assignments"],
            [s.to_dict() for s in signals],
            [r.to_dict() for r in recs],
        )
        pre = pre_sort_facts(briefing_input)
        focus = build_executive_focus(pre, briefing_input.data_completeness)
        assert pre.get("executive_focus")
        assert focus.do_first
