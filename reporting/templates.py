"""Static string templates for CTO Report Generator v1."""

from __future__ import annotations

EXECUTIVE_SUMMARY_TEMPLATE = (
    "The repository reads as a {pattern_label} ({confidence_pct} confidence). "
    "Overall health is {health_state} with a risk score of {score}."
)

ARCHITECTURE_CONTEXT_JUDGMENT = {
    "monolith": (
        "In a monolith, prioritize circular dependencies, oversized modules, and layering "
        "violations over shared-module fan-in alone."
    ),
    "modular_monolith": (
        "In a modular monolith, some shared service hubs are expected. Focus on circular "
        "dependencies, domain hub sprawl, and files that mix unrelated responsibilities."
    ),
    "microservices": (
        "In a distributed layout, coupling across service boundaries and inconsistent deploy "
        "units matter more than in-process fan-in within one service."
    ),
    "other": (
        "Validate the assumed architecture with the team before treating coupling findings as defects."
    ),
}

CATEGORY_DISPLAY_LABEL = {
    "architecture": "Architecture & Structure",
    "code_health": "Code Health & Maintainability",
    "delivery": "Delivery & Team Signals",
    "maintainability": "Long-Term Maintainability",
}

CATEGORY_ANALYSIS_TEMPLATE = (
    "{category_label}: {total} finding(s) — {high_count} high/critical and "
    "{medium_count} medium. Use the judgment hints below to separate expected monolith "
    "patterns from actionable smells."
)

CATEGORY_JUDGMENT_GUIDANCE = {
    "architecture": (
        "Architecture findings describe structural coupling and boundaries. Not every hotspot "
        "requires a refactor — confirm whether the module is an intentional shared facade."
    ),
    "code_health": (
        "Code health findings highlight maintainability pressure. Large or import-heavy files "
        "are usually worth a backlog item even when the system still runs."
    ),
    "delivery": (
        "Delivery findings reflect activity and ownership patterns. Treat bus factor and churn "
        "signals as staffing and process inputs, not code defects."
    ),
    "maintainability": (
        "Maintainability findings capture long-horizon evolution risk. Prioritize items that "
        "block onboarding or repeated incident classes."
    ),
}

PATTERN_CATEGORY_GUIDANCE = {
    "modular_monolith": {
        "architecture": (
            "Shared modules under services/ often show high fan-in by design after refactors."
        ),
    },
    "monolith": {
        "architecture": (
            "A single deployable will naturally centralize imports; weigh layering violations heavily."
        ),
    },
    "microservices": {
        "architecture": (
            "Prioritize cross-service import paths and duplicated deploy entry points."
        ),
    },
}

FINDING_JUDGMENT_HINTS = {
    "architecture.coupling_hotspot.": {
        "default": (
            "Verify whether this is a domain hub, infra facade, or accidental god-module."
        ),
        "modular_monolith": (
            "Rated medium for a modular monolith — shared fan-in is structurally normal. "
            "Escalate only if domain logic accumulates here."
        ),
        "monolith": (
            "Rated medium for a monolith — central imports are expected. "
            "Escalate for layering violations or mixed responsibilities."
        ),
    },
    "architecture.circular_dependency.": {
        "default": "Actionable — reciprocal imports increase refactor and test cost in any pattern.",
    },
    "architecture.layering_violation.": {
        "default": "Actionable — presentation-to-database coupling tends to spread unless bounded early.",
    },
    "code_health.large_file.": {
        "default": "Actionable — split or isolate when the file mixes persistence, orchestration, and UI rules.",
    },
    "code_health.low_cohesion.": {
        "default": "Review — confirm whether symbols belong together or the file is a convenience dump.",
    },
    "code_health.import_overload.": {
        "default": (
            "Contextual — route composition roots may be import-heavy; refactor when business logic grows."
        ),
    },
    "delivery.bus_factor": {
        "default": "Team signal — plan pairing, docs, and backup ownership; not a code architecture defect.",
    },
    "delivery.stale_activity": {
        "default": "Process signal — confirm whether the repo is active, archived, or seasonally idle.",
    },
    "delivery.high_churn_stable_loc": {
        "default": "Review — validate git metadata quality before treating churn as instability.",
    },
    "circular dependency hint": {
        "default": "Actionable — reciprocal imports increase refactor and test cost in any pattern.",
    },
    "high coupling hotspot detected": {
        "default": (
            "Contextual — verify whether this is a domain hub, infra facade, or accidental god-module."
        ),
    },
    "bus factor risk": {
        "default": "Team signal — plan pairing, docs, and backup ownership; not a code architecture defect.",
    },
}

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

SEVERITY_DISPLAY_LABEL = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
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
