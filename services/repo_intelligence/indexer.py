"""Build structured per-file code indexes from repository snapshots."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from services.repo_intelligence.ast_parsers.import_classifier import repo_module_roots
from services.repo_intelligence.ast_parsers.js_ts_parser import parse_js_ts
from services.repo_intelligence.ast_parsers.python_parser import parse_python
from services.repo_intelligence.config import (
    CODE_INDEX_VERSION,
    indexable_languages,
    max_code_index_bytes,
    max_code_index_files,
)
from services.repo_intelligence.github_client import GitHubRepoClient, GitHubRepoClientError
from services.repo_intelligence.language_map import (
    extension_from_path,
    is_binary_extension,
    language_for_extension,
)
from services.repo_intelligence.models.code_index import FileCodeIndex

logger = logging.getLogger(__name__)

_INDEXABLE_LANGUAGE_SET = frozenset(indexable_languages())


class CodeIndexError(Exception):
    """User-visible code index error."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def flatten_snapshot_files(folder_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten snapshot folder_structure into sorted file rows."""
    files: List[Dict[str, Any]] = []

    def walk(node: Dict[str, Any]) -> None:
        if node.get("type") == "file":
            files.append(
                {
                    "path": node.get("path") or "",
                    "git_sha": node.get("git_sha") or "",
                    "size_bytes": int(node.get("size_bytes") or 0),
                }
            )
            return
        for child in node.get("children") or []:
            walk(child)

    walk(folder_structure or {})
    files.sort(key=lambda row: row.get("path") or "")
    return files


def index_file_content(
    file_path: str,
    content: str,
    *,
    language: str,
    repo_file_paths: Sequence[str],
    indexed_at: str,
    git_sha: str = "",
) -> FileCodeIndex:
    """Parse one file's source into a deterministic code index entry."""
    repo_roots = repo_module_roots(repo_file_paths)
    functions: List[Any] = []
    classes: List[Any] = []
    imports: List[Any] = []

    if language == "Python":
        functions, classes, imports = parse_python(content, repo_roots=repo_roots)
    elif language in {"JavaScript", "TypeScript"}:
        functions, classes, imports = parse_js_ts(content, repo_roots=repo_roots)

    return FileCodeIndex(
        file_path=file_path,
        language=language,
        symbols={
            "functions": [fn.to_dict() for fn in functions],
            "classes": [cls.to_dict() for cls in classes],
        },
        imports=imports,
        last_indexed=indexed_at,
        git_sha=git_sha,
    )


def should_index_file(file_path: str, size_bytes: int) -> bool:
    ext = extension_from_path(file_path)
    if is_binary_extension(ext):
        return False
    language = language_for_extension(ext)
    if not language or language not in _INDEXABLE_LANGUAGE_SET:
        return False
    # Tree metadata can report size 0 for empty source files; blob fetch is authoritative.
    if size_bytes > max_code_index_bytes():
        return False
    return True


def summarize_index_eligibility(snapshot_files: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Count how many snapshot files are eligible for AST indexing (diagnostics only)."""
    skipped = {"language": 0, "binary": 0, "too_large": 0, "empty_path": 0}
    eligible = 0
    for row in snapshot_files:
        path = row.get("path") or ""
        if not path:
            skipped["empty_path"] += 1
            continue
        size_bytes = int(row.get("size_bytes") or 0)
        ext = extension_from_path(path)
        if is_binary_extension(ext):
            skipped["binary"] += 1
            continue
        language = language_for_extension(ext)
        if not language or language not in _INDEXABLE_LANGUAGE_SET:
            skipped["language"] += 1
            continue
        if size_bytes > max_code_index_bytes():
            skipped["too_large"] += 1
            continue
        eligible += 1
    return {
        "total_files": len(snapshot_files),
        "index_eligible": eligible,
        "indexable_languages": sorted(_INDEXABLE_LANGUAGE_SET),
        "skipped": skipped,
    }


def build_code_index(
    snapshot_files: List[Dict[str, Any]],
    *,
    content_fetcher,
    indexed_at: Optional[str] = None,
) -> List[FileCodeIndex]:
    """
    Build code index entries for all indexable files in a snapshot file list.

    content_fetcher: callable(git_sha) -> str (decoded UTF-8 text)
    """
    when = indexed_at or _utc_now_iso()
    all_paths = [row.get("path") or "" for row in snapshot_files if row.get("path")]
    entries: List[FileCodeIndex] = []
    indexed_count = 0
    file_cap = max_code_index_files()

    for row in snapshot_files:
        path = row.get("path") or ""
        if not path:
            continue

        ext = extension_from_path(path)
        language = language_for_extension(ext) or "Unknown"
        git_sha = str(row.get("git_sha") or "")
        size_bytes = int(row.get("size_bytes") or 0)

        if not should_index_file(path, size_bytes):
            continue
        if indexed_count >= file_cap:
            logger.info("Code index file cap reached (%s); skipping remaining files", file_cap)
            break

        try:
            content = content_fetcher(git_sha)
        except Exception as exc:
            logger.warning("Skipping code index for %s: %s", path, exc)
            entries.append(FileCodeIndex.empty(path, language, last_indexed=when, git_sha=git_sha))
            indexed_count += 1
            continue

        if len(content.encode("utf-8")) > max_code_index_bytes():
            logger.info("Code index skipped (content too large): %s", path)
            continue

        entries.append(
            index_file_content(
                path,
                content,
                language=language,
                repo_file_paths=all_paths,
                indexed_at=when,
                git_sha=git_sha,
            )
        )
        indexed_count += 1

    entries.sort(key=lambda row: row.file_path)
    return entries


def build_code_index_from_snapshot(
    client: GitHubRepoClient,
    owner: str,
    repo: str,
    snapshot_payload: Dict[str, Any],
    *,
    indexed_at: Optional[str] = None,
) -> List[FileCodeIndex]:
    """Fetch file contents from GitHub and build a code index for a stored snapshot."""
    files = flatten_snapshot_files(snapshot_payload.get("folder_structure") or {})

    def fetch(git_sha: str) -> str:
        content_bytes, _size = client.get_blob_content(owner, repo, git_sha)
        return content_bytes.decode("utf-8", errors="replace")

    when = (
        indexed_at or snapshot_payload.get("repository", {}).get("last_synced_at") or _utc_now_iso()
    )
    return build_code_index(files, content_fetcher=fetch, indexed_at=when)


def build_and_store_code_index(
    snapshot_id: str,
    workspace_id: str,
    *,
    token: str,
) -> Dict[str, Any]:
    """Load snapshot from DB, build code index, persist per-file rows."""
    from services.repo_intelligence.code_index_store import get_code_index_store
    from services.repo_intelligence.store import get_store

    record = get_store().get_snapshot(snapshot_id)
    if not record or record.get("workspace_id") != workspace_id:
        raise CodeIndexError("Snapshot not found")
    if record.get("status") != "completed":
        raise CodeIndexError("Snapshot is not completed")

    payload = record.get("payload") or {}
    repo_info = payload.get("repository") or {}
    full_name = str(repo_info.get("full_name") or record.get("repo_full_name") or "")
    if "/" not in full_name:
        raise CodeIndexError("Snapshot is missing repository full name")

    owner, repo = full_name.split("/", 1)
    client = GitHubRepoClient(token)

    try:
        entries = build_code_index_from_snapshot(client, owner, repo, payload)
    except GitHubRepoClientError as exc:
        raise CodeIndexError(str(exc)) from exc

    store = get_code_index_store()
    store.replace_snapshot_index(snapshot_id, entries)

    return {
        "snapshot_id": snapshot_id,
        "indexed_files": len(entries),
        "code_index_version": CODE_INDEX_VERSION,
        "entries": [entry.to_dict() for entry in entries],
    }
