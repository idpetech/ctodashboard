"""Typed structures for repo snapshots and file index rows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class TreeNode:
    path: str
    git_sha: str
    size_bytes: int
    node_type: str
    mode: str = ""


@dataclass
class FileIndexEntry:
    path: str
    git_sha: str
    size_bytes: int
    node_type: str
    extension: str
    language: Optional[str]
    depth: int
    line_count: Optional[int] = None
    content_sha256: Optional[str] = None

    def to_row(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "git_sha": self.git_sha,
            "size_bytes": self.size_bytes,
            "node_type": self.node_type,
            "extension": self.extension or None,
            "language": self.language,
            "line_count": self.line_count,
            "content_sha256": self.content_sha256,
            "depth": self.depth,
        }


@dataclass
class TreeStats:
    file_count: int = 0
    directory_count: int = 0
    total_blob_bytes: int = 0
    indexed_line_count_files: int = 0
    extension_counts: Dict[str, int] = field(default_factory=dict)
    language_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_count": self.file_count,
            "directory_count": self.directory_count,
            "total_blob_bytes": self.total_blob_bytes,
            "indexed_line_count_files": self.indexed_line_count_files,
            "extension_counts": dict(sorted(self.extension_counts.items())),
            "language_counts": dict(sorted(self.language_counts.items())),
        }


@dataclass
class SnapshotRecord:
    snapshot_id: str
    workspace_id: str
    assignment_id: str
    repo_full_name: str
    default_branch: Optional[str]
    commit_sha: str
    status: str
    captured_at: str
    error_message: Optional[str] = None
    repo_metadata: Dict[str, Any] = field(default_factory=dict)
    language_bytes: Dict[str, Any] = field(default_factory=dict)
    tree_stats: Dict[str, Any] = field(default_factory=dict)
    index_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
