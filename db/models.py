"""Typed records for CTO Lens Repo Intelligence storage."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


def _iso_timestamp(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        dt = value
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=None)
        return dt.isoformat().replace("+00:00", "Z")
    return str(value)


@dataclass
class RepositoryRecord:
    """Stable repository identity within a workspace assignment."""

    repository_id: str
    workspace_id: str
    assignment_id: str
    owner: str
    repo_name: str
    repo_full_name: str
    default_branch: str = "main"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> RepositoryRecord:
        return cls(
            repository_id=str(row.get("repository_id") or ""),
            workspace_id=str(row.get("workspace_id") or ""),
            assignment_id=str(row.get("assignment_id") or ""),
            owner=str(row.get("owner") or ""),
            repo_name=str(row.get("repo_name") or ""),
            repo_full_name=str(row.get("repo_full_name") or ""),
            default_branch=str(row.get("default_branch") or "main"),
            metadata=_json_dict(row.get("metadata")),
            created_at=_iso_timestamp(row.get("created_at")),
            updated_at=_iso_timestamp(row.get("updated_at")),
        )


@dataclass
class SnapshotRecord:
    """Point-in-time repository snapshot header + JSON payload."""

    snapshot_id: str
    workspace_id: str
    assignment_id: str
    owner: str
    repo_name: str
    repo_full_name: str
    repository_id: str = ""
    default_branch: str = "main"
    head_commit_sha: str = ""
    last_synced_at: str = ""
    status: str = "pending"
    error_message: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    snapshot_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> SnapshotRecord:
        return cls(
            snapshot_id=str(row.get("snapshot_id") or ""),
            repository_id=str(row.get("repository_id") or ""),
            workspace_id=str(row.get("workspace_id") or ""),
            assignment_id=str(row.get("assignment_id") or ""),
            owner=str(row.get("owner") or ""),
            repo_name=str(row.get("repo_name") or ""),
            repo_full_name=str(row.get("repo_full_name") or ""),
            default_branch=str(row.get("default_branch") or "main"),
            head_commit_sha=str(row.get("head_commit_sha") or ""),
            last_synced_at=_iso_timestamp(row.get("last_synced_at")),
            status=str(row.get("status") or "pending"),
            error_message=str(row.get("error_message") or ""),
            payload=_json_dict(row.get("payload")),
            snapshot_version=int(row.get("snapshot_version") or 1),
        )


@dataclass(frozen=True)
class CommitRecord:
    """Normalized commit metadata for time-range queries."""

    snapshot_id: str
    repository_id: str
    commit_hash: str
    author: str
    committed_at: str
    files_changed_count: int = 0
    commit_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> CommitRecord:
        return cls(
            snapshot_id=str(row.get("snapshot_id") or ""),
            repository_id=str(row.get("repository_id") or ""),
            commit_hash=str(row.get("commit_hash") or ""),
            author=str(row.get("author") or ""),
            committed_at=_iso_timestamp(row.get("committed_at")),
            files_changed_count=int(row.get("files_changed_count") or 0),
            commit_payload=_json_dict(row.get("commit_payload")),
        )


@dataclass
class CodeIndexRecord:
    """Per-file code index row."""

    snapshot_id: str
    file_path: str
    repository_id: str = ""
    git_sha: str = ""
    language: str = ""
    index_payload: Dict[str, Any] = field(default_factory=dict)
    last_indexed: str = ""
    code_index_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> CodeIndexRecord:
        return cls(
            snapshot_id=str(row.get("snapshot_id") or ""),
            repository_id=str(row.get("repository_id") or ""),
            file_path=str(row.get("file_path") or ""),
            git_sha=str(row.get("git_sha") or ""),
            language=str(row.get("language") or ""),
            index_payload=_json_dict(row.get("index_payload")),
            last_indexed=_iso_timestamp(row.get("last_indexed")),
            code_index_version=int(row.get("code_index_version") or 1),
        )


@dataclass(frozen=True)
class CodeSymbolRecord:
    """Denormalized symbol row for fast lookup by name and file path."""

    snapshot_id: str
    repository_id: str
    file_path: str
    symbol_kind: str
    symbol_name: str
    line: int
    parent_symbol: str = ""
    language: str = ""
    git_sha: str = ""
    symbol_payload: Dict[str, Any] = field(default_factory=dict)
    last_indexed: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BaselineMetricsRecord:
    """Numerical baseline metrics for a snapshot."""

    snapshot_id: str
    repo_full_name: str
    repository_id: str = ""
    metrics_payload: Dict[str, Any] = field(default_factory=dict)
    computed_at: str = ""
    metrics_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> BaselineMetricsRecord:
        return cls(
            snapshot_id=str(row.get("snapshot_id") or ""),
            repository_id=str(row.get("repository_id") or ""),
            repo_full_name=str(row.get("repo_full_name") or ""),
            metrics_payload=_json_dict(row.get("metrics_payload")),
            computed_at=_iso_timestamp(row.get("computed_at")),
            metrics_version=int(row.get("metrics_version") or 1),
        )


@dataclass
class RepositoryQuery:
    """Filter for repository-scoped reads."""

    workspace_id: str
    assignment_id: Optional[str] = None
    repo_full_name: Optional[str] = None
    repository_id: Optional[str] = None


@dataclass
class TimeRangeQuery:
    """Inclusive time-range filter (ISO timestamps or datetimes)."""

    since: Optional[str] = None
    until: Optional[str] = None

    def sql_bounds(self) -> tuple[Optional[str], Optional[str]]:
        return self.since, self.until


def _json_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        import json

        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}
