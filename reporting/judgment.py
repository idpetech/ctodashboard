"""Shared judgment-hint helpers for reporting sections."""

from __future__ import annotations

from reporting.models import FindingInput
from reporting.templates import FINDING_JUDGMENT_HINTS


def finding_judgment_hint(finding: FindingInput, architecture_pattern: str) -> str:
    for prefix, hint in FINDING_JUDGMENT_HINTS.items():
        if finding.id.startswith(prefix) or prefix in finding.title.lower():
            pattern_hint = hint.get(architecture_pattern) or hint.get("default") or ""
            if pattern_hint:
                return pattern_hint
    if finding.severity in {"critical", "high"}:
        return "Material for this architecture pattern — warrants engineering review."
    if finding.severity == "medium":
        return "Moderate signal for this architecture pattern — validate before refactoring."
    return "Low signal for this architecture pattern — monitor unless it blocks delivery."
