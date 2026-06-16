"""Capture and persist deterministic GitHub repository snapshots."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.assignment_metrics_config import (
    connector_credentials_ready,
    github_metrics_config,
    missing_connector_message,
)
from services.repo_intelligence.config import SNAPSHOT_VERSION, is_repo_intelligence_enabled
from services.repo_intelligence.github_client import GitHubRepoClient, GitHubRepoClientError
from services.repo_intelligence.snapshot_models import (
    CommitMetadata,
    RepositoryMetadata,
    RepositorySnapshot,
)
from services.repo_intelligence.store import get_store
from services.repo_intelligence.tree_builder import build_folder_tree

logger = logging.getLogger(__name__)


class RepoSnapshotError(Exception):
    """User-visible snapshot error."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_repo_input(repo_input: str) -> tuple[str, str]:
    return GitHubRepoClient.parse_repo_identifier(repo_input)


def build_repository_snapshot(
    client: GitHubRepoClient,
    repo_input: str,
    *,
    snapshot_id: str,
    synced_at: Optional[str] = None,
) -> RepositorySnapshot:
    """Fetch GitHub data and assemble a JSON-serializable snapshot (no persistence)."""
    owner, repo_name = parse_repo_input(repo_input)
    repo_meta = client.get_repo(owner, repo_name)
    default_branch = repo_meta.get("default_branch") or "main"
    head_commit_sha = client.get_branch_commit_sha(owner, repo_name, default_branch)
    tree_sha = client.get_commit_tree_sha(owner, repo_name, head_commit_sha)
    tree_items = client.get_recursive_tree(owner, repo_name, tree_sha)
    folder_structure = build_folder_tree(tree_items)

    commit_items = client.list_recent_commits(owner, repo_name)
    commits: List[CommitMetadata] = []
    for item in commit_items:
        sha = str(item.get("sha") or "")
        if not sha:
            continue
        files_changed_count = client.get_commit_files_changed_count(owner, repo_name, sha)
        commits.append(
            CommitMetadata(
                hash=sha,
                author=GitHubRepoClient.commit_author_name(item),
                timestamp=GitHubRepoClient.commit_timestamp(item),
                files_changed_count=files_changed_count,
            )
        )

    commits.sort(key=lambda row: (row.timestamp, row.hash), reverse=True)

    full_name = str(repo_meta.get("full_name") or f"{owner}/{repo_name}")
    metadata = RepositoryMetadata(
        owner=owner,
        repo_name=repo_name,
        full_name=full_name,
        default_branch=default_branch,
        last_synced_at=synced_at or _utc_now_iso(),
        head_commit_sha=head_commit_sha,
    )

    return RepositorySnapshot(
        snapshot_id=snapshot_id,
        repository=metadata,
        folder_structure=folder_structure,
        commits=commits,
        status="completed",
        snapshot_version=SNAPSHOT_VERSION,
    )


def capture_repository_snapshot(
    token: str,
    repo_input: str,
    *,
    workspace_id: str,
    assignment_id: str,
) -> Dict[str, Any]:
    """Ingest repo snapshot from GitHub and store in repository_snapshots."""
    if not is_repo_intelligence_enabled():
        raise RepoSnapshotError("Repo intelligence is disabled")

    client = GitHubRepoClient(token)
    store = get_store()
    owner, repo_name = parse_repo_input(repo_input)
    full_name = f"{owner}/{repo_name}"
    snapshot_id: Optional[str] = None

    try:
        snapshot_id = store.create_snapshot_pending(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            owner=owner,
            repo_name=repo_name,
            repo_full_name=full_name,
        )
        snapshot = build_repository_snapshot(client, repo_input, snapshot_id=snapshot_id)
        store.save_snapshot(snapshot)
        return snapshot.to_dict()
    except (GitHubRepoClientError, RepoSnapshotError) as exc:
        if snapshot_id:
            store.mark_snapshot_failed(snapshot_id, str(exc))
        raise RepoSnapshotError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Repository snapshot failed for %s", repo_input)
        if snapshot_id:
            store.mark_snapshot_failed(snapshot_id, str(exc))
        raise RepoSnapshotError(f"Repository snapshot failed: {exc}") from exc


def _resolve_repo_input(
    workspace_id: str,
    assignment_id: str,
    assignment: Dict[str, Any],
    repo_override: Optional[str],
) -> str:
    if repo_override and repo_override.strip():
        return repo_override.strip()

    metrics_config = assignment.get("metrics_config") or {}
    if isinstance(metrics_config, str):
        import json

        try:
            metrics_config = json.loads(metrics_config)
        except json.JSONDecodeError:
            metrics_config = {}

    github_cfg = metrics_config.get("github") or {}
    gh = github_metrics_config(workspace_id, assignment_id, github_cfg)
    org = (gh.get("org") or "").strip()
    repos = gh.get("repos") or []
    if not org or not repos:
        raise RepoSnapshotError(
            "GitHub org and at least one repo are required. "
            "Configure github_org and github_repos on the assignment, "
            'or pass {"repo": "owner/name"} or a GitHub URL in the request body.'
        )
    first_repo = str(repos[0]).strip()
    if "/" in first_repo:
        return first_repo
    return f"{org}/{first_repo}"


def create_repo_snapshot(
    workspace_id: str,
    assignment_id: str,
    assignment: Dict[str, Any],
    *,
    repo_input: Optional[str] = None,
    repo_full_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Assignment-scoped snapshot capture using stored GitHub credentials."""
    if not connector_credentials_ready(workspace_id, assignment_id, "github"):
        raise RepoSnapshotError(missing_connector_message("github"))

    resolved = (
        repo_input
        or repo_full_name
        or _resolve_repo_input(workspace_id, assignment_id, assignment, None)
    )

    from services.auth.credential_service import CredentialService

    creds = CredentialService().get_github_credentials(workspace_id, assignment_id)
    token = creds.get("token")
    if not token:
        raise RepoSnapshotError(missing_connector_message("github"))

    payload = capture_repository_snapshot(
        token,
        resolved,
        workspace_id=workspace_id,
        assignment_id=assignment_id,
    )
    return {"success": True, "snapshot": payload}


def list_snapshots(
    workspace_id: str, assignment_id: str, *, limit: int = 20
) -> List[Dict[str, Any]]:
    if not is_repo_intelligence_enabled():
        return []
    return get_store().list_snapshots(workspace_id, assignment_id, limit=limit)


def get_snapshot(workspace_id: str, snapshot_id: str) -> Optional[Dict[str, Any]]:
    if not is_repo_intelligence_enabled():
        return None
    record = get_store().get_snapshot(snapshot_id)
    if not record or record.get("workspace_id") != workspace_id:
        return None
    return record.get("payload") or record


def list_file_index(
    workspace_id: str,
    snapshot_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """Flatten folder_structure files for backward-compatible API consumers."""
    record = get_snapshot(workspace_id, snapshot_id)
    if not record:
        return {"files": [], "total": 0}

    files = _flatten_folder_files(record.get("folder_structure") or {})
    files.sort(key=lambda row: row.get("path") or "")
    total = len(files)
    page = files[offset : offset + limit]
    return {"files": page, "total": total, "limit": limit, "offset": offset}


def _flatten_folder_files(node: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    node_type = node.get("type")
    path = node.get("path") or prefix
    if node_type == "file":
        out.append(
            {
                "path": path,
                "git_sha": node.get("git_sha"),
                "size_bytes": node.get("size_bytes"),
                "node_type": "blob",
            }
        )
        return out
    for child in node.get("children") or []:
        out.extend(_flatten_folder_files(child))
    return out
