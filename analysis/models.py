"""Analysis Layer v1 — deterministic models (read-only pipeline JSON in, findings out)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Mapping, Sequence, Tuple

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

_SEVERITY_RANK: Dict[FindingSeverity, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def severity_rank(severity: FindingSeverity) -> int:
    return _SEVERITY_RANK[severity]


def finding_sort_key(finding: Finding) -> Tuple[int, str, str]:
    """Deterministic ordering: severity desc, category asc, id asc."""
    return (-severity_rank(finding.severity), finding.category, finding.id)


@dataclass(frozen=True)
class Finding:
    """A single rule-based observation derived from pipeline data."""

    id: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    evidence: str
    confidence: float
    impact: str
    recommendation: str

    def __post_init__(self) -> None:
        if self.category not in FINDING_CATEGORIES:
            raise ValueError(f"invalid finding category: {self.category!r}")
        if self.severity not in FINDING_SEVERITIES:
            raise ValueError(f"invalid finding severity: {self.severity!r}")
        if not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not self.id.strip():
            raise ValueError("finding id is required")
        if not self.title.strip():
            raise ValueError("finding title is required")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Finding:
        return cls(
            id=str(data.get("id") or ""),
            category=_coerce_category(data.get("category")),
            severity=_coerce_severity(data.get("severity")),
            title=str(data.get("title") or ""),
            evidence=str(data.get("evidence") or ""),
            confidence=float(data.get("confidence") or 0.0),
            impact=str(data.get("impact") or ""),
            recommendation=str(data.get("recommendation") or ""),
        )


@dataclass(frozen=True)
class AnalysisSummary:
    """Aggregated analysis output (numeric risk score + ranked risks)."""

    risk_score: int
    top_risks: Tuple[Finding, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.risk_score, int):
            raise ValueError("risk_score must be an integer")
        if not 0 <= self.risk_score <= 100:
            raise ValueError("risk_score must be between 0 and 100")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "top_risks": [finding.to_dict() for finding in self.top_risks],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AnalysisSummary:
        raw_risks = data.get("top_risks") or []
        top_risks = tuple(Finding.from_dict(row) for row in raw_risks if isinstance(row, Mapping))
        return cls(
            risk_score=int(data.get("risk_score") or 0),
            top_risks=top_risks,
        )


@dataclass(frozen=True)
class AnalysisResult:
    """Complete analysis output for a single pipeline ingest."""

    findings: Tuple[Finding, ...]
    summary: AnalysisSummary

    def to_dict(self) -> Dict[str, Any]:
        ordered = tuple(sorted(self.findings, key=finding_sort_key))
        return {
            "findings": [finding.to_dict() for finding in ordered],
            "summary": self.summary.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AnalysisResult:
        raw_findings = data.get("findings") or []
        findings = tuple(
            Finding.from_dict(row) for row in raw_findings if isinstance(row, Mapping)
        )
        summary_raw = data.get("summary") or {}
        summary = (
            AnalysisSummary.from_dict(summary_raw)
            if isinstance(summary_raw, Mapping)
            else AnalysisSummary(risk_score=0, top_risks=())
        )
        return cls(findings=findings, summary=summary)


@dataclass(frozen=True)
class RepoContext:
    """Minimal repository identity extracted from pipeline_result JSON."""

    snapshot_id: str
    repository_id: str
    repo_full_name: str
    head_commit_sha: str
    file_count: int
    index_eligible: int
    indexed_files: int
    result_fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RepoContext:
        return cls(
            snapshot_id=str(data.get("snapshot_id") or ""),
            repository_id=str(data.get("repository_id") or ""),
            repo_full_name=str(data.get("repo_full_name") or ""),
            head_commit_sha=str(data.get("head_commit_sha") or ""),
            file_count=int(data.get("file_count") or 0),
            index_eligible=int(data.get("index_eligible") or 0),
            indexed_files=int(data.get("indexed_files") or 0),
            result_fingerprint=str(data.get("result_fingerprint") or ""),
        )


@dataclass(frozen=True)
class PipelineInput:
    """
    Read-only view of pipeline output JSON.

    This type is the sole input boundary for Analysis Layer v1. Analyzers must
    only consume fields exposed here — never GitHub, git, filesystem, or DB.
    """

    repo: RepoContext
    snapshot: Dict[str, Any]
    index: Tuple[Dict[str, Any], ...]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo": self.repo.to_dict(),
            "snapshot": dict(self.snapshot),
            "index": [dict(row) for row in self.index],
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_pipeline_result(cls, data: Mapping[str, Any]) -> PipelineInput:
        """Build from PipelineResult.to_dict() or equivalent JSON."""
        repo = RepoContext.from_dict(data)
        snapshot = _copy_mapping(data.get("snapshot"))
        index_raw = data.get("index")
        if index_raw is None:
            index_raw = data.get("code_index")
        index = tuple(_copy_mapping(row) for row in _as_sequence(index_raw))
        metrics = _copy_mapping(data.get("metrics"))
        return cls(repo=repo, snapshot=snapshot, index=index, metrics=metrics)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PipelineInput:
        """Build from nested {repo, snapshot, index, metrics} document."""
        repo_raw = data.get("repo") or {}
        repo = RepoContext.from_dict(repo_raw if isinstance(repo_raw, Mapping) else {})
        snapshot = _copy_mapping(data.get("snapshot"))
        index = tuple(_copy_mapping(row) for row in _as_sequence(data.get("index")))
        metrics = _copy_mapping(data.get("metrics"))
        return cls(repo=repo, snapshot=snapshot, index=index, metrics=metrics)


def _coerce_category(value: Any) -> FindingCategory:
    text = str(value or "").strip()
    if text in FINDING_CATEGORIES:
        return text  # type: ignore[return-value]
    raise ValueError(f"invalid finding category: {value!r}")


def _coerce_severity(value: Any) -> FindingSeverity:
    text = str(value or "").strip()
    if text in FINDING_SEVERITIES:
        return text  # type: ignore[return-value]
    raise ValueError(f"invalid finding severity: {value!r}")


def _copy_mapping(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value[key] for key in sorted(value.keys(), key=str)}


def _as_sequence(value: Any) -> Sequence[Any]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return value
    return ()
