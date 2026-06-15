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
