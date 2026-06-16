"""Postgres persistence for baseline repository metrics — delegates to db.repository_store."""

from __future__ import annotations

from typing import Any, Dict, Optional

from config.logging_config import get_logger
from db.repository_store import RepositoryStore

logger = get_logger(__name__)


class BaselineMetricsStore:
    """Backward-compatible facade over the structured repository store."""

    def __init__(self, adapter: Any) -> None:
        self._store = RepositoryStore(adapter)

    def save_metrics(self, snapshot_id: str, metrics: Dict[str, Any]) -> None:
        self._store.upsert_baseline_metrics(snapshot_id, metrics)

    def get_metrics(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get_baseline_metrics(snapshot_id)


def get_metrics_store() -> BaselineMetricsStore:
    from services.security.db_system import secure_db

    return BaselineMetricsStore(secure_db.adapter)
