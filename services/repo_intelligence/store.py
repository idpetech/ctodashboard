"""Postgres persistence for repository snapshots — delegates to db.repository_store."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from db.repository_store import RepositoryStore
from services.repo_intelligence.snapshot_models import RepositorySnapshot

logger = get_logger(__name__)


class RepositorySnapshotStore:
    """Backward-compatible facade over the structured repository store."""

    def __init__(self, adapter: Any) -> None:
        self._store = RepositoryStore(adapter)

    def create_snapshot_pending(
        self,
        *,
        workspace_id: str,
        assignment_id: str,
        owner: str,
        repo_name: str,
        repo_full_name: str,
    ) -> str:
        return self._store.create_snapshot_pending(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            owner=owner,
            repo_name=repo_name,
            repo_full_name=repo_full_name,
        )

    def save_snapshot(self, snapshot: RepositorySnapshot) -> None:
        row = self._store.get_snapshot_row(snapshot.snapshot_id)
        if not row:
            raise ValueError("Snapshot row not found; create_snapshot_pending first")
        self._store.save_snapshot(
            snapshot,
            workspace_id=row.workspace_id,
            assignment_id=row.assignment_id,
        )

    def mark_snapshot_failed(self, snapshot_id: str, error_message: str) -> None:
        self._store.mark_snapshot_failed(snapshot_id, error_message)

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        row = self._store.get_snapshot_row(snapshot_id)
        if not row:
            return None
        return {
            "snapshot_id": row.snapshot_id,
            "workspace_id": row.workspace_id,
            "assignment_id": row.assignment_id,
            "owner": row.owner,
            "repo_name": row.repo_name,
            "repo_full_name": row.repo_full_name,
            "default_branch": row.default_branch,
            "head_commit_sha": row.head_commit_sha,
            "last_synced_at": row.last_synced_at,
            "status": row.status,
            "error_message": row.error_message,
            "payload": row.payload,
            "snapshot_version": row.snapshot_version,
            "repository_id": row.repository_id,
        }

    def list_snapshots(
        self,
        workspace_id: str,
        assignment_id: str,
        *,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        from db.models import RepositoryQuery

        rows = self._store.list_snapshots(
            RepositoryQuery(workspace_id=workspace_id, assignment_id=assignment_id),
            limit=limit,
        )
        return [row.payload for row in rows if row.payload]


def get_store() -> RepositorySnapshotStore:
    from services.security.secure_database import secure_db

    return RepositorySnapshotStore(secure_db.adapter)
