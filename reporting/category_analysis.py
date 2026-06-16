"""Category-level narrative and judgment guidance for CTO reports."""

from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from reporting.judgment import finding_judgment_hint
from reporting.models import CategoryAnalysis, CategoryFindingDetail, FindingInput
from reporting.templates import (
    CATEGORY_ANALYSIS_TEMPLATE,
    CATEGORY_DISPLAY_LABEL,
    CATEGORY_JUDGMENT_GUIDANCE,
    PATTERN_CATEGORY_GUIDANCE,
)


class CategoryAnalysisBuilder:
    """Build per-category sections with findings and judgment hints."""

    CATEGORY_ORDER = ("architecture", "code_health", "delivery", "maintainability")

    def build(
        self,
        grouped: Dict[str, List[FindingInput]],
        *,
        architecture_pattern: str,
    ) -> List[CategoryAnalysis]:
        sections: List[CategoryAnalysis] = []
        for category in self.CATEGORY_ORDER:
            rows = grouped.get(category) or []
            if not rows:
                continue
            counts = self._severity_counts(rows)
            sections.append(
                CategoryAnalysis(
                    category=category,
                    category_label=CATEGORY_DISPLAY_LABEL.get(category, category),
                    finding_count=len(rows),
                    severity_counts=counts,
                    assessment=self._category_assessment(category, counts, len(rows)),
                    judgment_guidance=self._category_judgment_guidance(category, architecture_pattern),
                    findings=tuple(self._category_findings(rows, architecture_pattern)),
                )
            )
        return sections

    @staticmethod
    def _severity_counts(rows: Sequence[FindingInput]) -> Dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for row in rows:
            counts[row.severity] += 1
        return counts

    @staticmethod
    def _category_assessment(category: str, counts: Mapping[str, int], total: int) -> str:
        high_signal = counts["critical"] + counts["high"]
        medium_signal = counts["medium"]
        label = CATEGORY_DISPLAY_LABEL.get(category, category)
        return CATEGORY_ANALYSIS_TEMPLATE.format(
            category_label=label,
            total=total,
            high_count=high_signal,
            medium_count=medium_signal,
        )

    @staticmethod
    def _category_judgment_guidance(category: str, architecture_pattern: str) -> str:
        pattern_guidance = PATTERN_CATEGORY_GUIDANCE.get(architecture_pattern, {}).get(category, "")
        base = CATEGORY_JUDGMENT_GUIDANCE.get(category, "")
        if pattern_guidance and base:
            return f"{base} {pattern_guidance}"
        return pattern_guidance or base

    def _category_findings(
        self,
        rows: Sequence[FindingInput],
        architecture_pattern: str,
    ) -> List[CategoryFindingDetail]:
        ordered = sorted(rows, key=lambda row: (-self._severity_rank(row.severity), row.id))
        return [
            CategoryFindingDetail(
                id=row.id,
                title=row.title,
                severity=row.severity,
                evidence=row.evidence,
                impact=row.impact,
                recommendation=row.recommendation,
                judgment_hint=finding_judgment_hint(row, architecture_pattern),
            )
            for row in ordered
        ]

    @staticmethod
    def _severity_rank(severity: str) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 0)
