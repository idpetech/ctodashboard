"""
Load pipeline_result JSON from persisted Postgres rows.

This is the ONLY analysis-layer module that touches the database.
Analyzers and AnalysisEngine remain JSON-in / JSON-out.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from db.repository_store import RepositoryStore, get_repository_store


class PipelineLoadError(ValueError):
    """Raised when persisted snapshot data is missing or incomplete."""


def load_pipeline_result_from_db(
    snapshot_id: str,
    *,
    workspace_id: Optional[str] = None,
    store: Optional[RepositoryStore] = None,
) -> Dict[str, Any]:
    """
    Assemble a PipelineResult-shaped dict from repository_snapshots,
    repository_code_index, and repository_baseline_metrics.
    """
    repo_store = store or get_repository_store()
    row = repo_store.get_snapshot_row(snapshot_id)
    if not row:
        raise PipelineLoadError(f"Snapshot not found: {snapshot_id}")
    if workspace_id and row.workspace_id != workspace_id:
        raise PipelineLoadError(f"Snapshot not found: {snapshot_id}")
    if row.status != "completed":
        raise PipelineLoadError(f"Snapshot is not completed (status={row.status})")

    snapshot = row.payload
    if not snapshot:
        raise PipelineLoadError("Snapshot payload is empty")

    metrics = repo_store.get_baseline_metrics(snapshot_id)
    if not metrics:
        raise PipelineLoadError(
            "Baseline metrics not found for snapshot; run pipeline metrics step first"
        )

    code_index = _load_full_code_index(repo_store, snapshot_id)
    indexed_files = len(code_index)

    return {
        "snapshot_id": row.snapshot_id,
        "repository_id": row.repository_id or "",
        "repo_full_name": row.repo_full_name,
        "head_commit_sha": row.head_commit_sha,
        "file_count": int((metrics.get("repo_size") or {}).get("total_files") or 0),
        "index_eligible": indexed_files,
        "indexed_files": indexed_files,
        "result_fingerprint": "",
        "persisted": True,
        "snapshot": snapshot,
        "code_index": code_index,
        "metrics": metrics,
    }


def _load_full_code_index(store: RepositoryStore, snapshot_id: str) -> List[Dict[str, Any]]:
    """Page through code index rows (bounded pages, deterministic order)."""
    collected: List[Dict[str, Any]] = []
    offset = 0
    page_size = 2000
    while True:
        batch = store.list_code_index_entries(
            snapshot_id=snapshot_id,
            limit=page_size,
            offset=offset,
        )
        if not batch:
            break
        collected.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    collected.sort(key=lambda row: str(row.get("file_path") or ""))
    return collected
