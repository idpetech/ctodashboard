"""Static string templates for CTO Report Generator v1."""

from __future__ import annotations

EXECUTIVE_SUMMARY_TEMPLATE = (
    "The system is currently {health_state} with a risk score of {score}."
)

CTO_NOTES_TEMPLATE = (
    "Primary risk is driven by {dominant_category} concerns affecting "
    "system stability and delivery velocity."
)

RECOMMENDATION_VERBS: tuple[str, ...] = (
    "isolate",
    "decouple",
    "simplify",
    "stabilize",
    "modularize",
)

CATEGORY_BUSINESS_LABEL = {
    "architecture": "structural and system design",
    "code_health": "maintainability and code quality",
    "delivery": "execution and delivery velocity",
    "maintainability": "long-term evolution capacity",
}

CATEGORY_CTO_LABEL = {
    "architecture": "architecture",
    "code_health": "code_health",
    "delivery": "delivery",
    "maintainability": "maintainability",
}

SEVERITY_BUSINESS_LABEL = {
    "critical": "system-threatening risk",
    "high": "urgent structural concern",
    "medium": "moderate engineering risk",
    "low": "informational observation",
}

TITLE_BUSINESS_OVERRIDES = {
    "circular dependency hint": (
        "Reciprocal dependencies between components increase systemic change risk"
    ),
    "high coupling hotspot detected": (
        "A shared module is tightly coupled across multiple system boundaries"
    ),
    "controller-to-database layering violation": (
        "Presentation logic has direct persistence coupling"
    ),
    "large file complexity": "Oversized modules elevate maintenance and review cost",
    "low cohesion risk": "Multiple responsibilities are concentrated in single modules",
    "high dependency surface": "Modules depend on an unusually broad set of packages",
    "bus factor risk": "Delivery knowledge is concentrated in a single contributor",
    "stale repository activity": "The codebase shows limited recent engineering activity",
    "high commit frequency with low per-commit churn": (
        "Delivery cadence shows high activity with limited substantive change per commit"
    ),
}
