"""
CTOLens Recommendation Engine — domain model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class RecommendationPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class RecommendationRationale:
    """Explainability payload — no LLM; derived from signals and catalog."""

    triggering_signals: List[str]
    supporting_metrics: Dict[str, Any]
    business_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggering_signals": list(self.triggering_signals),
            "supporting_metrics": dict(self.supporting_metrics),
            "business_rationale": self.business_rationale,
        }


@dataclass(frozen=True)
class Recommendation:
    recommendation_id: str
    title: str
    description: str
    category: str
    priority: RecommendationPriority
    impact_score: int
    effort_score: int
    project_name: str
    source_signal_ids: List[str]
    rationale: RecommendationRationale
    priority_score: float = field(repr=True)
    project_id: str = field(default="", repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority.value,
            "impact_score": self.impact_score,
            "effort_score": self.effort_score,
            "project_name": self.project_name,
            "project_id": self.project_id,
            "source_signal_ids": list(self.source_signal_ids),
            "rationale": self.rationale.to_dict(),
            "priority_score": round(self.priority_score, 4),
        }

    @staticmethod
    def make_id(project_id: str, signal_type: str) -> str:
        return f"rec:{project_id}:{signal_type}"
