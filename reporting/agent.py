"""CTO Report Generator Agent v1 — orchestrator (analysis JSON in, CTO report out)."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from reporting.category_analysis import CategoryAnalysisBuilder
from reporting.grouping import GroupingEngine
from reporting.models import AnalysisInput, CTOReport
from reporting.prioritizer import KEY_FINDINGS_LIMIT, Prioritizer
from reporting.severity_index import SeverityIndexBuilder
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
        self._category_builder = CategoryAnalysisBuilder()
        self._severity_index = SeverityIndexBuilder()

    def run(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        validated = validate_analysis_result(analysis_result)
        analysis_input = AnalysisInput.from_dict(validated)

        grouped = self._grouper.group(list(analysis_input.findings))
        prioritized = self._prioritizer.prioritize(list(analysis_input.findings))
        key_source = self._prioritizer.top_key_findings(prioritized)

        architecture_context = self._synthesizer.build_architecture_context(
            analysis_input.architecture_profile
        )
        executive_summary = self._synthesizer.build_executive_summary(
            analysis_input.risk_score,
            architecture_context,
        )
        severity_summary, risks_by_severity = self._severity_index.build(
            analysis_input.findings,
            architecture_pattern=architecture_context.pattern,
        )
        key_findings = self._synthesizer.build_key_findings(key_source)
        category_analysis = self._category_builder.build(
            grouped,
            architecture_pattern=architecture_context.pattern,
        )
        recommendations = self._synthesizer.build_recommendations(prioritized)
        risk_breakdown = self._synthesizer.build_risk_breakdown(grouped)
        cto_notes = self._synthesizer.build_cto_notes(
            grouped,
            executive_summary.overall_health,
            architecture_context,
        )

        report = CTOReport(
            architecture_context=architecture_context,
            executive_summary=executive_summary,
            severity_summary=severity_summary,
            risks_by_severity=tuple(risks_by_severity),
            key_findings=tuple(key_findings),
            category_analysis=tuple(category_analysis),
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
        "architecture_context",
        "executive_summary",
        "severity_summary",
        "risks_by_severity",
        "key_findings",
        "category_analysis",
        "risk_breakdown",
        "recommendations",
        "cto_notes",
    )
    for key in required_top:
        if key not in report:
            raise ReportAgentError(f"CTO report missing required field: {key}")

    architecture_context = report.get("architecture_context") or {}
    if not isinstance(architecture_context, dict) or not architecture_context.get("pattern"):
        raise ReportAgentError("architecture_context.pattern is required")

    severity_summary = report.get("severity_summary") or {}
    if not isinstance(severity_summary, dict) or "total" not in severity_summary:
        raise ReportAgentError("severity_summary.total is required")

    risks_by_severity = report.get("risks_by_severity")
    if not isinstance(risks_by_severity, list):
        raise ReportAgentError("risks_by_severity must be an array")

    listed_total = sum(
        int((section or {}).get("count") or 0)
        for section in risks_by_severity
        if isinstance(section, dict)
    )
    if listed_total != int(severity_summary.get("total") or 0):
        raise ReportAgentError("risks_by_severity count must match severity_summary.total")

    category_analysis = report.get("category_analysis")
    if not isinstance(category_analysis, list):
        raise ReportAgentError("category_analysis must be an array")

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
