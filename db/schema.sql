-- CTO Lens Repo Intelligence — structured storage (PostgreSQL)
--
-- Design goals:
--   * Relational columns for identity + query paths (repo, file, symbol, time)
--   * JSONB payloads for forward-compatible extensions (future review agents)
--   * Incremental upserts per repository / snapshot / file / commit
--   * No agent, scoring, or AI-specific columns
--
-- Apply via canonical_schema / postgres_store migrations at app startup.

-- ---------------------------------------------------------------------------
-- 1. Repository metadata (stable identity per workspace assignment)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repositories (
    repository_id   TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL,
    assignment_id   TEXT NOT NULL,
    owner           TEXT NOT NULL,
    repo_name       TEXT NOT NULL,
    repo_full_name  TEXT NOT NULL,
    default_branch  TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workspace_id, assignment_id, repo_full_name)
);

CREATE INDEX IF NOT EXISTS idx_repositories_workspace
    ON repositories (workspace_id, assignment_id);

CREATE INDEX IF NOT EXISTS idx_repositories_full_name
    ON repositories (repo_full_name);

-- ---------------------------------------------------------------------------
-- 2. Snapshots (point-in-time repository capture)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repository_snapshots (
    snapshot_id       TEXT PRIMARY KEY,
    repository_id     TEXT REFERENCES repositories (repository_id) ON DELETE CASCADE,
    workspace_id      TEXT NOT NULL,
    assignment_id     TEXT NOT NULL,
    owner             TEXT NOT NULL,
    repo_name         TEXT NOT NULL,
    repo_full_name    TEXT NOT NULL,
    default_branch    TEXT,
    head_commit_sha   TEXT NOT NULL DEFAULT '',
    last_synced_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status            TEXT NOT NULL DEFAULT 'pending',
    error_message     TEXT,
    payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
    snapshot_version  INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_repository_snapshots_workspace
    ON repository_snapshots (workspace_id, assignment_id, last_synced_at DESC);

CREATE INDEX IF NOT EXISTS idx_repository_snapshots_repository_time
    ON repository_snapshots (repository_id, last_synced_at DESC);

CREATE INDEX IF NOT EXISTS idx_repository_snapshots_repo_full_name
    ON repository_snapshots (repo_full_name, last_synced_at DESC);

-- ---------------------------------------------------------------------------
-- 3. Commits (normalized for time-range queries)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repository_commits (
    id                   BIGSERIAL PRIMARY KEY,
    snapshot_id          TEXT NOT NULL REFERENCES repository_snapshots (snapshot_id) ON DELETE CASCADE,
    repository_id        TEXT NOT NULL REFERENCES repositories (repository_id) ON DELETE CASCADE,
    commit_hash          TEXT NOT NULL,
    author               TEXT NOT NULL DEFAULT '',
    committed_at         TIMESTAMPTZ NOT NULL,
    files_changed_count  INTEGER NOT NULL DEFAULT 0,
    commit_payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (snapshot_id, commit_hash)
);

CREATE INDEX IF NOT EXISTS idx_repository_commits_repository_time
    ON repository_commits (repository_id, committed_at DESC);

CREATE INDEX IF NOT EXISTS idx_repository_commits_snapshot_time
    ON repository_commits (snapshot_id, committed_at DESC);

CREATE INDEX IF NOT EXISTS idx_repository_commits_author
    ON repository_commits (repository_id, author);

-- ---------------------------------------------------------------------------
-- 4. Code index (per-file AST index, incremental upsert)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repository_code_index (
    id                  SERIAL PRIMARY KEY,
    snapshot_id         TEXT NOT NULL REFERENCES repository_snapshots (snapshot_id) ON DELETE CASCADE,
    repository_id       TEXT REFERENCES repositories (repository_id) ON DELETE CASCADE,
    file_path           TEXT NOT NULL,
    git_sha             TEXT NOT NULL DEFAULT '',
    language            TEXT NOT NULL DEFAULT '',
    index_payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_indexed        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    code_index_version  INTEGER NOT NULL DEFAULT 1,
    UNIQUE (snapshot_id, file_path)
);

CREATE INDEX IF NOT EXISTS idx_repository_code_index_snapshot
    ON repository_code_index (snapshot_id);

CREATE INDEX IF NOT EXISTS idx_repository_code_index_path
    ON repository_code_index (snapshot_id, file_path);

CREATE INDEX IF NOT EXISTS idx_repository_code_index_repository_path
    ON repository_code_index (repository_id, file_path);

CREATE INDEX IF NOT EXISTS idx_repository_code_index_payload
    ON repository_code_index USING GIN (index_payload);

-- ---------------------------------------------------------------------------
-- 5. Code symbols (denormalized for fast symbol lookup)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repository_code_symbols (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_id     TEXT NOT NULL REFERENCES repository_snapshots (snapshot_id) ON DELETE CASCADE,
    repository_id   TEXT NOT NULL REFERENCES repositories (repository_id) ON DELETE CASCADE,
    file_path       TEXT NOT NULL,
    symbol_kind     TEXT NOT NULL CHECK (symbol_kind IN ('function', 'class', 'method')),
    symbol_name     TEXT NOT NULL,
    parent_symbol   TEXT,
    line            INTEGER NOT NULL,
    language        TEXT NOT NULL DEFAULT '',
    git_sha         TEXT NOT NULL DEFAULT '',
    symbol_payload  JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_indexed    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (snapshot_id, file_path, symbol_kind, symbol_name, line)
);

CREATE INDEX IF NOT EXISTS idx_repository_code_symbols_repo_name
    ON repository_code_symbols (repository_id, symbol_name);

CREATE INDEX IF NOT EXISTS idx_repository_code_symbols_snapshot_path
    ON repository_code_symbols (snapshot_id, file_path);

CREATE INDEX IF NOT EXISTS idx_repository_code_symbols_repo_time
    ON repository_code_symbols (repository_id, last_indexed DESC);

-- ---------------------------------------------------------------------------
-- 6. Baseline metrics (numerical snapshot metrics)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repository_baseline_metrics (
    snapshot_id      TEXT PRIMARY KEY REFERENCES repository_snapshots (snapshot_id) ON DELETE CASCADE,
    repository_id    TEXT REFERENCES repositories (repository_id) ON DELETE CASCADE,
    repo_full_name   TEXT NOT NULL DEFAULT '',
    metrics_payload  JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metrics_version  INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_repository_baseline_metrics_repo
    ON repository_baseline_metrics (repo_full_name);

CREATE INDEX IF NOT EXISTS idx_repository_baseline_metrics_repository_time
    ON repository_baseline_metrics (repository_id, computed_at DESC);
