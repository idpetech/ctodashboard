"""GitHub REST client for repository snapshot ingestion."""

from __future__ import annotations

import base64
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from services.repo_intelligence.config import github_timeout_seconds, max_commits

logger = logging.getLogger(__name__)

_GITHUB_HOSTS = frozenset({"github.com", "www.github.com"})


class GitHubRepoClientError(Exception):
    """Raised when GitHub API calls fail in a non-recoverable way."""


class GitHubRepoClient:
    """Read-only GitHub API access for repo snapshots."""

    def __init__(self, token: str, *, user_agent: str = "CTOLens-RepoSnapshot/1.0") -> None:
        if not token or not str(token).strip():
            raise GitHubRepoClientError("GitHub token is required")
        self.base_url = "https://api.github.com"
        self.timeout = github_timeout_seconds()
        self.headers = {
            "Authorization": f"token {token.strip()}",
            "Accept": "application/vnd.github+json",
            "User-Agent": user_agent,
        }

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise GitHubRepoClientError(f"GitHub request failed: {exc}") from exc

        if response.status_code == 404:
            raise GitHubRepoClientError(f"GitHub resource not found: {path}")
        if response.status_code == 401:
            raise GitHubRepoClientError("GitHub credentials are invalid or expired")
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining", "?")
            raise GitHubRepoClientError(
                f"GitHub API forbidden (rate limit remaining: {remaining})"
            )
        if response.status_code >= 400:
            body = (response.text or "")[:200]
            raise GitHubRepoClientError(f"GitHub API error {response.status_code}: {body}")
        return response.json()

    @staticmethod
    def parse_repo_identifier(value: str) -> Tuple[str, str]:
        """
        Accept GitHub repo URL or owner/name identifier.
        Examples: https://github.com/octocat/Hello-World, octocat/Hello-World
        """
        raw = (value or "").strip()
        if not raw:
            raise GitHubRepoClientError("Repository URL or identifier is required")

        if "://" in raw or raw.lower().startswith("github.com"):
            if "://" not in raw:
                raw = f"https://{raw.lstrip('/')}"
            parsed = urlparse(raw)
            if parsed.netloc.lower() not in _GITHUB_HOSTS:
                raise GitHubRepoClientError("Only github.com repository URLs are supported")
            path = (parsed.path or "").strip("/")
        else:
            path = raw.strip("/")

        if path.endswith(".git"):
            path = path[:-4]
        path = re.sub(r"/+$", "", path)

        if path.count("/") != 1:
            raise GitHubRepoClientError(
                "Repository must be owner/name or a github.com/owner/name URL"
            )
        owner, name = path.split("/", 1)
        if not owner or not name:
            raise GitHubRepoClientError("Repository owner and name are required")
        return owner, name

    @staticmethod
    def parse_repo_full_name(repo_full_name: str) -> Tuple[str, str]:
        return GitHubRepoClient.parse_repo_identifier(repo_full_name)

    def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        data = self._request("GET", f"/repos/{owner}/{repo}")
        return {
            "full_name": data.get("full_name"),
            "name": data.get("name"),
            "owner_login": (data.get("owner") or {}).get("login"),
            "default_branch": data.get("default_branch") or "main",
            "private": bool(data.get("private")),
            "pushed_at": data.get("pushed_at"),
            "updated_at": data.get("updated_at"),
        }

    def get_branch_commit_sha(self, owner: str, repo: str, branch: str) -> str:
        data = self._request("GET", f"/repos/{owner}/{repo}/branches/{branch}")
        commit = data.get("commit") or {}
        sha = commit.get("sha")
        if not sha:
            raise GitHubRepoClientError(f"Could not resolve commit for branch {branch}")
        return str(sha)

    def get_commit_tree_sha(self, owner: str, repo: str, commit_sha: str) -> str:
        data = self._request("GET", f"/repos/{owner}/{repo}/git/commits/{commit_sha}")
        tree = data.get("tree") or {}
        sha = tree.get("sha")
        if not sha:
            raise GitHubRepoClientError(f"Could not resolve tree for commit {commit_sha}")
        return str(sha)

    def get_recursive_tree(self, owner: str, repo: str, tree_sha: str) -> List[Dict[str, Any]]:
        data = self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
            params={"recursive": "1"},
        )
        if data.get("truncated"):
            raise GitHubRepoClientError(
                "GitHub tree response was truncated; repository exceeds ingestion limits"
            )
        tree = data.get("tree") or []
        return sorted(tree, key=lambda item: item.get("path") or "")

    def list_recent_commits(self, owner: str, repo: str, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        target = limit if limit is not None else max_commits()
        target = max(1, min(target, max_commits()))
        collected: List[Dict[str, Any]] = []
        page = 1

        while len(collected) < target:
            per_page = min(100, target - len(collected))
            batch = self._request(
                "GET",
                f"/repos/{owner}/{repo}/commits",
                params={"per_page": per_page, "page": page},
            )
            if not isinstance(batch, list) or not batch:
                break
            collected.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        collected = collected[:target]
        collected.sort(
            key=lambda row: (
                (row.get("commit") or {}).get("author", {}).get("date") or "",
                row.get("sha") or "",
            ),
            reverse=True,
        )
        return collected

    def get_commit_files_changed_count(self, owner: str, repo: str, commit_sha: str) -> int:
        data = self._request("GET", f"/repos/{owner}/{repo}/commits/{commit_sha}")
        files = data.get("files") or []
        return len(files)

    @staticmethod
    def commit_author_name(commit_item: Dict[str, Any]) -> str:
        author = commit_item.get("author") or {}
        if author.get("login"):
            return str(author["login"])
        commit = commit_item.get("commit") or {}
        author_block = commit.get("author") or {}
        return str(author_block.get("name") or author_block.get("email") or "unknown")

    @staticmethod
    def commit_timestamp(commit_item: Dict[str, Any]) -> str:
        commit = commit_item.get("commit") or {}
        author_block = commit.get("author") or {}
        return str(author_block.get("date") or "")

    def get_blob_content(self, owner: str, repo: str, blob_sha: str) -> Tuple[bytes, int]:
        data = self._request("GET", f"/repos/{owner}/{repo}/git/blobs/{blob_sha}")
        size = int(data.get("size") or 0)
        encoding = (data.get("encoding") or "").lower()
        raw = data.get("content") or ""
        if encoding != "base64":
            raise GitHubRepoClientError(f"Unsupported blob encoding: {encoding or 'unknown'}")
        try:
            content = base64.b64decode(raw, validate=False)
        except Exception as exc:
            raise GitHubRepoClientError(f"Failed to decode blob {blob_sha}") from exc
        return content, size
