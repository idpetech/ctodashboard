"""Code health rule-based analyzer."""

from __future__ import annotations

from typing import List

from analysis.analyzers._helpers import slug, symbol_count
from analysis.constants import (
    IMPORT_OVERLOAD_THRESHOLD,
    LARGE_SYMBOL_COUNT_THRESHOLD,
    LOW_COHESION_SYMBOL_THRESHOLD,
)
from analysis.models import Finding, PipelineInput


class CodeHealthAnalyzer:
    """Detect large files, low cohesion, and import overload."""

    def analyze(self, pipeline_input: PipelineInput) -> List[Finding]:
        findings: List[Finding] = []
        index = list(pipeline_input.index)
        index.sort(key=lambda row: str(row.get("file_path") or ""))

        for entry in index:
            file_path = str(entry.get("file_path") or "")
            if not file_path:
                continue
            symbols = symbol_count(entry)
            imports = entry.get("imports") or []
            import_count = len(imports) if isinstance(imports, list) else 0
            file_slug = slug(file_path)

            if symbols > LARGE_SYMBOL_COUNT_THRESHOLD:
                findings.append(
                    Finding(
                        id=f"code_health.large_file.{file_slug}",
                        category="code_health",
                        severity="high",
                        title="Large file complexity",
                        evidence=(
                            f"File '{file_path}' defines {symbols} symbols "
                            f"(threshold {LARGE_SYMBOL_COUNT_THRESHOLD})."
                        ),
                        confidence=0.88,
                        impact="Large files are harder to test, review, and change safely.",
                        recommendation="Split responsibilities into smaller focused modules.",
                    )
                )

            if symbols > LOW_COHESION_SYMBOL_THRESHOLD:
                findings.append(
                    Finding(
                        id=f"code_health.low_cohesion.{file_slug}",
                        category="code_health",
                        severity="medium",
                        title="Low cohesion risk",
                        evidence=(
                            f"File '{file_path}' contains {symbols} functions/classes "
                            f"(threshold {LOW_COHESION_SYMBOL_THRESHOLD})."
                        ),
                        confidence=0.8,
                        impact="Multiple responsibilities in one file reduce maintainability.",
                        recommendation="Group related behavior and extract unrelated symbols.",
                    )
                )

            if import_count > IMPORT_OVERLOAD_THRESHOLD:
                findings.append(
                    Finding(
                        id=f"code_health.import_overload.{file_slug}",
                        category="code_health",
                        severity="high",
                        title="High dependency surface",
                        evidence=(
                            f"File '{file_path}' has {import_count} imports "
                            f"(threshold {IMPORT_OVERLOAD_THRESHOLD})."
                        ),
                        confidence=0.87,
                        impact="Broad import surface increases coupling and breakage risk.",
                        recommendation="Reduce direct dependencies; consolidate shared imports.",
                    )
                )

        findings.sort(key=lambda finding: finding.id)
        return findings
