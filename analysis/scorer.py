"""Deterministic risk score aggregation for Analysis Layer v1 / v1.1."""

from __future__ import annotations

from typing import Sequence, Tuple

from analysis.constants import (
    CALIBRATED_SCORE_MULTIPLIER,
    SCORE_CAP_BY_RULE_PREFIX,
    SEVERITY_POINTS,
    TOP_RISKS_LIMIT,
)
from analysis.models import Finding, finding_sort_key


def _rule_prefix(finding_id: str) -> str:
    """Group scored findings by rule family (e.g. architecture.coupling_hotspot)."""
    parts = finding_id.split(".")
    if len(parts) >= 2:
        return ".".join(parts[:2])
    return finding_id


class RiskScorer:
    """Sum severity points (clamped 0–100) and select top risks."""

    def score(
        self,
        findings: Sequence[Finding],
        *,
        strict: bool = False,
    ) -> Tuple[int, Tuple[Finding, ...]]:
        if strict:
            total = sum(SEVERITY_POINTS[finding.severity] for finding in findings)
        else:
            bucket_totals: dict[str, int] = {}
            for finding in findings:
                prefix = _rule_prefix(finding.id)
                cap = SCORE_CAP_BY_RULE_PREFIX.get(prefix, 15)
                points = SEVERITY_POINTS[finding.severity]
                current = bucket_totals.get(prefix, 0)
                bucket_totals[prefix] = min(cap, current + points)
            raw_total = sum(bucket_totals.values())
            total = int(round(raw_total * CALIBRATED_SCORE_MULTIPLIER))

        risk_score = max(0, min(100, total))
        ordered = sorted(findings, key=finding_sort_key)
        top_risks = tuple(ordered[:TOP_RISKS_LIMIT])
        return risk_score, top_risks
