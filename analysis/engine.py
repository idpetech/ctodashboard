"""Analysis Layer v1 orchestrator (reads pipeline JSON only)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from analysis.architecture_profile import detect_architecture_profile
from analysis.analyzers.architecture import ArchitectureAnalyzer
from analysis.analyzers.code_health import CodeHealthAnalyzer
from analysis.analyzers.delivery import DeliveryAnalyzer
from analysis.calibration import apply_pattern_severity, calibrate_findings
from analysis.config import is_analysis_strict_mode
from analysis.models import AnalysisResult, AnalysisSummary, ArchitectureProfile, Finding, PipelineInput
from analysis.scorer import RiskScorer


class AnalysisEngineError(ValueError):
    """Raised when pipeline input fails validation."""


class AnalysisEngine:
    """
    Deterministic post-processing orchestrator.

    Reads pipeline_result JSON only — no GitHub, filesystem, database, or LLM calls.
    """

    def __init__(
        self,
        *,
        architecture_analyzer: ArchitectureAnalyzer | None = None,
        code_health_analyzer: CodeHealthAnalyzer | None = None,
        delivery_analyzer: DeliveryAnalyzer | None = None,
        scorer: RiskScorer | None = None,
    ) -> None:
        self._architecture = architecture_analyzer or ArchitectureAnalyzer()
        self._code_health = code_health_analyzer or CodeHealthAnalyzer()
        self._delivery = delivery_analyzer or DeliveryAnalyzer()
        self._scorer = scorer or RiskScorer()

    def run(self, pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
        validated = validate_pipeline_result(pipeline_result)
        pipeline_input = PipelineInput.from_pipeline_result(validated)

        findings: List[Finding] = []
        findings.extend(self._architecture.analyze(pipeline_input))
        findings.extend(self._code_health.analyze(pipeline_input))
        findings.extend(self._delivery.analyze(pipeline_input))

        findings = sorted(findings, key=lambda finding: finding.id)
        strict = is_analysis_strict_mode()
        findings = list(
            calibrate_findings(
                findings,
                strict=strict,
                metrics=pipeline_input.metrics,
                snapshot=pipeline_input.snapshot,
            )
        )
        profile_raw = detect_architecture_profile(pipeline_input)
        architecture_profile = ArchitectureProfile.from_dict(profile_raw)
        findings = list(
            apply_pattern_severity(
                findings,
                architecture_profile.pattern,
                strict=strict,
            )
        )
        risk_score, top_risks = self._scorer.score(findings, strict=strict)

        result = AnalysisResult(
            findings=tuple(findings),
            summary=AnalysisSummary(
                risk_score=risk_score,
                top_risks=top_risks,
                architecture_profile=architecture_profile,
            ),
        )
        return result.to_dict()


def validate_pipeline_result(pipeline_result: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Guardrails before analysis.

    Requires snapshot, index (or code_index), and metrics.
    Rejects missing or wrong-typed required sections.
    """
    if not isinstance(pipeline_result, Mapping):
        raise AnalysisEngineError("pipeline_result must be a JSON object")

    errors: List[str] = []

    snapshot = pipeline_result.get("snapshot")
    if not isinstance(snapshot, Mapping) or not snapshot:
        errors.append("snapshot is required and must be a non-empty object")

    index = pipeline_result.get("index")
    if index is None:
        index = pipeline_result.get("code_index")
    if index is None:
        errors.append("index (or code_index) is required")
    elif not isinstance(index, Sequence) or isinstance(index, (str, bytes)):
        errors.append("index must be an array")

    metrics = pipeline_result.get("metrics")
    if not isinstance(metrics, Mapping) or not metrics:
        errors.append("metrics is required and must be a non-empty object")

    if errors:
        raise AnalysisEngineError("; ".join(errors))

    normalized: Dict[str, Any] = dict(pipeline_result)
    if normalized.get("index") is None:
        normalized["index"] = list(index)  # type: ignore[arg-type]
    return normalized


def run_analysis(pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience wrapper for AnalysisEngine.run()."""
    return AnalysisEngine().run(pipeline_result)
