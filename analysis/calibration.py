"""Analysis Layer v1.1 calibration — suppress noisy heuristics, keep real smells."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence, Tuple

from analysis.models import Finding, FindingSeverity

# Modules with high fan-in by design (logging, DB facades, composition roots).
INFRA_COUPLING_PATH_SUFFIXES: Tuple[str, ...] = (
    "logging_config.py",
    "routes/api/deps.py",
    "services/workspace/db_access.py",
    "services/security/db_system.py",
    "services/security/db_registry.py",
    "services/security/db_workspaces.py",
    "services/security/db_credentials.py",
    "services/security/db_users.py",
    "services/security/secure_database.py",
)

# Route/deps modules that are expected to aggregate imports.
COMPOSITION_ROOT_PATH_SUFFIXES: Tuple[str, ...] = (
    "routes/api/deps.py",
)

_SEVERITY_RANK: dict[FindingSeverity, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

_RANK_TO_SEVERITY: dict[int, FindingSeverity] = {
    4: "critical",
    3: "high",
    2: "medium",
    1: "low",
}

# Max severity by finding family once architecture pattern is known.
_PATTERN_SEVERITY_CEILINGS: dict[str, dict[str, FindingSeverity]] = {
    "modular_monolith": {
        "architecture.coupling_hotspot.": "medium",
        "code_health.import_overload.": "medium",
        "code_health.low_cohesion.": "low",
        "delivery.": "medium",
    },
    "monolith": {
        "architecture.coupling_hotspot.": "medium",
        "code_health.import_overload.": "medium",
        "code_health.low_cohesion.": "low",
        "delivery.": "medium",
    },
}


def is_infra_coupling_hotspot(module_hint: str) -> bool:
    normalized = (module_hint or "").replace("\\", "/").lower()
    return any(normalized.endswith(suffix.lower()) for suffix in INFRA_COUPLING_PATH_SUFFIXES)


def is_composition_root(file_path: str) -> bool:
    normalized = (file_path or "").replace("\\", "/").lower()
    return any(normalized.endswith(suffix.lower()) for suffix in COMPOSITION_ROOT_PATH_SUFFIXES)


def _file_path_from_evidence(evidence: str) -> str:
    marker = "File '"
    if marker not in evidence:
        return ""
    start = evidence.index(marker) + len(marker)
    end = evidence.find("'", start)
    if end < 0:
        return ""
    return evidence[start:end]


def _module_hint_from_coupling_evidence(evidence: str) -> str:
    marker = "Internal module target '"
    if marker not in evidence:
        return ""
    start = evidence.index(marker) + len(marker)
    end = evidence.find("'", start)
    if end < 0:
        return ""
    return evidence[start:end]


def _file_slug_from_finding_id(finding_id: str, *, prefix: str) -> str:
    if not finding_id.startswith(prefix):
        return ""
    return finding_id[len(prefix) :]


def _large_file_slugs(findings: Sequence[Finding]) -> frozenset[str]:
    prefix = "code_health.large_file."
    return frozenset(
        _file_slug_from_finding_id(finding.id, prefix=prefix)
        for finding in findings
        if finding.id.startswith(prefix)
    )


def _is_unreliable_churn_metric(metrics: Mapping[str, Any], snapshot: Mapping[str, Any]) -> bool:
    activity = metrics.get("activity") or {}
    churn = float(activity.get("churn_rate_files_per_commit") or 0.0)
    if churn > 0.0:
        return False

    commits = snapshot.get("commits") or []
    if not isinstance(commits, list) or not commits:
        return True

    for row in commits:
        if not isinstance(row, Mapping):
            continue
        if int(row.get("files_changed_count") or 0) > 0:
            return False
    return True


def _contributor_count(metrics: Mapping[str, Any]) -> int:
    contributors = metrics.get("contributors") or {}
    per_contributor = contributors.get("commits_per_contributor") or []
    if not isinstance(per_contributor, list):
        return 0
    return sum(1 for row in per_contributor if isinstance(row, Mapping))


def calibrate_findings(
    findings: Sequence[Finding],
    *,
    strict: bool,
    metrics: Mapping[str, Any] | None = None,
    snapshot: Mapping[str, Any] | None = None,
) -> Tuple[Finding, ...]:
    """
    Post-process analyzer output to reduce false positives.

    When strict=True, returns findings unchanged (Analysis Layer v1 behavior).
    """
    if strict:
        return tuple(findings)

    metrics = metrics or {}
    snapshot = snapshot or {}
    large_slugs = _large_file_slugs(findings)
    suppress_churn = _is_unreliable_churn_metric(metrics, snapshot)
    single_contributor = _contributor_count(metrics) <= 1

    calibrated: list[Finding] = []
    for finding in findings:
        if finding.id.startswith("architecture.coupling_hotspot."):
            module_hint = _module_hint_from_coupling_evidence(finding.evidence)
            if is_infra_coupling_hotspot(module_hint):
                continue

        if finding.id.startswith("code_health.low_cohesion."):
            slug = _file_slug_from_finding_id(finding.id, prefix="code_health.low_cohesion.")
            if slug in large_slugs:
                continue

        if finding.id.startswith("code_health.import_overload."):
            file_path = _file_path_from_evidence(finding.evidence)
            if is_composition_root(file_path):
                continue

        if finding.id == "delivery.bus_factor" and single_contributor:
            continue

        if finding.id == "delivery.high_churn_stable_loc" and suppress_churn:
            continue

        calibrated.append(finding)

    return tuple(calibrated)


def apply_pattern_severity(
    findings: Sequence[Finding],
    architecture_pattern: str,
    *,
    strict: bool,
) -> Tuple[Finding, ...]:
    """
    Adjust finding severity for the detected architecture pattern.

    Severity reflects what is high *for this shape of system*, not raw rule output.
    """
    if strict or architecture_pattern in {"", "other", "microservices"}:
        return tuple(findings)

    ceilings = _PATTERN_SEVERITY_CEILINGS.get(architecture_pattern)
    if not ceilings:
        return tuple(findings)

    adjusted: list[Finding] = []
    for finding in findings:
        ceiling: FindingSeverity | None = None
        for prefix, cap in ceilings.items():
            if finding.id.startswith(prefix):
                ceiling = cap
                break
        if ceiling is None:
            adjusted.append(finding)
            continue
        capped = _cap_severity(finding.severity, ceiling)
        if capped == finding.severity:
            adjusted.append(finding)
        else:
            adjusted.append(replace(finding, severity=capped))
    return tuple(adjusted)


def _cap_severity(severity: FindingSeverity, ceiling: FindingSeverity) -> FindingSeverity:
    capped_rank = min(_SEVERITY_RANK[severity], _SEVERITY_RANK[ceiling])
    return _RANK_TO_SEVERITY[capped_rank]
