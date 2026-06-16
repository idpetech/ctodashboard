"""Deterministic architecture pattern classification from pipeline index data."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal, Tuple

from analysis.models import PipelineInput

ArchitecturePattern = Literal["monolith", "modular_monolith", "microservices", "other"]

PATTERN_LABELS: Dict[ArchitecturePattern, str] = {
    "monolith": "Monolith",
    "modular_monolith": "Modular Monolith",
    "microservices": "Microservices / Distributed",
    "other": "Mixed or Undetermined",
}

ENTRY_FILE_NAMES: Tuple[str, ...] = (
    "integrated_dashboard.py",
    "app.py",
    "main.py",
    "wsgi.py",
    "manage.py",
    "server.py",
)


def detect_architecture_profile(pipeline_input: PipelineInput) -> Dict[str, Any]:
    """Infer deployable shape from indexed paths and repo metrics (no external I/O)."""
    paths = _indexed_paths(pipeline_input)
    metrics = pipeline_input.metrics or {}
    repo_size = metrics.get("repo_size") or {}
    total_files = int(repo_size.get("total_files") or pipeline_input.repo.file_count or 0)

    entry_points = [path for path in paths if path.split("/")[-1] in ENTRY_FILE_NAMES]
    entry_roots = sorted({"/".join(path.split("/")[:-1]) or "." for path in entry_points})

    dockerfile_count = sum(
        1 for path in paths if path.lower().endswith("dockerfile") or "/dockerfile" in path.lower()
    )
    compose_count = sum(1 for path in paths if "docker-compose" in path.lower())
    k8s_count = sum(
        1
        for path in paths
        if any(token in path.lower() for token in ("k8s/", "kubernetes/", "helm/", "charts/"))
    )

    services_files = sum(1 for path in paths if path.startswith("services/"))
    routes_files = sum(1 for path in paths if path.startswith("routes/"))
    templates_files = sum(1 for path in paths if path.startswith("templates/"))
    connectors_files = sum(1 for path in paths if path.startswith("connectors/"))

    signals: List[str] = []
    if entry_points:
        primary = sorted(entry_points)[0]
        signals.append(f"Primary application entry detected at {primary}.")
    if services_files:
        signals.append(f"Domain-oriented modules under services/ ({services_files} indexed files).")
    if routes_files:
        signals.append(f"Central HTTP/route layer under routes/ ({routes_files} indexed files).")
    if templates_files:
        signals.append(f"Server-rendered UI under templates/ ({templates_files} indexed files).")
    if dockerfile_count:
        signals.append(f"{dockerfile_count} Dockerfile(s) present in indexed tree.")
    if compose_count:
        signals.append(f"{compose_count} docker-compose manifest(s) present.")
    if k8s_count:
        signals.append(f"{k8s_count} Kubernetes/Helm manifest(s) present.")
    if len(entry_roots) > 1:
        signals.append(f"{len(entry_roots)} distinct application roots with entry files.")

    pattern, confidence, summary = _classify_pattern(
        entry_points=entry_points,
        entry_roots=entry_roots,
        services_files=services_files,
        routes_files=routes_files,
        templates_files=templates_files,
        connectors_files=connectors_files,
        dockerfile_count=dockerfile_count,
        compose_count=compose_count,
        k8s_count=k8s_count,
        total_files=total_files,
    )

    return {
        "pattern": pattern,
        "pattern_label": PATTERN_LABELS[pattern],
        "confidence": round(confidence, 2),
        "summary": summary,
        "signals": tuple(signals[:8]),
    }


def _indexed_paths(pipeline_input: PipelineInput) -> List[str]:
    paths: List[str] = []
    for entry in pipeline_input.index:
        path = str(entry.get("file_path") or "").replace("\\", "/")
        if path:
            paths.append(path)
    return sorted(set(paths))


def _classify_pattern(
    *,
    entry_points: Iterable[str],
    entry_roots: Iterable[str],
    services_files: int,
    routes_files: int,
    templates_files: int,
    connectors_files: int,
    dockerfile_count: int,
    compose_count: int,
    k8s_count: int,
    total_files: int,
) -> Tuple[ArchitecturePattern, float, str]:
    entry_roots_list = list(entry_roots)
    entry_count = len(list(entry_points))

    distributed_score = 0
    if len(entry_roots_list) >= 3:
        distributed_score += 2
    if dockerfile_count >= 3:
        distributed_score += 2
    elif dockerfile_count >= 2:
        distributed_score += 1
    if k8s_count >= 5:
        distributed_score += 2
    elif k8s_count >= 2:
        distributed_score += 1
    if compose_count >= 2:
        distributed_score += 1

    if distributed_score >= 3:
        confidence = min(0.95, 0.65 + distributed_score * 0.08)
        summary = (
            "Multiple deployable units or orchestration manifests suggest a distributed "
            "or microservice-oriented layout rather than a single deployable binary."
        )
        return "microservices", confidence, summary

    modular_score = 0
    if entry_count <= 2:
        modular_score += 1
    if services_files >= 8:
        modular_score += 2
    elif services_files >= 3:
        modular_score += 1
    if routes_files >= 2:
        modular_score += 1
    if templates_files >= 2 or connectors_files >= 2:
        modular_score += 1

    if modular_score >= 4:
        confidence = min(0.92, 0.55 + modular_score * 0.07)
        summary = (
            "Single primary deployable with domain modules (services/, routes/, templates/) "
            "indicates a modular monolith — one runtime, intentionally partitioned code."
        )
        return "modular_monolith", confidence, summary

    if entry_count == 1 and total_files <= 120 and services_files <= 5:
        summary = (
            "Compact codebase with a single entry point and limited module boundaries "
            "reads as a classic monolith."
        )
        return "monolith", 0.72, summary

    if entry_count >= 1 and services_files == 0 and routes_files == 0:
        summary = (
            "Single-application layout without strong domain folders; treat structural findings "
            "as direct maintainability signals."
        )
        return "monolith", 0.6, summary

    summary = (
        "Structure does not clearly match monolith, modular monolith, or microservice patterns. "
        "Use category analysis below and validate assumptions with the team."
    )
    return "other", 0.45, summary
