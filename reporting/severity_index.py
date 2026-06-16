"""All findings grouped by severity for team review."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from reporting.judgment import finding_judgment_hint
from reporting.models import FINDING_SEVERITIES, FindingInput, RiskFindingDetail, RisksBySeveritySection
from reporting.templates import CATEGORY_DISPLAY_LABEL, SEVERITY_DISPLAY_LABEL


class SeverityIndexBuilder:
    """Build complete severity index (every finding, grouped by severity)."""

    def build(
        self,
        findings: Sequence[FindingInput],
        *,
        architecture_pattern: str,
    ) -> Tuple[Dict[str, int], List[RisksBySeveritySection]]:
        details = [
            self._finding_detail(row, architecture_pattern)
            for row in sorted(findings, key=lambda row: (row.category, row.id))
        ]
        summary = self._severity_summary(details)
        sections: List[RisksBySeveritySection] = []
        for severity in FINDING_SEVERITIES:
            rows = [row for row in details if row.severity == severity]
            sections.append(
                RisksBySeveritySection(
                    severity=severity,
                    severity_label=SEVERITY_DISPLAY_LABEL.get(severity, severity.title()),
                    count=len(rows),
                    findings=tuple(rows),
                )
            )
        return summary, sections

    @staticmethod
    def _severity_summary(details: Sequence[RiskFindingDetail]) -> Dict[str, int]:
        counts = {severity: 0 for severity in FINDING_SEVERITIES}
        for row in details:
            counts[row.severity] += 1
        counts["total"] = len(details)
        return counts

    @staticmethod
    def _finding_detail(
        finding: FindingInput,
        architecture_pattern: str,
    ) -> RiskFindingDetail:
        return RiskFindingDetail(
            id=finding.id,
            category=finding.category,
            category_label=CATEGORY_DISPLAY_LABEL.get(finding.category, finding.category),
            title=finding.title,
            severity=finding.severity,
            evidence=finding.evidence,
            impact=finding.impact,
            recommendation=finding.recommendation,
            confidence=round(finding.confidence, 2),
            judgment_hint=finding_judgment_hint(finding, architecture_pattern),
        )
