"""
Load signal rule thresholds from JSON configuration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "signal_rules.json"

DEFAULT_RULES: Dict[str, Dict[str, Any]] = {
    "OVER_BUDGET": {
        "enabled": True,
        "warn_threshold_pct": 10.0,
        "critical_threshold_pct": 20.0,
        "confidence": 0.95,
    },
    "UNDER_BUDGET": {
        "enabled": True,
        "min_under_pct": 15.0,
        "confidence": 0.9,
    },
    "COST_SPIKE": {
        "enabled": True,
        "spike_threshold_pct": 25.0,
        "confidence": 0.85,
    },
    "NO_COMMITS_7_DAYS": {
        "enabled": True,
        "confidence": 0.9,
    },
    "NO_COMMITS_14_DAYS": {
        "enabled": True,
        "confidence": 0.92,
    },
    "VELOCITY_DROP": {
        "enabled": True,
        "drop_threshold_pct": 40.0,
        "confidence": 0.85,
    },
    "NO_JIRA_ACTIVITY": {
        "enabled": True,
        "lookback_days": 7,
        "confidence": 0.9,
    },
    "CONNECTOR_FAILURE": {
        "enabled": True,
        "confidence": 0.95,
    },
    "STALE_DATA": {
        "enabled": True,
        "stale_hours": 48,
        "confidence": 0.88,
    },
    "MISSING_OWNER": {
        "enabled": True,
        "confidence": 0.99,
    },
    "UNUSED_CAPACITY": {
        "enabled": True,
        "min_under_pct": 20.0,
        "min_team_size": 2,
        "confidence": 0.8,
    },
    "RESOURCE_IMBALANCE": {
        "enabled": True,
        "imbalance_ratio": 2.5,
        "min_team_size": 3,
        "confidence": 0.82,
    },
    "HIGH_PERFORMING_PROJECT": {
        "enabled": True,
        "min_under_pct": 10.0,
        "min_commits_7d": 5,
        "confidence": 0.78,
    },
    "SLOW_DELIVERY_TREND": {
        "enabled": True,
        "min_drop_pct": 15.0,
        "max_drop_pct": 40.0,
        "confidence": 0.76,
    },
    "BLOCKED_WORK_INCREASE": {
        "enabled": True,
        "min_increase_count": 2,
        "confidence": 0.8,
    },
    "PR_REVIEW_BOTTLENECK": {
        "enabled": True,
        "wait_hours_threshold": 24.0,
        "min_open_prs": 2,
        "confidence": 0.79,
    },
    "HIGH_REOPEN_RATE": {
        "enabled": True,
        "reopen_rate_threshold_pct": 20.0,
        "min_closed_issues_7d": 5,
        "confidence": 0.77,
    },
    "BUILD_FAILURE_TREND": {
        "enabled": True,
        "min_increase_count": 2,
        "confidence": 0.81,
    },
    "RELEASE_INSTABILITY": {
        "enabled": True,
        "failure_rate_threshold_pct": 25.0,
        "min_release_count_7d": 2,
        "confidence": 0.8,
    },
    "DEPENDENCY_CONCENTRATION": {
        "enabled": True,
        "top_share_threshold_pct": 70.0,
        "min_team_size": 2,
        "confidence": 0.74,
    },
    "HIGH_SERVICE_COUPLING": {
        "enabled": True,
        "min_connectors": 4,
        "min_service_count": 4,
        "confidence": 0.73,
    },
    "TECH_DEBT_ACCUMULATION": {
        "enabled": True,
        "min_jira_issues_7d": 5,
        "max_commits_7d": 2,
        "min_issue_to_commit_ratio": 3.0,
        "confidence": 0.78,
    },
    "LOW_THROUGHPUT_PROJECT": {
        "enabled": True,
        "min_under_pct": 10.0,
        "min_team_size": 2,
        "max_commits_per_person_7d": 1.5,
        "confidence": 0.75,
    },
    "STALLED_PROJECT": {
        "enabled": True,
        "min_under_pct": 10.0,
        "min_team_size": 2,
        "confidence": 0.77,
    },
    "MOMENTUM_ACCELERATION": {
        "enabled": True,
        "min_increase_pct": 25.0,
        "min_prior_commits": 2,
        "min_last_commits": 3,
        "confidence": 0.76,
    },
}


def load_signal_rules(config_path: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
    """Load rules from JSON; merge with defaults for missing keys."""
    path = Path(config_path or os.getenv("SIGNAL_RULES_PATH", _DEFAULT_CONFIG_PATH))
    merged = {key: dict(default) for key, default in DEFAULT_RULES.items()}

    if path.is_file():
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        file_rules = payload.get("rules") or payload
        for name, rule in file_rules.items():
            if name in merged and isinstance(rule, dict):
                merged[name].update(rule)

    return merged


def rule_enabled(rules: Dict[str, Dict[str, Any]], signal_type: str) -> bool:
    return bool(rules.get(signal_type, {}).get("enabled", True))


def rule_confidence(rules: Dict[str, Dict[str, Any]], signal_type: str) -> float:
    return float(rules.get(signal_type, {}).get("confidence", 0.8))
