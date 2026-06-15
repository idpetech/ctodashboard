"""Baseline numerical metrics from repository snapshots (no AI, no insights)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

from services.repo_intelligence.config import (
    BASELINE_METRICS_VERSION,
    loc_bytes_divisor,
    loc_sample_files,
    loc_sample_max_bytes,
)
from services.repo_intelligence.git_analyzer import analyze_activity, analyze_contributors
from services.repo_intelligence.indexer import flatten_snapshot_files
from services.repo_intelligence.language_map import (
    extension_from_path,
    is_binary_extension,
    language_for_extension,
)
from services.repo_intelligence.models.baseline_metrics import (
    BaselineMetrics,
    LanguageShare,
    LocProfileMetrics,
    RepoSizeMetrics,
)
from services.repo_intelligence.snapshot_models import RepositorySnapshot

logger = logging.getLogger(__name__)

ContentFetcher = Callable[[str], bytes]


class BaselineMetricsError(Exception):
    """User-visible baseline metrics error."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _line_count(content: bytes) -> int:
    if not content:
        return 0
    return len(content.splitlines())


def _max_line_length(content: bytes) -> int:
    if not content:
        return 0
    return max((len(line) for line in content.splitlines()), default=0)


def _is_loc_sample_candidate(path: str, size_bytes: int) -> bool:
    if size_bytes <= 0 or size_bytes > loc_sample_max_bytes():
        return False
    ext = extension_from_path(path)
    if is_binary_extension(ext):
        return False
    return language_for_extension(ext) is not None or ext in {
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".xml",
        ".html",
        ".css",
        ".scss",
        ".sh",
    }


def _sample_file_lines(
    files: Sequence[Dict[str, Any]],
    content_fetcher: Optional[ContentFetcher],
) -> Tuple[Dict[str, int], int, int, int]:
    """Return measured lines per path, total sample bytes, max line length."""
    sorted_files = sorted(files, key=lambda row: row.get("path") or "")
    measured_lines_by_path: Dict[str, int] = {}
    sample_bytes = 0
    max_line_length = 0

    if content_fetcher is None:
        return measured_lines_by_path, sample_bytes, max_line_length

    candidates = [
        row
        for row in sorted_files
        if _is_loc_sample_candidate(row.get("path") or "", int(row.get("size_bytes") or 0))
    ]
    for row in candidates[: loc_sample_files()]:
        path = row.get("path") or ""
        git_sha = str(row.get("git_sha") or "")
        if not git_sha:
            continue
        try:
            content = content_fetcher(git_sha)
        except Exception as exc:
            logger.warning("LOC sample skipped for %s: %s", path, exc)
            continue
        lines = _line_count(content)
        if lines <= 0:
            continue
        measured_lines_by_path[path] = lines
        sample_bytes += int(row.get("size_bytes") or 0)
        max_line_length = max(max_line_length, _max_line_length(content))

    return measured_lines_by_path, sample_bytes, max_line_length


def _build_loc_profile(
    measured_lines_by_path: Dict[str, int],
    sample_bytes: int,
    max_line_length: int,
) -> LocProfileMetrics:
    sample_files = len(measured_lines_by_path)
    sample_lines = sum(measured_lines_by_path.values())
    avg_bytes_per_line = round(sample_bytes / sample_lines, 4) if sample_lines > 0 else 0.0
    avg_loc_per_file = round(sample_lines / sample_files, 4) if sample_files > 0 else 0.0

    max_loc_per_file = 0
    max_loc_file_path = ""
    if measured_lines_by_path:
        max_loc_per_file = max(measured_lines_by_path.values())
        tied = [path for path, lines in measured_lines_by_path.items() if lines == max_loc_per_file]
        max_loc_file_path = sorted(tied)[0]

    return LocProfileMetrics(
        sample_files=sample_files,
        avg_bytes_per_line=avg_bytes_per_line,
        avg_loc_per_file=avg_loc_per_file,
        max_loc_per_file=max_loc_per_file,
        max_loc_file_path=max_loc_file_path,
        max_line_length=max_line_length,
    )


def _compute_repo_size(
    files: Sequence[Dict[str, Any]],
    measured_lines_by_path: Dict[str, int],
    loc_profile: LocProfileMetrics,
) -> RepoSizeMetrics:
    sorted_files = sorted(files, key=lambda row: row.get("path") or "")
    avg_bytes_per_line = loc_profile.avg_bytes_per_line
    fallback_divisor = float(loc_bytes_divisor())

    measured_loc = 0
    projected_loc = 0
    measured_files = 0
    projected_files = 0

    for row in sorted_files:
        path = row.get("path") or ""
        size_bytes = int(row.get("size_bytes") or 0)
        if path in measured_lines_by_path:
            measured_loc += measured_lines_by_path[path]
            measured_files += 1
            continue
        if size_bytes <= 0:
            continue
        projected_files += 1
        if avg_bytes_per_line > 0:
            projected_loc += max(1, round(size_bytes / avg_bytes_per_line))
        else:
            projected_loc += max(1, round(size_bytes / fallback_divisor))

    if measured_files > 0 and avg_bytes_per_line > 0:
        method = "sampled_average_bytes_per_line"
    elif measured_files > 0:
        method = "sampled_lines_only"
    else:
        method = f"fixed_divisor_{int(fallback_divisor)}"

    return RepoSizeMetrics(
        total_files=len(sorted_files),
        total_loc=measured_loc + projected_loc,
        measured_loc=measured_loc,
        projected_loc=projected_loc,
        measured_files=measured_files,
        projected_files=projected_files,
        estimation_method=method,
    )


def _language_distribution(files: Sequence[Dict[str, Any]]) -> Dict[str, LanguageShare]:
    counts: Dict[str, int] = {}
    for row in files:
        path = row.get("path") or ""
        ext = extension_from_path(path)
        language = language_for_extension(ext) or "Other"
        counts[language] = counts.get(language, 0) + 1

    total = len(files)
    if total == 0:
        return {}

    shares: Dict[str, LanguageShare] = {}
    for language in sorted(counts):
        count = counts[language]
        percent = round(count / total, 4)
        shares[language] = LanguageShare(file_count=count, percent=percent)
    return shares


def compute_baseline_metrics(
    snapshot: Dict[str, Any],
    *,
    computed_at: Optional[str] = None,
    content_fetcher: Optional[ContentFetcher] = None,
) -> BaselineMetrics:
    snapshot_id = str(snapshot.get("snapshot_id") or "")
    repository = snapshot.get("repository") or {}
    repo_full_name = str(repository.get("full_name") or "")
    reference_iso = str(repository.get("last_synced_at") or _utc_now_iso())

    files = flatten_snapshot_files(snapshot.get("folder_structure") or {})
    commits = snapshot.get("commits") or []

    measured_lines, sample_bytes, max_line_length = _sample_file_lines(files, content_fetcher)
    loc_profile = _build_loc_profile(measured_lines, sample_bytes, max_line_length)
    repo_size = _compute_repo_size(files, measured_lines, loc_profile)

    return BaselineMetrics(
        snapshot_id=snapshot_id,
        repo_full_name=repo_full_name,
        computed_at=computed_at or _utc_now_iso(),
        metrics_version=BASELINE_METRICS_VERSION,
        repo_size=repo_size,
        loc_profile=loc_profile,
        language_distribution=_language_distribution(files),
        contributors=analyze_contributors(commits),
        activity=analyze_activity(commits, reference_iso=reference_iso),
    )


def compute_baseline_metrics_from_model(snapshot: RepositorySnapshot) -> BaselineMetrics:
    return compute_baseline_metrics(snapshot.to_dict())


def _github_content_fetcher(token: str, owner: str, repo: str) -> ContentFetcher:
    from services.repo_intelligence.github_client import GitHubRepoClient

    client = GitHubRepoClient(token)

    def fetch(git_sha: str) -> bytes:
        content, _size = client.get_blob_content(owner, repo, git_sha)
        return content

    return fetch


def build_and_store_baseline_metrics(snapshot_id: str, workspace_id: str) -> Dict[str, Any]:
    from services.auth.credential_service import CredentialService
    from services.repo_intelligence.metrics_store import get_metrics_store
    from services.repo_intelligence.store import get_store

    record = get_store().get_snapshot(snapshot_id)
    if not record or record.get("workspace_id") != workspace_id:
        raise BaselineMetricsError("Snapshot not found")
    if record.get("status") != "completed":
        raise BaselineMetricsError("Snapshot is not completed")

    payload = record.get("payload") or {}
    repository = payload.get("repository") or {}
    full_name = str(repository.get("full_name") or record.get("repo_full_name") or "")
    content_fetcher: Optional[ContentFetcher] = None

    assignment_id = record.get("assignment_id")
    if assignment_id and "/" in full_name:
        creds = CredentialService().get_github_credentials(workspace_id, assignment_id)
        token = creds.get("token")
        if token:
            owner, repo_name = full_name.split("/", 1)
            content_fetcher = _github_content_fetcher(token, owner, repo_name)

    metrics = compute_baseline_metrics(payload, content_fetcher=content_fetcher)
    get_metrics_store().save_metrics(snapshot_id, metrics.to_dict())
    return metrics.to_dict()
