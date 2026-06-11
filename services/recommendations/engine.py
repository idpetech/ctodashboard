"""
CTOLens Recommendation Engine — signals in, ranked recommendations out.

Deterministic. No LLM. Fully explainable via structured rationale.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from services.recommendations.catalog import get_catalog_entry, load_recommendation_catalog
from services.recommendations.models import Recommendation, RecommendationRationale
from services.recommendations.ranking import classify_priority, compute_priority_score
from services.signals.models import Signal


class RecommendationEngine:
    """Convert Signal objects into ranked executive recommendations."""

    def __init__(self, catalog_path: str | Path | None = None):
        self._catalog = load_recommendation_catalog(catalog_path)

    @property
    def catalog(self) -> dict:
        return self._catalog

    def recommend(self, signals: List[Signal]) -> List[Recommendation]:
        recommendations: List[Recommendation] = []
        for signal in signals:
            rec = self._signal_to_recommendation(signal)
            if rec is not None:
                recommendations.append(rec)
        return self._sort_recommendations(recommendations)

    def _signal_to_recommendation(self, signal: Signal) -> Optional[Recommendation]:
        entry = get_catalog_entry(self._catalog, signal.signal_type.value)
        if not entry:
            return None

        impact_score = int(entry["impact_score"])
        effort_score = int(entry["effort_score"])
        priority_score = compute_priority_score(signal, impact_score, self._catalog)

        description = str(entry["description"]).format(
            project_name=signal.project_name,
            metric_value=signal.metric_value,
            threshold=signal.threshold,
        )

        supporting_metrics = {
            "signal_type": signal.signal_type.value,
            "severity": signal.severity.value,
            "confidence": signal.confidence,
            "metric_value": signal.metric_value,
            "threshold": signal.threshold,
            "signal_description": signal.description,
        }

        rationale = RecommendationRationale(
            triggering_signals=[signal.signal_id],
            supporting_metrics=supporting_metrics,
            business_rationale=str(entry["business_rationale"]),
        )

        return Recommendation(
            recommendation_id=Recommendation.make_id(signal.project_id, signal.signal_type.value),
            title=str(entry["title"]),
            description=description,
            category=str(entry.get("category") or signal.category.value),
            priority=classify_priority(priority_score, self._catalog),
            impact_score=impact_score,
            effort_score=effort_score,
            project_name=signal.project_name,
            project_id=signal.project_id,
            source_signal_ids=[signal.signal_id],
            rationale=rationale,
            priority_score=priority_score,
        )

    @staticmethod
    def _sort_recommendations(items: List[Recommendation]) -> List[Recommendation]:
        priority_rank = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            items,
            key=lambda r: (
                -r.priority_score,
                priority_rank.get(r.priority.value, 9),
                -r.impact_score,
                r.project_name,
                r.recommendation_id,
            ),
        )
