#!/usr/bin/env python3
"""
End-to-end Repo Intelligence CLI (no Flask).

Runs: GitHub ingest → repository snapshot → code index → baseline metrics.

Examples:
  export GITHUB_TOKEN=ghp_...
  ./venv/bin/python scripts/repo_intelligence_e2e.py --repo octocat/Hello-World

  # Save JSON artifacts locally
  ./venv/bin/python scripts/repo_intelligence_e2e.py \\
    --repo https://github.com/owner/repo --out /tmp/repo-intel

  # Persist to Postgres (uses assignment GitHub creds from DB)
  export ENABLE_REPO_INTELLIGENCE=true
  ./venv/bin/python scripts/repo_intelligence_e2e.py \\
    --repo owner/repo --persist \\
    --workspace admin_workspace --assignment YOUR_ASSIGNMENT_ID
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from dotenv import load_dotenv

load_dotenv()
if not os.getenv("RAILWAY_ENVIRONMENT"):
    load_dotenv(ROOT / ".env.local", override=True)


def _resolve_token(args: argparse.Namespace) -> str:
    if args.token:
        return args.token.strip()
    env_token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if env_token:
        return env_token
    if args.workspace and args.assignment:
        from services.auth.credential_service import CredentialService

        creds = CredentialService().get_github_credentials(args.workspace, args.assignment)
        token = (creds.get("token") or "").strip()
        if token:
            return token
    raise SystemExit(
        "GitHub token required: use --token, GITHUB_TOKEN env, or --workspace + --assignment with stored creds"
    )


def _print_summary(
    snapshot: Dict[str, Any],
    entries: List[Dict[str, Any]],
    *,
    index_skipped: bool = False,
    index_eligibility: Dict[str, Any] | None = None,
) -> None:
    from services.repo_intelligence.indexer import (
        flatten_snapshot_files,
        summarize_index_eligibility,
    )

    repo = snapshot.get("repository") or {}
    print("\n=== Repository snapshot ===")
    print(f"  snapshot_id:   {snapshot.get('snapshot_id')}")
    print(f"  full_name:     {repo.get('full_name')}")
    print(f"  default_branch:{repo.get('default_branch')}")
    print(f"  head_commit:   {repo.get('head_commit_sha', '')[:12]}...")
    print(f"  last_synced:   {repo.get('last_synced_at')}")
    print(f"  commits:       {len(snapshot.get('commits') or [])}")

    snapshot_files = flatten_snapshot_files(snapshot.get("folder_structure") or {})
    eligibility = index_eligibility or summarize_index_eligibility(snapshot_files)
    print(f"  total_files:   {eligibility.get('total_files')}")

    children = (snapshot.get("folder_structure") or {}).get("children") or []
    print(f"  root entries:  {len(children)}")

    print("\n=== Code index ===")
    if index_skipped:
        print("  status:        skipped (--skip-index)")
        print(f"  index_eligible:{eligibility.get('index_eligible')} (Python/JS/TS only)")
        return

    print(f"  indexed_files: {len(entries)}")
    print(f"  index_eligible:{eligibility.get('index_eligible')} (Python/JS/TS only)")
    skipped = eligibility.get("skipped") or {}
    if not entries and eligibility.get("index_eligible"):
        print("  note:          eligible files exist but none were indexed (check logs / GitHub token)")
    elif not entries and skipped.get("language"):
        langs = ", ".join(eligibility.get("indexable_languages") or [])
        print(f"  note:          no {langs} files in snapshot ({skipped.get('language')} files skipped by language filter)")

    if entries:
        sample = entries[0]
        print(f"  sample file:   {sample.get('file_path')} ({sample.get('language')})")
        syms = sample.get("symbols") or {}
        print(f"    functions:   {len(syms.get('functions') or [])}")
        print(f"    classes:     {len(syms.get('classes') or [])}")
        print(f"    imports:     {len(sample.get('imports') or [])}")

    py_files = [e for e in entries if e.get("language") == "Python"]
    js_files = [e for e in entries if e.get("language") in {"JavaScript", "TypeScript"}]
    print(f"  Python:        {len(py_files)}")
    print(f"  JS/TS:         {len(js_files)}")


def _print_metrics_summary(metrics: Dict[str, Any]) -> None:
    print("\n=== Baseline metrics ===")
    size = metrics.get("repo_size") or {}
    loc = metrics.get("loc_profile") or {}
    print(f"  total_files:       {size.get('total_files')}")
    print(f"  total_loc:         {size.get('total_loc')} ({size.get('estimation_method')})")
    print(f"  measured_loc:      {size.get('measured_loc')} ({size.get('measured_files')} files)")
    print(f"  projected_loc:     {size.get('projected_loc')} ({size.get('projected_files')} files)")
    print(f"  sample_files:      {loc.get('sample_files')}")
    print(f"  avg_bytes/line:    {loc.get('avg_bytes_per_line')}")
    print(f"  avg_loc/file:      {loc.get('avg_loc_per_file')}")
    print(f"  max_loc/file:      {loc.get('max_loc_per_file')} ({loc.get('max_loc_file_path')})")
    print(f"  max_line_length:   {loc.get('max_line_length')}")

    langs = metrics.get("language_distribution") or {}
    if langs:
        top = sorted(langs.items(), key=lambda row: -row[1].get("file_count", 0))[:5]
        print("  languages:")
        for name, share in top:
            print(f"    {name}: {share.get('file_count')} files ({share.get('percent')})")

    contrib = metrics.get("contributors") or {}
    print(f"  contributors:  {contrib.get('total')}")

    activity = metrics.get("activity") or {}
    print(f"  commits 7d:    {activity.get('commits_last_7_days')}")
    print(f"  commits 30d:   {activity.get('commits_last_30_days')}")
    print(f"  last commit:   {activity.get('last_commit_timestamp')}")
    print(f"  churn/commit:  {activity.get('churn_rate_files_per_commit')}")


def _write_artifacts(
    out_dir: Path,
    snapshot: Dict[str, Any],
    entries: List[Dict[str, Any]],
    metrics: Dict[str, Any] | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap_path = out_dir / "snapshot.json"
    index_path = out_dir / "code_index.json"
    snap_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_path.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nWrote {snap_path}")
    print(f"Wrote {index_path}")
    if metrics is not None:
        metrics_path = out_dir / "metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {metrics_path}")


def _run_in_memory(repo: str, token: str, *, skip_index: bool) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    from services.repo_intelligence.github_client import GitHubRepoClient, GitHubRepoClientError
    from services.repo_intelligence.indexer import build_code_index_from_snapshot
    from services.repo_intelligence.snapshot_service import build_repository_snapshot

    client = GitHubRepoClient(token)
    snapshot_id = uuid.uuid4().hex
    print(f"Building snapshot for {repo} ...")
    try:
        snap = build_repository_snapshot(client, repo, snapshot_id=snapshot_id)
        snapshot = snap.to_dict()
    except GitHubRepoClientError as exc:
        raise SystemExit(f"Snapshot failed: {exc}") from exc

    entries: List[Dict[str, Any]] = []
    if skip_index:
        print("Skipping code index (--skip-index)")
        return snapshot, entries

    owner, repo_name = client.parse_repo_identifier(repo)
    print("Building code index (fetching file blobs from GitHub) ...")
    try:
        index_entries = build_code_index_from_snapshot(client, owner, repo_name, snapshot)
    except GitHubRepoClientError as exc:
        raise SystemExit(f"Code index failed: {exc}") from exc

    entries = [entry.to_dict() for entry in index_entries]
    return snapshot, entries


def _run_persist(
    repo: str,
    token: str,
    workspace_id: str,
    assignment_id: str,
    *,
    skip_index: bool,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    from services.repo_intelligence.github_client import GitHubRepoClient, GitHubRepoClientError
    from services.repo_intelligence.indexer import CodeIndexError, build_and_store_code_index
    from services.repo_intelligence.snapshot_service import build_repository_snapshot
    from services.repo_intelligence.store import get_store

    client = GitHubRepoClient(token)
    owner, repo_name = client.parse_repo_identifier(repo)
    full_name = f"{owner}/{repo_name}"
    store = get_store()

    print(f"Persisting snapshot for {full_name} ...")

    snapshot_id = store.create_snapshot_pending(
        workspace_id=workspace_id,
        assignment_id=assignment_id,
        owner=owner,
        repo_name=repo_name,
        repo_full_name=full_name,
    )
    try:
        snap = build_repository_snapshot(client, repo, snapshot_id=snapshot_id)
        store.save_snapshot(snap)
        snapshot = snap.to_dict()
    except GitHubRepoClientError as exc:
        store.mark_snapshot_failed(snapshot_id, str(exc))
        raise SystemExit(f"Snapshot failed: {exc}") from exc

    entries: List[Dict[str, Any]] = []
    if skip_index:
        print("Skipping code index (--skip-index)")
        return snapshot, entries

    print("Building and storing code index ...")
    try:
        result = build_and_store_code_index(snapshot_id, workspace_id, token=token)
    except CodeIndexError as exc:
        raise SystemExit(f"Code index failed: {exc}") from exc

    entries = result.get("entries") or []
    print(f"Stored snapshot_id={snapshot_id} indexed_files={result.get('indexed_files')}")
    return snapshot, entries


def _compute_metrics(
    snapshot: Dict[str, Any],
    *,
    persist: bool,
    workspace_id: str,
    token: str | None = None,
) -> Dict[str, Any]:
    from services.repo_intelligence.metrics_engine import (
        _github_content_fetcher,
        build_and_store_baseline_metrics,
        compute_baseline_metrics,
    )

    print("Computing baseline metrics ...")
    if persist:
        snapshot_id = str(snapshot.get("snapshot_id") or "")
        return build_and_store_baseline_metrics(snapshot_id, workspace_id)

    content_fetcher = None
    full_name = str((snapshot.get("repository") or {}).get("full_name") or "")
    if token and "/" in full_name:
        owner, repo_name = full_name.split("/", 1)
        content_fetcher = _github_content_fetcher(token, owner, repo_name)
        print("  LOC: sampling file contents for dynamic bytes/line average")

    return compute_baseline_metrics(snapshot, content_fetcher=content_fetcher).to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo Intelligence E2E CLI (no Flask)")
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPO", "").strip(),
        help="GitHub repo URL or owner/name (or GITHUB_REPO env)",
    )
    parser.add_argument("--token", help="GitHub PAT (or GITHUB_TOKEN env)")
    parser.add_argument("--workspace", help="Workspace ID for --persist or DB token lookup")
    parser.add_argument("--assignment", help="Assignment ID for --persist or DB token lookup")
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Save snapshot + code index to Postgres (requires DATABASE_URL)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write snapshot.json and code_index.json to this directory",
    )
    parser.add_argument("--skip-index", action="store_true", help="Only build repository snapshot")
    parser.add_argument("--skip-metrics", action="store_true", help="Skip baseline metrics computation")
    parser.add_argument("--json", action="store_true", help="Print full JSON to stdout")
    args = parser.parse_args()

    if not args.repo:
        parser.error("--repo or GITHUB_REPO is required")

    token = _resolve_token(args)

    if args.persist:
        if not args.workspace or not args.assignment:
            parser.error("--persist requires --workspace and --assignment")
        snapshot, entries = _run_persist(
            args.repo,
            token,
            args.workspace,
            args.assignment,
            skip_index=args.skip_index,
        )
    else:
        snapshot, entries = _run_in_memory(args.repo, token, skip_index=args.skip_index)

    metrics: Dict[str, Any] | None = None
    if not args.skip_metrics:
        metrics = _compute_metrics(
            snapshot,
            persist=bool(args.persist),
            workspace_id=args.workspace or "",
            token=token,
        )
        _print_metrics_summary(metrics)

    _print_summary(snapshot, entries, index_skipped=bool(args.skip_index))

    if args.out:
        _write_artifacts(args.out, snapshot, entries, metrics)

    if args.json:
        payload: Dict[str, Any] = {"snapshot": snapshot, "code_index": entries}
        if metrics is not None:
            payload["metrics"] = metrics
        print(json.dumps(payload, indent=2, sort_keys=True))

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
