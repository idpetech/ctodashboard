"""Narrative synthesis for CTO Report Generator v1 (no new analysis)."""

from __future__ import annotations

from typing import Dict, List, Sequence

from reporting.models import (
    ExecutiveSummary,
    FindingInput,
    HealthState,
    KeyFinding,
    Recommendation,
    health_state_for_risk_score,
)
from reporting.templates import (
    CATEGORY_BUSINESS_LABEL,
    CATEGORY_CTO_LABEL,
    CTO_NOTES_TEMPLATE,
    EXECUTIVE_SUMMARY_TEMPLATE,
    RECOMMENDATION_VERBS,
    SEVERITY_BUSINESS_LABEL,
    TITLE_BUSINESS_OVERRIDES,
)


class Synthesizer:
    """Convert analysis findings into executive narrative structures."""

    def build_executive_summary(self, risk_score: int) -> ExecutiveSummary:
        health = health_state_for_risk_score(risk_score)
        one_line = EXECUTIVE_SUMMARY_TEMPLATE.format(
            health_state=health,
            score=risk_score,
        )
        assessment = (
            f"{one_line} Priority should focus on {self._health_focus(health)}."
        )
        return ExecutiveSummary(
            overall_health=health,
            risk_score=risk_score,
            one_line_assessment=assessment,
        )

    def build_key_findings(self, prioritized: Sequence[FindingInput]) -> List[KeyFinding]:
        rows: List[KeyFinding] = []
        for finding in prioritized:
            rows.append(
                KeyFinding(
                    title=self._business_title(finding),
                    severity=finding.severity,
                    business_impact=self._business_impact(finding),
                    technical_summary=self._technical_summary(finding),
                )
            )
        return rows

    def build_recommendations(self, prioritized: Sequence[FindingInput]) -> List[Recommendation]:
        seen: set[str] = set()
        rows: List[Recommendation] = []
        verb_cycle = list(RECOMMENDATION_VERBS)
        verb_index = 0

        for finding in prioritized:
            action = self._recommendation_action(finding, verb_cycle[verb_index % len(verb_cycle)])
            verb_index += 1
            normalized = action.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            rows.append(Recommendation(action=action))

        return rows[:5]

    def build_cto_notes(
        self,
        grouped: Dict[str, List[FindingInput]],
        health: HealthState,
    ) -> str:
        dominant = self._dominant_category(grouped)
        dominant_label = CATEGORY_CTO_LABEL.get(dominant, dominant)
        notes = CTO_NOTES_TEMPLATE.format(dominant_category=dominant_label)
        health_clause = {
            "Healthy": "Current signals are manageable with routine engineering hygiene.",
            "At Risk": "Near-term intervention is recommended to prevent delivery drag.",
            "Critical": "Immediate executive attention is warranted to reduce systemic exposure.",
        }[health]
        return f"{notes} {health_clause}"

    def build_risk_breakdown(
        self,
        grouped: Dict[str, List[FindingInput]],
    ) -> Dict[str, Dict[str, int]]:
        breakdown: Dict[str, Dict[str, int]] = {}
        for category, rows in sorted(grouped.items()):
            counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for row in rows:
                counts[row.severity] += 1
            breakdown[category] = counts
        return breakdown

    @staticmethod
    def _health_focus(health: HealthState) -> str:
        if health == "Healthy":
            return "sustaining quality and predictable delivery"
        if health == "At Risk":
            return "stabilizing architecture and delivery flow"
        return "containing systemic risk and restoring engineering leverage"

    def _business_title(self, finding: FindingInput) -> str:
        lowered = finding.title.strip().lower()
        for key, phrase in TITLE_BUSINESS_OVERRIDES.items():
            if key in lowered:
                return phrase
        category_label = CATEGORY_BUSINESS_LABEL.get(finding.category, finding.category)
        return f"{finding.title} ({category_label})"

    def _business_impact(self, finding: FindingInput) -> str:
        severity_label = SEVERITY_BUSINESS_LABEL.get(finding.severity, finding.severity)
        category_label = CATEGORY_BUSINESS_LABEL.get(finding.category, finding.category)
        impact = finding.impact.strip() or "Engineering change risk may increase."
        return (
            f"This is classified as {severity_label} within {category_label}. "
            f"{impact}"
        )

    @staticmethod
    def _technical_summary(finding: FindingInput) -> str:
        evidence = finding.evidence.strip() or finding.title
        return evidence

    @staticmethod
    def _recommendation_action(finding: FindingInput, verb: str) -> str:
        base = finding.recommendation.strip()
        if not base:
            category = CATEGORY_BUSINESS_LABEL.get(finding.category, "system")
            return f"{verb} {category} risk areas highlighted in {finding.id}."
        lowered = base[:1].lower() + base[1:] if base else base
        if lowered.startswith(tuple(RECOMMENDATION_VERBS)):
            return lowered
        return f"{verb} {lowered}"

    @staticmethod
    def _dominant_category(grouped: Dict[str, List[FindingInput]]) -> str:
        best_category = "architecture"
        best_count = -1
        for category in sorted(grouped.keys()):
            count = len(grouped[category])
            if count > best_count:
                best_category = category
                best_count = count
        return best_category
