# Repo Intelligence POC

**Status:** Infrastructure only (no AI, no findings, no dashboards)  
**Feature flag:** `ENABLE_REPO_INTELLIGENCE` (default `false`)

## Purpose

Ingest any GitHub repository via the REST API, parse its tree into a deterministic file index, and store structured metadata in Postgres for **later** analysis pipelines.

This module does **not**:

- call LLMs
- score or rank code
- produce security/cost/engineering findings
- render UI

## Components

| Layer | Module |
|-------|--------|
| Ingestion | `services/repo_intelligence/github_client.py` |
| Parsing | `services/repo_intelligence/parser.py` |
| Indexing | `services/repo_intelligence/indexer.py` |
| Orchestration | `services/repo_intelligence/snapshot_service.py` |
| Storage | `services/repo_intelligence/store.py` |
| API | `routes/api/repo_intelligence.py` |

## Postgres tables

- `repository_snapshots` — full JSON payload (metadata, folder tree, commits)
- `repo_snapshots` (legacy file-index POC) — one row per capture (commit SHA, repo metadata, language bytes, tree stats)
- `repo_file_index` — one row per file path (git SHA, size, extension, optional line count + content SHA256)

Tables are created idempotently at boot (same pattern as product analytics).

## API (auth + workspace access required)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/workspaces/<ws>/assignments/<asg>/repo-intelligence/snapshots` | Create snapshot |
| `GET` | same | List snapshots for assignment |
| `GET` | `/api/workspaces/<ws>/repo-intelligence/snapshots/<id>` | Snapshot metadata |
| `GET` | `/api/workspaces/<ws>/repo-intelligence/snapshots/<id>/files` | Paginated file index |

### Snapshot JSON shape

```json
{
  "snapshot_id": "...",
  "repository": {
    "owner": "octocat",
    "repo_name": "Hello-World",
    "full_name": "octocat/Hello-World",
    "default_branch": "main",
    "last_synced_at": "2026-06-15T12:00:00Z",
    "head_commit_sha": "abc123"
  },
  "folder_structure": { "type": "directory", "children": [] },
  "commits": [
    { "hash": "...", "author": "octocat", "timestamp": "...", "files_changed_count": 3 }
  ]
}
```

### Create snapshot body (optional)

```json
{
  "repo": "owner/name",
  "include_line_counts": true
}
```

If `repo` is omitted, the first repo from assignment GitHub config (`github_org` + `github_repos`) is used.

## Safety limits (env)

| Variable | Default | Meaning |
|----------|---------|---------|
| `REPO_INTEL_MAX_TREE_ENTRIES` | 50000 | Max Git tree nodes |
| `REPO_INTEL_MAX_BLOB_BYTES` | 262144 | Max blob size for line/hash fetch |
| `REPO_INTEL_MAX_LINE_COUNT_FILES` | 5000 | Max files to fetch for line counts |
| `REPO_INTEL_GITHUB_TIMEOUT` | 30 | HTTP timeout seconds |

## Local enable

```bash
export ENABLE_REPO_INTELLIGENCE=true
source .env.local
./venv/bin/python integrated_dashboard.py
```

### Offline deterministic test

```bash
./venv/bin/python scripts/test_repo_intelligence_index.py
```

## Determinism guarantees

- Tree paths sorted alphabetically before persist
- Extension/language aggregates use sorted keys in `tree_stats`
- GitHub `/languages` map stored with sorted keys
- Same commit SHA + repo → same file paths and git SHAs (line counts depend on blob caps)

## Next phases (out of scope here)

- Analysis workers consuming `repo_file_index`
- Incremental snapshots (compare SHAs)
- Webhooks / scheduled re-ingestion
