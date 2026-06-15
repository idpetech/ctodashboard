"""Data models for CTO Report Generator Agent v1 (narrative layer only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Mapping, Sequence, Tuple

HealthState = Literal["Healthy", "At Risk", "Critical"]
HEALTH_STATES: Tuple[HealthState, ...] = ("Healthy", "At Risk", "Critical")

FindingCategory = Literal["architecture", "code_health", "delivery", "maintainability"]
FindingSeverity = Literal["low", "medium", "high", "critical"]

FINDING_CATEGORIES: Tuple[FindingCategory, ...] = (
    "architecture",
    "code_health",
    "delivery",
    "maintainability",
)

FINDING_SEVERITIES: Tuple[FindingSeverity, ...] = (
    "low",
    "medium",
    "high",
    "critical",
)


@dataclass(frozen=True)
class FindingInput:
    """Read-only finding row from analysis_result JSON."""

    id: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    evidence: str
    confidence: float
    impact: str
    recommendation: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FindingInput:
        category = str(data.get("category") or "")
        severity = str(data.get("severity") or "")
        if category not in FINDING_CATEGORIES:
            raise ValueError(f"invalid finding category: {category!r}")
        if severity not in FINDING_SEVERITIES:
            raise ValueError(f"invalid finding severity: {severity!r}")
        confidence = float(data.get("confidence") or 0.0)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return cls(
            id=str(data.get("id") or ""),
            category=category,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            title=str(data.get("title") or ""),
            evidence=str(data.get("evidence") or ""),
            confidence=confidence,
            impact=str(data.get("impact") or ""),
            recommendation=str(data.get("recommendation") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnalysisInput:
    """Read-only analysis_result boundary (findings + summary only)."""

    findings: Tuple[FindingInput, ...]
    risk_score: int
    top_risks: Tuple[FindingInput, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AnalysisInput:
        summary = data.get("summary") or {}
        if not isinstance(summary, Mapping):
            raise ValueError("summary must be an object")
        if "risk_score" not in summary:
            raise ValueError("summary.risk_score is required")

        raw_findings = data.get("findings")
        if not isinstance(raw_findings, Sequence) or isinstance(raw_findings, (str, bytes)):
            raise ValueError("findings must be an array")

        findings = tuple(
            FindingInput.from_dict(row) for row in raw_findings if isinstance(row, Mapping)
        )

        raw_top = summary.get("top_risks") or []
        top_risks = tuple(
            FindingInput.from_dict(row) for row in raw_top if isinstance(row, Mapping)
        )

        risk_score = int(summary.get("risk_score") or 0)
        if not 0 <= risk_score <= 100:
            raise ValueError("risk_score must be between 0 and 100")

        return cls(findings=findings, risk_score=risk_score, top_risks=top_risks)


@dataclass(frozen=True)
class ExecutiveSummary:
    overall_health: HealthState
    risk_score: int
    one_line_assessment: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KeyFinding:
    title: str
    severity: FindingSeverity
    business_impact: str
    technical_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Recommendation:
    action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CTOReport:
    executive_summary: ExecutiveSummary
    key_findings: Tuple[KeyFinding, ...]
    risk_breakdown: Dict[str, Dict[str, int]]
    recommendations: Tuple[Recommendation, ...]
    cto_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executive_summary": self.executive_summary.to_dict(),
            "key_findings": [row.to_dict() for row in self.key_findings],
            "risk_breakdown": self.risk_breakdown,
            "recommendations": [row.to_dict() for row in self.recommendations],
            "cto_notes": self.cto_notes,
        }


def health_state_for_risk_score(risk_score: int) -> HealthState:
    if risk_score <= 40:
        return "Healthy"
    if risk_score <= 70:
        return "At Risk"
    return "Critical"
