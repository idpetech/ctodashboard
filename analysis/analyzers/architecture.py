"""Architecture rule-based analyzer."""

from __future__ import annotations

from collections import Counter
from typing import List, Mapping, Sequence

from analysis.analyzers._helpers import (
    importer_targets_file,
    internal_imports,
    module_path_hint,
    path_segments,
    slug,
)
from analysis.constants import COUPLING_IMPORTER_THRESHOLD
from analysis.models import Finding, PipelineInput


class ArchitectureAnalyzer:
    """Detect coupling, layering violations, and circular import hints."""

    def analyze(self, pipeline_input: PipelineInput) -> List[Finding]:
        findings: List[Finding] = []
        index = list(pipeline_input.index)
        index.sort(key=lambda row: str(row.get("file_path") or ""))

        findings.extend(self._dependency_concentration(index))
        findings.extend(self._layering_violations(index))
        findings.extend(self._circular_dependency_hints(index))
        findings.sort(key=lambda finding: finding.id)
        return findings

    def _dependency_concentration(self, index: Sequence[Mapping[str, object]]) -> List[Finding]:
        importer_counts: Counter[str] = Counter()
        for entry in index:
            for item in internal_imports(entry):
                hint = module_path_hint(str(item.get("module") or ""))
                if hint:
                    importer_counts[hint] += 1

        findings: List[Finding] = []
        for hint, count in sorted(importer_counts.items()):
            if count < COUPLING_IMPORTER_THRESHOLD:
                continue
            findings.append(
                Finding(
                    id=f"architecture.coupling_hotspot.{slug(hint)}",
                    category="architecture",
                    severity="high",
                    title="High coupling hotspot detected",
                    evidence=(
                        f"Internal module target '{hint}' is imported by "
                        f"{count} indexed files (threshold {COUPLING_IMPORTER_THRESHOLD})."
                    ),
                    confidence=0.9,
                    impact="Changes to this module may cascade across many dependents.",
                    recommendation="Reduce fan-in via interfaces, facades, or module splits.",
                )
            )
        return findings

    def _layering_violations(self, index: Sequence[Mapping[str, object]]) -> List[Finding]:
        findings: List[Finding] = []
        for entry in index:
            file_path = str(entry.get("file_path") or "")
            segments = set(path_segments(file_path))
            if "controller" not in segments and "controllers" not in segments:
                continue

            for item in internal_imports(entry):
                module = str(item.get("module") or "").lower()
                if "database" in module or "db" == module.split(".")[-1]:
                    findings.append(
                        Finding(
                            id=f"architecture.layering_violation.{slug(file_path)}",
                            category="architecture",
                            severity="high",
                            title="Controller-to-database layering violation",
                            evidence=(
                                f"File '{file_path}' is under a controller path and "
                                f"imports '{item.get('module')}' directly."
                            ),
                            confidence=0.85,
                            impact="Presentation layer is coupled to persistence details.",
                            recommendation="Route database access through a service or repository layer.",
                        )
                    )
                    break
        return findings

    def _circular_dependency_hints(self, index: Sequence[Mapping[str, object]]) -> List[Finding]:
        findings: List[Finding] = []
        paths = [str(entry.get("file_path") or "") for entry in index]
        paths = [path for path in paths if path]

        for left_idx, left_path in enumerate(paths):
            left_entry = index[left_idx]
            for right_idx in range(left_idx + 1, len(paths)):
                right_path = paths[right_idx]
                right_entry = index[right_idx]
                left_to_right = importer_targets_file(left_entry, right_path)
                right_to_left = importer_targets_file(right_entry, left_path)
                if not (left_to_right and right_to_left):
                    continue
                pair_id = slug(f"{left_path}_and_{right_path}")
                findings.append(
                    Finding(
                        id=f"architecture.circular_dependency.{pair_id}",
                        category="architecture",
                        severity="high",
                        title="Circular dependency hint",
                        evidence=(
                            f"'{left_path}' imports '{right_path}' and "
                            f"'{right_path}' imports '{left_path}' (internal imports)."
                        ),
                        confidence=0.8,
                        impact="Circular dependencies increase change risk and test difficulty.",
                        recommendation="Extract shared contracts or invert one dependency direction.",
                    )
                )
        return findings
