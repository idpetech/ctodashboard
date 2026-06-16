"""Postgres persistence for per-file code index entries — delegates to db.repository_store."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from db.repository_store import RepositoryStore
from services.repo_intelligence.models.code_index import FileCodeIndex

logger = get_logger(__name__)


class CodeIndexStore:
    """Backward-compatible facade over the structured repository store."""

    def __init__(self, adapter: Any) -> None:
        self._store = RepositoryStore(adapter)

    def replace_snapshot_index(self, snapshot_id: str, entries: List[FileCodeIndex]) -> int:
        return self._store.upsert_code_index_entries(snapshot_id, entries, replace=True)

    def list_index_entries(
        self,
        snapshot_id: str,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return self._store.list_code_index_entries(snapshot_id=snapshot_id, limit=limit, offset=offset)

    def count_index_entries(self, snapshot_id: str) -> int:
        return self._store.count_code_index_entries(snapshot_id)

    def get_index_entry(self, snapshot_id: str, file_path: str) -> Optional[Dict[str, Any]]:
        return self._store.get_code_index_entry(snapshot_id, file_path)


def get_code_index_store() -> CodeIndexStore:
    from services.security.db_system import secure_db

    return CodeIndexStore(secure_db.adapter)
