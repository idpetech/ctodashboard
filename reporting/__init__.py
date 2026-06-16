"""CTO Report Generator Agent v1 — executive narrative from analysis JSON only."""

from reporting.agent import CTOReportAgent, ReportAgentError, run_cto_report
from reporting.models import (
    AnalysisInput,
    ArchitectureContext,
    CategoryAnalysis,
    CTOReport,
    ExecutiveSummary,
    KeyFinding,
    Recommendation,
)

__all__ = [
    "AnalysisInput",
    "ArchitectureContext",
    "CategoryAnalysis",
    "CTOReport",
    "CTOReportAgent",
    "ExecutiveSummary",
    "KeyFinding",
    "Recommendation",
    "ReportAgentError",
    "run_cto_report",
]
