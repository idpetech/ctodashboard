#!/usr/bin/env python3
"""Offline deterministic checks for CTO Report Generator v1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reporting.agent import CTOReportAgent, ReportAgentError, validate_analysis_result

def _assert_import_allowed(module_name: str, forbidden_roots: tuple[str, ...], file_name: str) -> None:
    lowered = module_name.lower()
    for token in forbidden_roots:
        if lowered == token or lowered.startswith(f"{token}."):
            raise AssertionError(f"forbidden import {module_name!r} in reporting/{file_name}")


SAMPLE = {
    "findings": [
        {
            "id": "architecture.circular_dependency.a",
            "category": "architecture",
            "severity": "high",
            "title": "Circular dependency hint",
            "evidence": "A imports B and B imports A",
            "confidence": 0.8,
            "impact": "Refactor risk",
            "recommendation": "Extract shared contracts",
        },
        {
            "id": "delivery.bus_factor",
            "category": "delivery",
            "severity": "high",
            "title": "Bus factor risk",
            "evidence": "Top contributor 70%",
            "confidence": 0.92,
            "impact": "Concentrated ownership",
            "recommendation": "Spread ownership via pairing",
        },
    ],
    "summary": {"risk_score": 75, "top_risks": []},
}


def main() -> int:
    try:
        validate_analysis_result({"summary": {"risk_score": 1}})
        raise AssertionError("expected validation failure")
    except ReportAgentError:
        pass

    agent = CTOReportAgent()
    first = agent.run(SAMPLE)
    second = agent.run(SAMPLE)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    assert first["executive_summary"]["overall_health"] == "Critical"
    assert len(first["key_findings"]) <= 5
    assert first["cto_notes"]

    # isolation: reporting package must not import pipeline/github layers
    import ast
    import reporting

    forbidden_roots = (
        "github",
        "repo_intelligence",
        "pipeline_loader",
        "repository_store",
        "analysis.pipeline_loader",
        "services.repo_intelligence",
    )
    reporting_dir = Path(reporting.__file__).resolve().parent
    for py_file in reporting_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _assert_import_allowed(alias.name, forbidden_roots, py_file.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                _assert_import_allowed(node.module, forbidden_roots, py_file.name)

    print("PASS: CTO report generator deterministic")
    print(json.dumps(first["executive_summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
