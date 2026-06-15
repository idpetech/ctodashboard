"""JSON-serializable models for repository snapshots."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RepositoryMetadata:
    owner: str
    repo_name: str
    full_name: str
    default_branch: str
    last_synced_at: str
    head_commit_sha: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommitMetadata:
    hash: str
    author: str
    timestamp: str
    files_changed_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FolderNode:
    """Recursive directory tree node (files and directories)."""

    name: str
    path: str
    type: str
    children: List[FolderNode] = field(default_factory=list)
    size_bytes: Optional[int] = None
    git_sha: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "name": self.name,
            "path": self.path,
            "type": self.type,
        }
        if self.size_bytes is not None:
            data["size_bytes"] = self.size_bytes
        if self.git_sha:
            data["git_sha"] = self.git_sha
        if self.type == "directory":
            data["children"] = [child.to_dict() for child in self.children]
        return data


@dataclass
class RepositorySnapshot:
    snapshot_id: str
    repository: RepositoryMetadata
    folder_structure: Dict[str, Any]
    commits: List[CommitMetadata]
    status: str = "completed"
    snapshot_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "status": self.status,
            "snapshot_version": self.snapshot_version,
            "repository": self.repository.to_dict(),
            "folder_structure": self.folder_structure,
            "commits": [c.to_dict() for c in self.commits],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepositorySnapshot:
        repo = data.get("repository") or {}
        commits_raw = data.get("commits") or []
        return cls(
            snapshot_id=str(data.get("snapshot_id") or ""),
            status=str(data.get("status") or "completed"),
            snapshot_version=int(data.get("snapshot_version") or 1),
            repository=RepositoryMetadata(
                owner=str(repo.get("owner") or ""),
                repo_name=str(repo.get("repo_name") or ""),
                full_name=str(repo.get("full_name") or ""),
                default_branch=str(repo.get("default_branch") or "main"),
                last_synced_at=str(repo.get("last_synced_at") or ""),
                head_commit_sha=str(repo.get("head_commit_sha") or ""),
            ),
            folder_structure=data.get("folder_structure") or {},
            commits=[
                CommitMetadata(
                    hash=str(c.get("hash") or ""),
                    author=str(c.get("author") or ""),
                    timestamp=str(c.get("timestamp") or ""),
                    files_changed_count=int(c.get("files_changed_count") or 0),
                )
                for c in commits_raw
            ],
        )
