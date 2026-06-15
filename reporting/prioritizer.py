"""Deterministic finding prioritization for CTO Report Generator v1."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from reporting.models import FindingInput, FindingSeverity

SEVERITY_WEIGHT: dict[FindingSeverity, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

DEFAULT_MAX_FINDINGS = 10
KEY_FINDINGS_LIMIT = 5


class Prioritizer:
    """Sort findings by severity weight, then confidence, then id."""

    def prioritize(
        self,
        findings: Sequence[FindingInput],
        *,
        max_count: int = DEFAULT_MAX_FINDINGS,
    ) -> List[FindingInput]:
        ordered = sorted(findings, key=self._sort_key)
        limit = max(1, min(max_count, DEFAULT_MAX_FINDINGS))
        return ordered[:limit]

    def top_key_findings(self, findings: Sequence[FindingInput]) -> List[FindingInput]:
        return self.prioritize(findings, max_count=KEY_FINDINGS_LIMIT)

    @staticmethod
    def _sort_key(finding: FindingInput) -> Tuple[int, float, str]:
        return (
            -SEVERITY_WEIGHT[finding.severity],
            -round(finding.confidence, 4),
            finding.id,
        )
