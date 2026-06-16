"""Unified Postgres storage for CTO Lens Repo Intelligence."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from config.logging_config import get_logger
from db.models import (
    BaselineMetricsRecord,
    CodeSymbolRecord,
    CommitRecord,
    RepositoryQuery,
    RepositoryRecord,
    SnapshotRecord,
    TimeRangeQuery,
)
from services.repo_intelligence.config import (
    BASELINE_METRICS_VERSION,
    CODE_INDEX_VERSION,
    SNAPSHOT_VERSION,
)
from services.repo_intelligence.models.code_index import FileCodeIndex
from services.repo_intelligence.snapshot_models import CommitMetadata, RepositorySnapshot

logger = get_logger(__name__)


class RepositoryStoreError(Exception):
    """User-visible repository storage error."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_commit_timestamp(value: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        return _utc_now()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return _utc_now()
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _json_loads(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _symbols_from_index_entry(
    entry: FileCodeIndex,
    *,
    snapshot_id: str,
    repository_id: str,
) -> List[CodeSymbolRecord]:
    """Extract denormalized symbol rows from a file code index entry."""
    rows: List[CodeSymbolRecord] = []
    payload = entry.to_dict()
    indexed_at = entry.last_indexed

    for fn in payload.get("symbols", {}).get("functions") or []:
        rows.append(
            CodeSymbolRecord(
                snapshot_id=snapshot_id,
                repository_id=repository_id,
                file_path=entry.file_path,
                symbol_kind="function",
                symbol_name=str(fn.get("name") or ""),
                line=int(fn.get("line") or 0),
                language=entry.language,
                git_sha=entry.git_sha,
                symbol_payload={"source": "function"},
                last_indexed=indexed_at,
            )
        )

    for cls in payload.get("symbols", {}).get("classes") or []:
        class_name = str(cls.get("name") or "")
        rows.append(
            CodeSymbolRecord(
                snapshot_id=snapshot_id,
                repository_id=repository_id,
                file_path=entry.file_path,
                symbol_kind="class",
                symbol_name=class_name,
                line=int(cls.get("line") or 0),
                language=entry.language,
                git_sha=entry.git_sha,
                symbol_payload={"source": "class"},
                last_indexed=indexed_at,
            )
        )
        for method in cls.get("methods") or []:
            rows.append(
                CodeSymbolRecord(
                    snapshot_id=snapshot_id,
                    repository_id=repository_id,
                    file_path=entry.file_path,
                    symbol_kind="method",
                    symbol_name=str(method.get("name") or ""),
                    parent_symbol=class_name,
                    line=int(method.get("line") or 0),
                    language=entry.language,
                    git_sha=entry.git_sha,
                    symbol_payload={"source": "method", "parent": class_name},
                    last_indexed=indexed_at,
                )
            )
    return rows


class RepositoryStore:
    """Structured, incremental storage for repo intelligence artifacts."""

    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    # ------------------------------------------------------------------
    # Repository metadata
    # ------------------------------------------------------------------
    def upsert_repository(
        self,
        *,
        workspace_id: str,
        assignment_id: str,
        owner: str,
        repo_name: str,
        repo_full_name: str,
        default_branch: str = "main",
        metadata: Optional[Dict[str, Any]] = None,
        repository_id: Optional[str] = None,
    ) -> RepositoryRecord:
        repo_id = repository_id or uuid.uuid4().hex
        when = _utc_now()
        meta_json = json.dumps(metadata or {})
        self.adapter.execute_update(
            """
            INSERT INTO repositories (
                repository_id, workspace_id, assignment_id, owner, repo_name,
                repo_full_name, default_branch, metadata, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (workspace_id, assignment_id, repo_full_name) DO UPDATE SET
                owner = EXCLUDED.owner,
                repo_name = EXCLUDED.repo_name,
                default_branch = EXCLUDED.default_branch,
                metadata = repositories.metadata || EXCLUDED.metadata,
                updated_at = EXCLUDED.updated_at
            """,
            (
                repo_id,
                workspace_id,
                assignment_id,
                owner,
                repo_name,
                repo_full_name,
                default_branch,
                meta_json,
                when,
                when,
            ),
        )
        record = self.get_repository(
            RepositoryQuery(
                workspace_id=workspace_id,
                assignment_id=assignment_id,
                repo_full_name=repo_full_name,
            )
        )
        if not record:
            raise RepositoryStoreError("Failed to upsert repository")
        return record

    def get_repository(self, query: RepositoryQuery) -> Optional[RepositoryRecord]:
        clauses = ["workspace_id = %s"]
        params: List[Any] = [query.workspace_id]

        if query.repository_id:
            clauses.append("repository_id = %s")
            params.append(query.repository_id)
        if query.assignment_id:
            clauses.append("assignment_id = %s")
            params.append(query.assignment_id)
        if query.repo_full_name:
            clauses.append("repo_full_name = %s")
            params.append(query.repo_full_name)

        rows = self.adapter.execute_query(
            f"""
            SELECT repository_id, workspace_id, assignment_id, owner, repo_name,
                   repo_full_name, default_branch, metadata, created_at, updated_at
            FROM repositories
            WHERE {' AND '.join(clauses)}
            LIMIT 1
            """,
            tuple(params),
        )
        return RepositoryRecord.from_row(dict(rows[0])) if rows else None

    def list_repositories(self, workspace_id: str, *, assignment_id: Optional[str] = None) -> List[RepositoryRecord]:
        if assignment_id:
            rows = self.adapter.execute_query(
                """
                SELECT repository_id, workspace_id, assignment_id, owner, repo_name,
                       repo_full_name, default_branch, metadata, created_at, updated_at
                FROM repositories
                WHERE workspace_id = %s AND assignment_id = %s
                ORDER BY repo_full_name ASC
                """,
                (workspace_id, assignment_id),
            )
        else:
            rows = self.adapter.execute_query(
                """
                SELECT repository_id, workspace_id, assignment_id, owner, repo_name,
                       repo_full_name, default_branch, metadata, created_at, updated_at
                FROM repositories
                WHERE workspace_id = %s
                ORDER BY repo_full_name ASC
                """,
                (workspace_id,),
            )
        return [RepositoryRecord.from_row(dict(row)) for row in rows or []]

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------
    def create_snapshot_pending(
        self,
        *,
        workspace_id: str,
        assignment_id: str,
        owner: str,
        repo_name: str,
        repo_full_name: str,
        repository_id: Optional[str] = None,
    ) -> str:
        repo = self.upsert_repository(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            owner=owner,
            repo_name=repo_name,
            repo_full_name=repo_full_name,
            repository_id=repository_id,
        )
        snapshot_id = uuid.uuid4().hex
        when = _utc_now()
        self.adapter.execute_update(
            """
            INSERT INTO repository_snapshots (
                snapshot_id, repository_id, workspace_id, assignment_id, owner,
                repo_name, repo_full_name, default_branch, head_commit_sha,
                last_synced_at, status, payload, snapshot_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, '', %s, 'pending', '{}'::jsonb, %s)
            """,
            (
                snapshot_id,
                repo.repository_id,
                workspace_id,
                assignment_id,
                owner,
                repo_name,
                repo_full_name,
                when,
                SNAPSHOT_VERSION,
            ),
        )
        return snapshot_id

    def save_snapshot(
        self,
        snapshot: RepositorySnapshot,
        *,
        workspace_id: str,
        assignment_id: str,
        repository_id: Optional[str] = None,
    ) -> SnapshotRecord:
        """Persist snapshot and normalized commit rows."""
        return self.save_snapshot_with_context(
            snapshot,
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            repository_id=repository_id,
        )

    def save_snapshot_with_context(
        self,
        snapshot: RepositorySnapshot,
        *,
        workspace_id: str,
        assignment_id: str,
        repository_id: Optional[str] = None,
    ) -> SnapshotRecord:
        """Persist snapshot when workspace context is supplied by the caller."""
        repo = self.upsert_repository(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            owner=snapshot.repository.owner,
            repo_name=snapshot.repository.repo_name,
            repo_full_name=snapshot.repository.full_name,
            default_branch=snapshot.repository.default_branch,
            repository_id=repository_id,
        )
        payload = snapshot.to_dict()
        self.adapter.execute_update(
            """
            UPDATE repository_snapshots
            SET repository_id = %s,
                workspace_id = %s,
                assignment_id = %s,
                owner = %s,
                repo_name = %s,
                repo_full_name = %s,
                default_branch = %s,
                head_commit_sha = %s,
                last_synced_at = %s,
                status = 'completed',
                error_message = NULL,
                payload = %s::jsonb,
                snapshot_version = %s
            WHERE snapshot_id = %s
            """,
            (
                repo.repository_id,
                workspace_id,
                assignment_id,
                snapshot.repository.owner,
                snapshot.repository.repo_name,
                snapshot.repository.full_name,
                snapshot.repository.default_branch,
                snapshot.repository.head_commit_sha,
                snapshot.repository.last_synced_at,
                json.dumps(payload),
                SNAPSHOT_VERSION,
                snapshot.snapshot_id,
            ),
        )
        self.upsert_commits(snapshot.snapshot_id, repo.repository_id, snapshot.commits)
        saved = self.get_snapshot_row(snapshot.snapshot_id)
        if not saved:
            raise RepositoryStoreError("Failed to persist snapshot")
        return saved

    def mark_snapshot_failed(self, snapshot_id: str, error_message: str) -> None:
        self.adapter.execute_update(
            """
            UPDATE repository_snapshots
            SET status = 'failed', error_message = %s
            WHERE snapshot_id = %s
            """,
            (error_message[:2000], snapshot_id),
        )

    def get_snapshot_row(self, snapshot_id: str) -> Optional[SnapshotRecord]:
        rows = self.adapter.execute_query(
            """
            SELECT snapshot_id, repository_id, workspace_id, assignment_id, owner,
                   repo_name, repo_full_name, default_branch, head_commit_sha,
                   last_synced_at, status, error_message, payload, snapshot_version
            FROM repository_snapshots
            WHERE snapshot_id = %s
            """,
            (snapshot_id,),
        )
        return SnapshotRecord.from_row(dict(rows[0])) if rows else None

    def get_snapshot_payload(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        row = self.get_snapshot_row(snapshot_id)
        return row.payload if row else None

    def list_snapshots(
        self,
        query: RepositoryQuery,
        *,
        time_range: Optional[TimeRangeQuery] = None,
        limit: int = 20,
        status: str = "completed",
    ) -> List[SnapshotRecord]:
        clauses = ["workspace_id = %s"]
        params: List[Any] = [query.workspace_id]

        if query.assignment_id:
            clauses.append("assignment_id = %s")
            params.append(query.assignment_id)
        if query.repository_id:
            clauses.append("repository_id = %s")
            params.append(query.repository_id)
        if query.repo_full_name:
            clauses.append("repo_full_name = %s")
            params.append(query.repo_full_name)
        if status:
            clauses.append("status = %s")
            params.append(status)
        if time_range and time_range.since:
            clauses.append("last_synced_at >= %s")
            params.append(time_range.since)
        if time_range and time_range.until:
            clauses.append("last_synced_at <= %s")
            params.append(time_range.until)

        params.append(max(1, min(limit, 200)))
        rows = self.adapter.execute_query(
            f"""
            SELECT snapshot_id, repository_id, workspace_id, assignment_id, owner,
                   repo_name, repo_full_name, default_branch, head_commit_sha,
                   last_synced_at, status, error_message, payload, snapshot_version
            FROM repository_snapshots
            WHERE {' AND '.join(clauses)}
            ORDER BY last_synced_at DESC
            LIMIT %s
            """,
            tuple(params),
        )
        return [SnapshotRecord.from_row(dict(row)) for row in rows or []]

    # ------------------------------------------------------------------
    # Commits
    # ------------------------------------------------------------------
    def upsert_commits(
        self,
        snapshot_id: str,
        repository_id: str,
        commits: Sequence[CommitMetadata],
    ) -> int:
        if not commits:
            return 0
        count = 0
        try:
            self.adapter.begin_transaction()
            for commit in commits:
                committed_at = _parse_commit_timestamp(commit.timestamp)
                payload = commit.to_dict()
                self.adapter.execute_update(
                    """
                    INSERT INTO repository_commits (
                        snapshot_id, repository_id, commit_hash, author,
                        committed_at, files_changed_count, commit_payload
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (snapshot_id, commit_hash) DO UPDATE SET
                        author = EXCLUDED.author,
                        committed_at = EXCLUDED.committed_at,
                        files_changed_count = EXCLUDED.files_changed_count,
                        commit_payload = EXCLUDED.commit_payload
                    """,
                    (
                        snapshot_id,
                        repository_id,
                        commit.hash,
                        commit.author,
                        committed_at,
                        commit.files_changed_count,
                        json.dumps(payload),
                    ),
                )
                count += 1
            self.adapter.commit_transaction()
        except Exception:
            self.adapter.rollback_transaction()
            raise
        return count

    def list_commits(
        self,
        *,
        repository_id: str,
        snapshot_id: Optional[str] = None,
        time_range: Optional[TimeRangeQuery] = None,
        limit: int = 100,
    ) -> List[CommitRecord]:
        clauses = ["repository_id = %s"]
        params: List[Any] = [repository_id]

        if snapshot_id:
            clauses.append("snapshot_id = %s")
            params.append(snapshot_id)
        if time_range and time_range.since:
            clauses.append("committed_at >= %s")
            params.append(time_range.since)
        if time_range and time_range.until:
            clauses.append("committed_at <= %s")
            params.append(time_range.until)

        params.append(max(1, min(limit, 500)))
        rows = self.adapter.execute_query(
            f"""
            SELECT snapshot_id, repository_id, commit_hash, author,
                   committed_at, files_changed_count, commit_payload
            FROM repository_commits
            WHERE {' AND '.join(clauses)}
            ORDER BY committed_at DESC
            LIMIT %s
            """,
            tuple(params),
        )
        return [CommitRecord.from_row(dict(row)) for row in rows or []]

    # ------------------------------------------------------------------
    # Code index + symbols
    # ------------------------------------------------------------------
    def upsert_code_index_entries(
        self,
        snapshot_id: str,
        entries: Sequence[FileCodeIndex],
        *,
        replace: bool = False,
    ) -> int:
        snapshot = self.get_snapshot_row(snapshot_id)
        if not snapshot:
            raise RepositoryStoreError("Snapshot not found")
        repository_id = snapshot.repository_id
        if not repository_id:
            raise RepositoryStoreError("Snapshot is missing repository_id")

        count = 0
        try:
            self.adapter.begin_transaction()
            if replace:
                self.adapter.execute_update(
                    "DELETE FROM repository_code_index WHERE snapshot_id = %s",
                    (snapshot_id,),
                )
                self.adapter.execute_update(
                    "DELETE FROM repository_code_symbols WHERE snapshot_id = %s",
                    (snapshot_id,),
                )

            for entry in entries:
                payload = entry.to_dict()
                self.adapter.execute_update(
                    """
                    INSERT INTO repository_code_index (
                        snapshot_id, repository_id, file_path, git_sha, language,
                        index_payload, last_indexed, code_index_version
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (snapshot_id, file_path) DO UPDATE SET
                        repository_id = EXCLUDED.repository_id,
                        git_sha = EXCLUDED.git_sha,
                        language = EXCLUDED.language,
                        index_payload = EXCLUDED.index_payload,
                        last_indexed = EXCLUDED.last_indexed,
                        code_index_version = EXCLUDED.code_index_version
                    """,
                    (
                        snapshot_id,
                        repository_id,
                        entry.file_path,
                        entry.git_sha,
                        entry.language,
                        json.dumps(payload),
                        entry.last_indexed,
                        CODE_INDEX_VERSION,
                    ),
                )
                self._replace_symbols_for_file(snapshot_id, repository_id, entry)
                count += 1
            self.adapter.commit_transaction()
        except Exception:
            self.adapter.rollback_transaction()
            raise
        return count

    def _replace_symbols_for_file(
        self,
        snapshot_id: str,
        repository_id: str,
        entry: FileCodeIndex,
    ) -> None:
        self.adapter.execute_update(
            """
            DELETE FROM repository_code_symbols
            WHERE snapshot_id = %s AND file_path = %s
            """,
            (snapshot_id, entry.file_path),
        )
        for symbol in _symbols_from_index_entry(
            entry,
            snapshot_id=snapshot_id,
            repository_id=repository_id,
        ):
            self.adapter.execute_update(
                """
                INSERT INTO repository_code_symbols (
                    snapshot_id, repository_id, file_path, symbol_kind, symbol_name,
                    parent_symbol, line, language, git_sha, symbol_payload, last_indexed
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (snapshot_id, file_path, symbol_kind, symbol_name, line) DO UPDATE SET
                    parent_symbol = EXCLUDED.parent_symbol,
                    language = EXCLUDED.language,
                    git_sha = EXCLUDED.git_sha,
                    symbol_payload = EXCLUDED.symbol_payload,
                    last_indexed = EXCLUDED.last_indexed
                """,
                (
                    snapshot_id,
                    repository_id,
                    symbol.file_path,
                    symbol.symbol_kind,
                    symbol.symbol_name,
                    symbol.parent_symbol or None,
                    symbol.line,
                    symbol.language,
                    symbol.git_sha,
                    json.dumps(symbol.symbol_payload),
                    symbol.last_indexed or entry.last_indexed,
                ),
            )

    def get_code_index_entry(self, snapshot_id: str, file_path: str) -> Optional[Dict[str, Any]]:
        rows = self.adapter.execute_query(
            """
            SELECT index_payload
            FROM repository_code_index
            WHERE snapshot_id = %s AND file_path = %s
            """,
            (snapshot_id, file_path),
        )
        if not rows:
            return None
        payload = _json_loads(rows[0].get("index_payload") or {})
        return payload if isinstance(payload, dict) else None

    def list_code_index_entries(
        self,
        *,
        snapshot_id: Optional[str] = None,
        repository_id: Optional[str] = None,
        file_path: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []

        if snapshot_id:
            clauses.append("snapshot_id = %s")
            params.append(snapshot_id)
        if repository_id:
            clauses.append("repository_id = %s")
            params.append(repository_id)
        if file_path:
            clauses.append("file_path = %s")
            params.append(file_path)

        if not clauses:
            raise RepositoryStoreError("At least one of snapshot_id or repository_id is required")

        params.extend([max(1, min(limit, 2000)), max(0, offset)])
        rows = self.adapter.execute_query(
            f"""
            SELECT index_payload
            FROM repository_code_index
            WHERE {' AND '.join(clauses)}
            ORDER BY file_path ASC
            LIMIT %s OFFSET %s
            """,
            tuple(params),
        )
        out: List[Dict[str, Any]] = []
        for row in rows or []:
            payload = _json_loads(row.get("index_payload") or {})
            if isinstance(payload, dict):
                out.append(payload)
        return out

    def count_code_index_entries(self, snapshot_id: str) -> int:
        rows = self.adapter.execute_query(
            "SELECT COUNT(*) AS count FROM repository_code_index WHERE snapshot_id = %s",
            (snapshot_id,),
        )
        return int(rows[0]["count"]) if rows else 0

    def find_symbols(
        self,
        *,
        repository_id: str,
        symbol_name: str,
        snapshot_id: Optional[str] = None,
        file_path: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        clauses = ["repository_id = %s", "symbol_name = %s"]
        params: List[Any] = [repository_id, symbol_name]

        if snapshot_id:
            clauses.append("snapshot_id = %s")
            params.append(snapshot_id)
        if file_path:
            clauses.append("file_path = %s")
            params.append(file_path)

        params.append(max(1, min(limit, 500)))
        rows = self.adapter.execute_query(
            f"""
            SELECT snapshot_id, repository_id, file_path, symbol_kind, symbol_name,
                   parent_symbol, line, language, git_sha, symbol_payload, last_indexed
            FROM repository_code_symbols
            WHERE {' AND '.join(clauses)}
            ORDER BY last_indexed DESC, file_path ASC, line ASC
            LIMIT %s
            """,
            tuple(params),
        )
        out: List[Dict[str, Any]] = []
        for row in rows or []:
            item = dict(row)
            item["symbol_payload"] = _json_loads(item.get("symbol_payload") or {})
            out.append(item)
        return out

    def search_symbols_by_prefix(
        self,
        *,
        repository_id: str,
        name_prefix: str,
        snapshot_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        clauses = ["repository_id = %s", "symbol_name ILIKE %s"]
        params: List[Any] = [repository_id, f"{name_prefix}%"]
        if snapshot_id:
            clauses.append("snapshot_id = %s")
            params.append(snapshot_id)
        params.append(max(1, min(limit, 500)))
        rows = self.adapter.execute_query(
            f"""
            SELECT snapshot_id, repository_id, file_path, symbol_kind, symbol_name,
                   parent_symbol, line, language, git_sha, symbol_payload, last_indexed
            FROM repository_code_symbols
            WHERE {' AND '.join(clauses)}
            ORDER BY symbol_name ASC, file_path ASC, line ASC
            LIMIT %s
            """,
            tuple(params),
        )
        out: List[Dict[str, Any]] = []
        for row in rows or []:
            item = dict(row)
            item["symbol_payload"] = _json_loads(item.get("symbol_payload") or {})
            out.append(item)
        return out

    # ------------------------------------------------------------------
    # Baseline metrics
    # ------------------------------------------------------------------
    def upsert_baseline_metrics(
        self,
        snapshot_id: str,
        metrics: Dict[str, Any],
        *,
        repository_id: Optional[str] = None,
    ) -> BaselineMetricsRecord:
        snapshot = self.get_snapshot_row(snapshot_id)
        if not snapshot:
            raise RepositoryStoreError("Snapshot not found")

        repo_id = repository_id or snapshot.repository_id
        repo_full_name = str(metrics.get("repo_full_name") or snapshot.repo_full_name)
        computed_at = metrics.get("computed_at") or _iso(_utc_now())

        self.adapter.execute_update(
            """
            INSERT INTO repository_baseline_metrics (
                snapshot_id, repository_id, repo_full_name,
                metrics_payload, computed_at, metrics_version
            ) VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (snapshot_id) DO UPDATE SET
                repository_id = EXCLUDED.repository_id,
                repo_full_name = EXCLUDED.repo_full_name,
                metrics_payload = EXCLUDED.metrics_payload,
                computed_at = EXCLUDED.computed_at,
                metrics_version = EXCLUDED.metrics_version
            """,
            (
                snapshot_id,
                repo_id,
                repo_full_name,
                json.dumps(metrics),
                computed_at,
                BASELINE_METRICS_VERSION,
            ),
        )
        row = self.get_baseline_metrics_row(snapshot_id)
        if not row:
            raise RepositoryStoreError("Failed to persist baseline metrics")
        return row

    def get_baseline_metrics(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        row = self.get_baseline_metrics_row(snapshot_id)
        return row.metrics_payload if row else None

    def get_baseline_metrics_row(self, snapshot_id: str) -> Optional[BaselineMetricsRecord]:
        rows = self.adapter.execute_query(
            """
            SELECT snapshot_id, repository_id, repo_full_name,
                   metrics_payload, computed_at, metrics_version
            FROM repository_baseline_metrics
            WHERE snapshot_id = %s
            """,
            (snapshot_id,),
        )
        return BaselineMetricsRecord.from_row(dict(rows[0])) if rows else None

    def list_baseline_metrics(
        self,
        *,
        repository_id: str,
        time_range: Optional[TimeRangeQuery] = None,
        limit: int = 20,
    ) -> List[BaselineMetricsRecord]:
        clauses = ["repository_id = %s"]
        params: List[Any] = [repository_id]

        if time_range and time_range.since:
            clauses.append("computed_at >= %s")
            params.append(time_range.since)
        if time_range and time_range.until:
            clauses.append("computed_at <= %s")
            params.append(time_range.until)

        params.append(max(1, min(limit, 100)))
        rows = self.adapter.execute_query(
            f"""
            SELECT snapshot_id, repository_id, repo_full_name,
                   metrics_payload, computed_at, metrics_version
            FROM repository_baseline_metrics
            WHERE {' AND '.join(clauses)}
            ORDER BY computed_at DESC
            LIMIT %s
            """,
            tuple(params),
        )
        return [BaselineMetricsRecord.from_row(dict(row)) for row in rows or []]


def get_repository_store() -> RepositoryStore:
    from services.security.db_system import secure_db

    return RepositoryStore(secure_db.adapter)
