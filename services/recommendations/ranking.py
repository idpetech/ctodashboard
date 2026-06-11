"""
Recommendation ranking — Priority Score = Business Impact × Severity × Confidence.
"""

from __future__ import annotations

from typing import Any, Dict

from services.recommendations.models import RecommendationPriority
from services.signals.models import Signal, SignalSeverity


def severity_weight(catalog: Dict[str, Any], severity: SignalSeverity) -> float:
    weights = catalog.get("severity_weights") or {}
    return float(weights.get(severity.value, 1.0))


def compute_priority_score(
    signal: Signal,
    impact_score: int,
    catalog: Dict[str, Any],
) -> float:
    """Priority Score = impact_score × severity_weight × confidence."""
    return (
        float(impact_score) * severity_weight(catalog, signal.severity) * float(signal.confidence)
    )


def classify_priority(priority_score: float, catalog: Dict[str, Any]) -> RecommendationPriority:
    bands = catalog.get("priority_bands") or {}
    high_at = float(bands.get("high", 15.0))
    medium_at = float(bands.get("medium", 8.0))
    if priority_score >= high_at:
        return RecommendationPriority.HIGH
    if priority_score >= medium_at:
        return RecommendationPriority.MEDIUM
    return RecommendationPriority.LOW
