"""Deterministic CTO Lens repo ingestion pipeline (no LLM / agents / analysis)."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence

from db.models import RepositoryQuery
from db.repository_store import RepositoryStore, get_repository_store
from services.repo_intelligence.github_client import GitHubRepoClient, GitHubRepoClientError
from services.repo_intelligence.indexer import (
    build_code_index_from_snapshot,
    flatten_snapshot_files,
    summarize_index_eligibility,
)
from services.repo_intelligence.metrics_engine import (
    _github_content_fetcher,
    compute_baseline_metrics,
)
from services.repo_intelligence.models.code_index import FileCodeIndex
from services.repo_intelligence.snapshot_models import RepositorySnapshot
from services.repo_intelligence.snapshot_service import build_repository_snapshot, parse_repo_input

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """User-visible ingestion pipeline error."""


@dataclass
class PipelineOptions:
    """Runtime options for a single ingest run."""

    persist: bool = True
    skip_index: bool = False
    skip_metrics: bool = False
    force_new_snapshot: bool = False
    snapshot_id: Optional[str] = None
    # Future incremental ingest: when set, only these paths are code-indexed.
    changed_paths: Optional[Sequence[str]] = None


@dataclass
class PipelineResult:
    """Structured output from a completed pipeline run."""

    snapshot_id: str
    repository_id: str
    repo_full_name: str
    head_commit_sha: str
    file_count: int
    index_eligible: int
    indexed_files: int
    persisted: bool
    reused_snapshot: bool
    result_fingerprint: str
    snapshot: Dict[str, Any] = field(default_factory=dict)
    files: List[Dict[str, Any]] = field(default_factory=list)
    code_index: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _resolve_head_sync_timestamp(snapshot: RepositorySnapshot) -> str:
    """Use HEAD commit timestamp so re-runs at the same commit share the same sync time."""
    head = snapshot.repository.head_commit_sha
    for commit in snapshot.commits:
        if commit.hash == head and commit.timestamp:
            return commit.timestamp
    return snapshot.repository.last_synced_at


def _normalize_snapshot_timestamps(snapshot: RepositorySnapshot) -> RepositorySnapshot:
    synced_at = _resolve_head_sync_timestamp(snapshot)
    if synced_at == snapshot.repository.last_synced_at:
        return snapshot
    metadata = replace(snapshot.repository, last_synced_at=synced_at)
    return RepositorySnapshot(
        snapshot_id=snapshot.snapshot_id,
        repository=metadata,
        folder_structure=snapshot.folder_structure,
        commits=snapshot.commits,
        status=snapshot.status,
        snapshot_version=snapshot.snapshot_version,
    )


def _filter_files_for_incremental(
    files: List[Dict[str, Any]],
    changed_paths: Optional[Sequence[str]],
) -> List[Dict[str, Any]]:
    if not changed_paths:
        return files
    allowed = set(changed_paths)
    return [row for row in files if row.get("path") in allowed]


def _find_snapshot_by_head_commit(
    store: RepositoryStore,
    *,
    workspace_id: str,
    assignment_id: str,
    repository_id: str,
    head_commit_sha: str,
) -> Optional[str]:
    candidates = store.list_snapshots(
        RepositoryQuery(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            repository_id=repository_id,
        ),
        limit=200,
        status="completed",
    )
    for row in candidates:
        if row.head_commit_sha == head_commit_sha:
            return row.snapshot_id
    return None


def _result_fingerprint(
    *,
    snapshot: Dict[str, Any],
    files: List[Dict[str, Any]],
    code_index: List[Dict[str, Any]],
    metrics: Dict[str, Any],
) -> str:
    payload = {
        "head_commit_sha": (snapshot.get("repository") or {}).get("head_commit_sha"),
        "file_count": len(files),
        "indexed_files": len(code_index),
        "metrics_version": metrics.get("metrics_version"),
        "total_loc": (metrics.get("repo_size") or {}).get("total_loc"),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class RepoIngestionPipeline:
    """
    Orchestrates: snapshot → file list → code index → baseline metrics → persist.

    Idempotent: for the same repository HEAD commit, re-runs upsert into the same
    snapshot row (unless force_new_snapshot=True).
    """

    def __init__(self, store: Optional[RepositoryStore] = None) -> None:
        self._store = store or get_repository_store()

    def run(
        self,
        token: str,
        repo_input: str,
        *,
        workspace_id: str,
        assignment_id: str,
        options: Optional[PipelineOptions] = None,
    ) -> PipelineResult:
        opts = options or PipelineOptions()
        client = GitHubRepoClient(token)
        owner, repo_name = parse_repo_input(repo_input)
        full_name = f"{owner}/{repo_name}"

        repository_id = ""
        snapshot_id = opts.snapshot_id or ""
        reused_snapshot = False

        try:
            head_commit_sha = client.get_branch_commit_sha(
                owner,
                repo_name,
                client.get_repo(owner, repo_name).get("default_branch") or "main",
            )
        except GitHubRepoClientError as exc:
            raise PipelineError(str(exc)) from exc

        if opts.persist:
            repo = self._store.upsert_repository(
                workspace_id=workspace_id,
                assignment_id=assignment_id,
                owner=owner,
                repo_name=repo_name,
                repo_full_name=full_name,
            )
            repository_id = repo.repository_id

            if not opts.force_new_snapshot:
                existing = _find_snapshot_by_head_commit(
                    self._store,
                    workspace_id=workspace_id,
                    assignment_id=assignment_id,
                    repository_id=repository_id,
                    head_commit_sha=head_commit_sha,
                )
                if existing:
                    snapshot_id = existing
                    reused_snapshot = True

            if not snapshot_id:
                snapshot_id = self._store.create_snapshot_pending(
                    workspace_id=workspace_id,
                    assignment_id=assignment_id,
                    owner=owner,
                    repo_name=repo_name,
                    repo_full_name=full_name,
                )
        else:
            snapshot_id = snapshot_id or uuid.uuid4().hex

        logger.info(
            "Pipeline start repo=%s snapshot_id=%s head=%s reused=%s",
            full_name,
            snapshot_id,
            head_commit_sha[:12],
            reused_snapshot,
        )

        try:
            snapshot = build_repository_snapshot(client, repo_input, snapshot_id=snapshot_id)
        except GitHubRepoClientError as exc:
            if opts.persist:
                self._store.mark_snapshot_failed(snapshot_id, str(exc))
            raise PipelineError(str(exc)) from exc

        if snapshot.repository.head_commit_sha != head_commit_sha:
            logger.warning(
                "HEAD moved during ingest: expected %s got %s",
                head_commit_sha[:12],
                snapshot.repository.head_commit_sha[:12],
            )

        snapshot = _normalize_snapshot_timestamps(snapshot)
        snapshot_payload = snapshot.to_dict()
        synced_at = snapshot.repository.last_synced_at

        # Step 2 — deterministic file list
        files = flatten_snapshot_files(snapshot.folder_structure)
        files = _filter_files_for_incremental(files, opts.changed_paths)
        files.sort(key=lambda row: row.get("path") or "")
        eligibility = summarize_index_eligibility(
            flatten_snapshot_files(snapshot.folder_structure),
        )

        # Step 3 — code index
        code_index: List[Dict[str, Any]] = []
        index_entries: List[FileCodeIndex] = []
        if not opts.skip_index:
            index_snapshot = snapshot_payload
            if opts.changed_paths:
                # Index only incremental paths while retaining full repo path context.
                allowed = {row.get("path") for row in files}
                pruned = dict(snapshot_payload)
                pruned["folder_structure"] = _prune_folder_tree(
                    snapshot.folder_structure,
                    allowed,
                )
                index_snapshot = pruned
            try:
                index_entries = build_code_index_from_snapshot(
                    client,
                    owner,
                    repo_name,
                    index_snapshot,
                    indexed_at=synced_at,
                )
            except GitHubRepoClientError as exc:
                if opts.persist:
                    self._store.mark_snapshot_failed(snapshot_id, str(exc))
                raise PipelineError(str(exc)) from exc
            code_index = [entry.to_dict() for entry in index_entries]

        # Step 4 — baseline metrics (numerical only)
        metrics: Dict[str, Any] = {}
        if not opts.skip_metrics:
            content_fetcher = _github_content_fetcher(token, owner, repo_name)
            metrics = compute_baseline_metrics(
                snapshot_payload,
                computed_at=synced_at,
                content_fetcher=content_fetcher,
            ).to_dict()

        # Step 5 — persist (upsert = idempotent)
        if opts.persist:
            try:
                self._store.save_snapshot(
                    snapshot,
                    workspace_id=workspace_id,
                    assignment_id=assignment_id,
                    repository_id=repository_id or None,
                )
                if index_entries:
                    self._store.upsert_code_index_entries(
                        snapshot_id,
                        index_entries,
                        replace=not bool(opts.changed_paths),
                    )
                if metrics:
                    self._store.upsert_baseline_metrics(
                        snapshot_id,
                        metrics,
                        repository_id=repository_id or None,
                    )
            except Exception as exc:
                self._store.mark_snapshot_failed(snapshot_id, str(exc))
                raise PipelineError(f"Persist failed: {exc}") from exc

            row = self._store.get_snapshot_row(snapshot_id)
            if row:
                repository_id = row.repository_id or repository_id

        fingerprint = _result_fingerprint(
            snapshot=snapshot_payload,
            files=files,
            code_index=code_index,
            metrics=metrics,
        )

        return PipelineResult(
            snapshot_id=snapshot_id,
            repository_id=repository_id,
            repo_full_name=full_name,
            head_commit_sha=snapshot.repository.head_commit_sha,
            file_count=len(files) if opts.changed_paths else eligibility["total_files"],
            index_eligible=eligibility["index_eligible"],
            indexed_files=len(code_index),
            persisted=opts.persist,
            reused_snapshot=reused_snapshot,
            result_fingerprint=fingerprint,
            snapshot=snapshot_payload,
            files=files,
            code_index=code_index,
            metrics=metrics,
        )


def _prune_folder_tree(
    node: Dict[str, Any],
    allowed_paths: set[str],
) -> Dict[str, Any]:
    if node.get("type") == "file":
        path = node.get("path") or ""
        return node if path in allowed_paths else {}
    children: List[Dict[str, Any]] = []
    for child in node.get("children") or []:
        pruned = _prune_folder_tree(child, allowed_paths)
        if pruned:
            children.append(pruned)
    if not children:
        return {}
    return {
        "name": node.get("name") or "",
        "path": node.get("path") or "",
        "type": "directory",
        "children": children,
    }


def run_repo_ingestion(
    token: str,
    repo_input: str,
    *,
    workspace_id: str,
    assignment_id: str,
    options: Optional[PipelineOptions] = None,
) -> PipelineResult:
    """Convenience entrypoint for a full deterministic ingest."""
    return RepoIngestionPipeline().run(
        token,
        repo_input,
        workspace_id=workspace_id,
        assignment_id=assignment_id,
        options=options,
    )
