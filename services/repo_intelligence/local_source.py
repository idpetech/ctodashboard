"""Build repository snapshots from a local directory (no GitHub API)."""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.repo_intelligence.snapshot_models import (
    CommitMetadata,
    RepositoryMetadata,
    RepositorySnapshot,
)
from services.repo_intelligence.tree_builder import build_folder_tree, should_ignore_path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_local_root(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Local root is not a directory: {root}")
    return root


def default_repo_name(root: Path) -> str:
    return f"local/{root.name}"


def _run_git(root: Path, *args: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()


def read_local_git_metadata(root: Path) -> Tuple[str, List[CommitMetadata]]:
    """Return HEAD sha and recent commits when `.git` is present."""
    head = _run_git(root, "rev-parse", "HEAD") or ""
    if not head:
        fingerprint = _directory_fingerprint(root)
        return fingerprint, []

    log = _run_git(root, "log", "-100", "--pretty=format:%H|%an|%aI")
    commits: List[CommitMetadata] = []
    if log:
        for line in log.splitlines():
            parts = line.split("|", 2)
            if len(parts) != 3:
                continue
            commit_hash, author, timestamp = parts
            commits.append(
                CommitMetadata(
                    hash=commit_hash,
                    author=author or "unknown",
                    timestamp=timestamp or "",
                    files_changed_count=0,
                )
            )
    return head, commits


def _directory_fingerprint(root: Path) -> str:
    """Stable pseudo-commit id when git metadata is unavailable."""
    rows: List[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if should_ignore_path(rel):
            continue
        stat = path.stat()
        rows.append(f"{rel}:{stat.st_size}:{int(stat.st_mtime)}")
    digest = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
    return digest[:40]


def iter_local_tree_items(root: Path) -> List[Dict[str, Any]]:
    """Flat GitHub-style tree rows for all indexable files under root."""
    items: List[Dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if should_ignore_path(rel):
            continue
        items.append(
            {
                "path": rel,
                "type": "blob",
                "size": int(path.stat().st_size),
                # Reuse git_sha field as deterministic local content lookup key.
                "sha": rel,
            }
        )
    return items


def build_local_snapshot(
    root: Path,
    *,
    snapshot_id: Optional[str] = None,
    repo_full_name: Optional[str] = None,
) -> RepositorySnapshot:
    root = resolve_local_root(root)
    snapshot_id = snapshot_id or uuid.uuid4().hex
    full_name = (repo_full_name or default_repo_name(root)).strip()
    if "/" not in full_name:
        full_name = f"local/{full_name}"

    owner, repo_name = full_name.split("/", 1)
    head_commit_sha, commits = read_local_git_metadata(root)
    synced_at = utc_now_iso()
    if commits:
        synced_at = commits[0].timestamp or synced_at

    folder_structure = build_folder_tree(iter_local_tree_items(root))
    metadata = RepositoryMetadata(
        owner=owner,
        repo_name=repo_name,
        full_name=full_name,
        default_branch="local",
        last_synced_at=synced_at,
        head_commit_sha=head_commit_sha,
    )
    return RepositorySnapshot(
        snapshot_id=snapshot_id,
        repository=metadata,
        folder_structure=folder_structure,
        commits=commits,
        status="completed",
    )


def local_content_fetcher_text(root: Path):
    """Return UTF-8 text fetcher keyed by relative file path (stored in git_sha)."""

    root = resolve_local_root(root)

    def fetch(content_key: str) -> str:
        rel = (content_key or "").strip().lstrip("/")
        if not rel or ".." in Path(rel).parts:
            raise FileNotFoundError(f"Invalid local path key: {content_key!r}")
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        return path.read_text(encoding="utf-8", errors="replace")

    return fetch


def local_content_fetcher_bytes(root: Path):
    """Return bytes fetcher keyed by relative file path (stored in git_sha)."""

    root = resolve_local_root(root)

    def fetch(content_key: str) -> bytes:
        rel = (content_key or "").strip().lstrip("/")
        if not rel or ".." in Path(rel).parts:
            raise FileNotFoundError(f"Invalid local path key: {content_key!r}")
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        return path.read_bytes()

    return fetch
