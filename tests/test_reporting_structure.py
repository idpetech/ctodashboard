"""Reporting structure tests for architecture context and category analysis."""

from __future__ import annotations

from reporting.agent import CTOReportAgent

SAMPLE = {
    "findings": [
        {
            "id": "architecture.coupling_hotspot.credentials",
            "category": "architecture",
            "severity": "high",
            "title": "High coupling hotspot detected",
            "evidence": "Internal module target 'services/security/credential_service.py' is imported by 20 indexed files (threshold 5).",
            "confidence": 0.9,
            "impact": "Cascade risk",
            "recommendation": "Reduce fan-in via interfaces",
        },
        {
            "id": "code_health.large_file.store",
            "category": "code_health",
            "severity": "high",
            "title": "Large file complexity",
            "evidence": "File 'services/store.py' defines 40 symbols (threshold 30).",
            "confidence": 0.88,
            "impact": "Hard to review",
            "recommendation": "Split module",
        },
    ],
    "summary": {
        "risk_score": 55,
        "top_risks": [],
        "architecture_profile": {
            "pattern": "modular_monolith",
            "pattern_label": "Modular Monolith",
            "confidence": 0.85,
            "summary": "Single deployable with services/ modules.",
            "signals": ["Domain-oriented modules under services/ (120 indexed files)."],
        },
    },
}


def test_report_includes_architecture_context_and_category_analysis():
    report = CTOReportAgent().run(SAMPLE)
    assert report["architecture_context"]["pattern_label"] == "Modular Monolith"
    categories = [row["category"] for row in report["category_analysis"]]
    assert categories == ["architecture", "code_health"]
    assert report["category_analysis"][0]["findings"][0]["judgment_hint"]
    assert report["severity_summary"]["total"] == 2
    assert len(report["risks_by_severity"]) == 4
    high = next(row for row in report["risks_by_severity"] if row["severity"] == "high")
    assert high["count"] == 2
