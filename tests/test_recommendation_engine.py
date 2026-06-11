"""Unit tests for CTOLens Recommendation Engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.executive_briefing.assembler import OPPORTUNITY_SIGNAL_TYPES
from services.recommendations.engine import RecommendationEngine
from services.recommendations.models import RecommendationPriority
from services.recommendations.ranking import classify_priority, compute_priority_score
from services.signals.engine import SignalEngine
from services.signals.models import Signal, SignalCategory, SignalSeverity, SignalType

# Opportunity signals surfaced in briefing only until catalog entries are added.
OPPORTUNITY_ONLY_SIGNAL_TYPES = OPPORTUNITY_SIGNAL_TYPES - {
    "UNDER_BUDGET",
    "UNUSED_CAPACITY",
    "HIGH_PERFORMING_PROJECT",
}


def _signal(**kwargs) -> Signal:
    defaults = dict(
        signal_id="P1:UNDER_BUDGET",
        category=SignalCategory.FINANCIAL,
        severity=SignalSeverity.INFO,
        confidence=0.9,
        project_id="P1",
        project_name="Project One",
        title="Under budget",
        description="Monthly burn 15000 is below target 20000 by 25.0%.",
        metric_value=-25.0,
        threshold=-15.0,
        generated_at="2026-06-07T12:00:00Z",
        signal_type=SignalType.UNDER_BUDGET,
    )
    defaults.update(kwargs)
    return Signal(**defaults)


class TestRanking:
    def test_priority_score_formula(self):
        signal = _signal(confidence=0.9, severity=SignalSeverity.INFO)
        catalog = RecommendationEngine().catalog
        score = compute_priority_score(signal, impact_score=6, catalog=catalog)
        assert score == pytest.approx(6 * 1.0 * 0.9)

    def test_critical_severity_weights_higher(self):
        catalog = RecommendationEngine().catalog
        critical = _signal(severity=SignalSeverity.CRITICAL, confidence=0.95)
        warning = _signal(severity=SignalSeverity.WARNING, confidence=0.95)
        assert compute_priority_score(critical, 8, catalog) > compute_priority_score(
            warning, 8, catalog
        )

    def test_priority_bands(self):
        catalog = RecommendationEngine().catalog
        assert classify_priority(20.0, catalog) == RecommendationPriority.HIGH
        assert classify_priority(10.0, catalog) == RecommendationPriority.MEDIUM
        assert classify_priority(3.0, catalog) == RecommendationPriority.LOW


class TestRecommendationMapping:
    @pytest.mark.parametrize(
        "signal_type,expected_title_fragment",
        [
            (SignalType.UNDER_BUDGET, "unused capacity"),
            (SignalType.NO_COMMITS_14_DAYS, "Verify project status"),
            (SignalType.CONNECTOR_FAILURE, "Restore connector"),
            (SignalType.RESOURCE_IMBALANCE, "Rebalance"),
        ],
    )
    def test_catalog_examples(self, signal_type, expected_title_fragment):
        signal = _signal(
            signal_id=f"P1:{signal_type.value}",
            signal_type=signal_type,
            category=SignalCategory.FINANCIAL,
        )
        recs = RecommendationEngine().recommend([signal])
        assert len(recs) == 1
        assert (
            expected_title_fragment.lower() in recs[0].title.lower()
            or expected_title_fragment.lower() in recs[0].description.lower()
        )

    def test_all_signal_types_have_catalog_entries(self):
        engine = RecommendationEngine()
        for signal_type in SignalType:
            if signal_type.value in OPPORTUNITY_ONLY_SIGNAL_TYPES:
                continue
            assert signal_type.value in engine.catalog["recommendations"]

    def test_explainability_fields(self):
        signal = _signal()
        rec = RecommendationEngine().recommend([signal])[0]
        data = rec.to_dict()
        assert rec.source_signal_ids == [signal.signal_id]
        assert signal.signal_id in data["rationale"]["triggering_signals"]
        assert data["rationale"]["supporting_metrics"]["metric_value"] == -25.0
        assert data["rationale"]["business_rationale"]
        assert len(data["rationale"]["business_rationale"]) > 10

    def test_ranked_output_order(self):
        signals = [
            _signal(
                signal_id="A:OVER_BUDGET",
                signal_type=SignalType.OVER_BUDGET,
                severity=SignalSeverity.CRITICAL,
                confidence=0.95,
                metric_value=30.0,
            ),
            _signal(
                signal_id="B:MISSING_OWNER",
                signal_type=SignalType.MISSING_OWNER,
                severity=SignalSeverity.INFO,
                confidence=0.99,
            ),
        ]
        recs = RecommendationEngine().recommend(signals)
        assert recs[0].priority_score >= recs[1].priority_score

    def test_sample_pipeline_output(self):
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "samples/signals/input_context.json").read_text())
        signals = SignalEngine().evaluate_assignments(
            payload["assignments"],
            delivery_metrics=payload.get("delivery_metrics"),
            connector_metrics=payload.get("connector_metrics"),
        )
        engine = RecommendationEngine()
        recs = engine.recommend(signals)
        catalog_types = set(engine.catalog["recommendations"])
        mappable_signals = [s for s in signals if s.signal_type.value in catalog_types]
        out = {
            "recommendation_count": len(recs),
            "recommendations": [r.to_dict() for r in recs],
        }
        out_path = root / "samples/recommendations/output_recommendations.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        assert len(recs) == len(mappable_signals)
        assert all(r.rationale.triggering_signals for r in recs)
