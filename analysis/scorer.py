"""Deterministic risk score aggregation for Analysis Layer v1."""

from __future__ import annotations

from typing import Sequence, Tuple

from analysis.constants import SEVERITY_POINTS, TOP_RISKS_LIMIT
from analysis.models import Finding, finding_sort_key


class RiskScorer:
    """Sum severity points (clamped 0–100) and select top risks."""

    def score(self, findings: Sequence[Finding]) -> Tuple[int, Tuple[Finding, ...]]:
        total = sum(SEVERITY_POINTS[finding.severity] for finding in findings)
        risk_score = max(0, min(100, total))
        ordered = sorted(findings, key=finding_sort_key)
        top_risks = tuple(ordered[:TOP_RISKS_LIMIT])
        return risk_score, top_risks
