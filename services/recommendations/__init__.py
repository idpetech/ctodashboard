"""
CTOLens Recommendation Engine — ranked executive actions from signals.

Catalog: config/recommendation_catalog.json
Upstream: services.signals.SignalEngine
"""

from services.recommendations.engine import RecommendationEngine
from services.recommendations.models import (
    Recommendation,
    RecommendationPriority,
    RecommendationRationale,
)
from services.recommendations.ranking import classify_priority, compute_priority_score

__all__ = [
    "Recommendation",
    "RecommendationEngine",
    "RecommendationPriority",
    "RecommendationRationale",
    "classify_priority",
    "compute_priority_score",
]
