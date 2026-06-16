"""Fixed thresholds for deterministic Analysis Layer v1 rules."""

from __future__ import annotations

# Architecture
COUPLING_IMPORTER_THRESHOLD = 5

# Code health
LARGE_SYMBOL_COUNT_THRESHOLD = 30
LOW_COHESION_SYMBOL_THRESHOLD = 20
IMPORT_OVERLOAD_THRESHOLD = 25

# Delivery
BUS_FACTOR_THRESHOLD = 0.6
STALE_COMMITS_30D_THRESHOLD = 1
STALE_MIN_FILE_COUNT = 10
HIGH_CHURN_COMMITS_30D_THRESHOLD = 20
HIGH_CHURN_MAX_FILES_PER_COMMIT = 2.0

# Scorer
SEVERITY_POINTS = {
    "critical": 25,
    "high": 15,
    "medium": 7,
    "low": 2,
}

TOP_RISKS_LIMIT = 5

# v1.1 calibrated scoring — cap contribution per rule family (avoid saturation).
SCORE_CAP_BY_RULE_PREFIX = {
    "architecture.coupling_hotspot": 30,
    "architecture.circular_dependency": 30,
    "architecture.layering_violation": 15,
    "code_health.large_file": 30,
    "code_health.low_cohesion": 14,
    "code_health.import_overload": 15,
    "delivery.bus_factor": 15,
    "delivery.stale_activity": 7,
    "delivery.high_churn_stable_loc": 7,
}

# Scale down bucket totals so multi-rule repos stay in the 0–100 band.
CALIBRATED_SCORE_MULTIPLIER = 0.55
