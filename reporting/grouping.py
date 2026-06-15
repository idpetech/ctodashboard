"""Deterministic finding grouping for CTO Report Generator v1."""

from __future__ import annotations

from typing import Dict, List

from reporting.models import FINDING_CATEGORIES, FindingInput


class GroupingEngine:
    """Group findings by category field only (no inference)."""

    def group(self, findings: List[FindingInput]) -> Dict[str, List[FindingInput]]:
        grouped: Dict[str, List[FindingInput]] = {key: [] for key in FINDING_CATEGORIES}
        for finding in findings:
            grouped[finding.category].append(finding)

        for key in FINDING_CATEGORIES:
            grouped[key].sort(key=lambda row: row.id)
        return grouped
