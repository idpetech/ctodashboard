"""CTO Report Generator Agent v1 — orchestrator (analysis JSON in, CTO report out)."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from reporting.grouping import GroupingEngine
from reporting.models import AnalysisInput, CTOReport
from reporting.prioritizer import KEY_FINDINGS_LIMIT, Prioritizer
from reporting.synthesizer import Synthesizer


class ReportAgentError(ValueError):
    """Structured validation error for report generation."""


class CTOReportAgent:
    """
    Deterministic narrative layer over analysis_result JSON only.

    Must not access pipeline, GitHub, index, metrics, database, or LLM APIs.
    """

    def __init__(self) -> None:
        self._grouper = GroupingEngine()
        self._prioritizer = Prioritizer()
        self._synthesizer = Synthesizer()

    def run(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        validated = validate_analysis_result(analysis_result)
        analysis_input = AnalysisInput.from_dict(validated)

        grouped = self._grouper.group(list(analysis_input.findings))
        prioritized = self._prioritizer.prioritize(list(analysis_input.findings))
        key_source = self._prioritizer.top_key_findings(prioritized)

        executive_summary = self._synthesizer.build_executive_summary(analysis_input.risk_score)
        key_findings = self._synthesizer.build_key_findings(key_source)
        recommendations = self._synthesizer.build_recommendations(prioritized)
        risk_breakdown = self._synthesizer.build_risk_breakdown(grouped)
        cto_notes = self._synthesizer.build_cto_notes(
            grouped,
            executive_summary.overall_health,
        )

        report = CTOReport(
            executive_summary=executive_summary,
            key_findings=tuple(key_findings),
            risk_breakdown=risk_breakdown,
            recommendations=tuple(recommendations),
            cto_notes=cto_notes,
        )

        output = report.to_dict()
        validate_cto_report(output)
        return output


def validate_analysis_result(analysis_result: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(analysis_result, Mapping):
        raise ReportAgentError("analysis_result must be a JSON object")

    if "findings" not in analysis_result:
        raise ReportAgentError("analysis_result.findings is required")

    summary = analysis_result.get("summary")
    if not isinstance(summary, Mapping):
        raise ReportAgentError("analysis_result.summary is required")
    if "risk_score" not in summary:
        raise ReportAgentError("analysis_result.summary.risk_score is required")

    return dict(analysis_result)


def validate_cto_report(report: Dict[str, Any]) -> None:
    required_top = (
        "executive_summary",
        "key_findings",
        "risk_breakdown",
        "recommendations",
        "cto_notes",
    )
    for key in required_top:
        if key not in report:
            raise ReportAgentError(f"CTO report missing required field: {key}")

    key_findings = report.get("key_findings")
    if not isinstance(key_findings, list):
        raise ReportAgentError("key_findings must be an array")
    if len(key_findings) > KEY_FINDINGS_LIMIT:
        raise ReportAgentError(f"key_findings must contain at most {KEY_FINDINGS_LIMIT} items")

    for row in key_findings:
        if not isinstance(row, dict) or not row.get("severity"):
            raise ReportAgentError("each key finding must include severity")

    summary = report.get("executive_summary") or {}
    if "risk_score" not in summary:
        raise ReportAgentError("executive_summary.risk_score is required")

    if _contains_forbidden_temporal_keys(report):
        raise ReportAgentError("CTO report must not include timestamps")


def run_cto_report(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    return CTOReportAgent().run(analysis_result)


def _contains_forbidden_temporal_keys(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if lowered.endswith("_at") or lowered in {"timestamp", "generated_at", "created_at"}:
                return True
            if _contains_forbidden_temporal_keys(nested):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_forbidden_temporal_keys(item) for item in value)
    return False
