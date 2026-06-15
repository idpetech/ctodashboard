"""
Canonical PostgreSQL schema for CTO Dashboard.

Single source of truth for DDL and table names. All application SQL must use
TABLES.* names below. Do not duplicate CREATE TABLE statements elsewhere.
"""

from typing import List, Optional

SCHEMA_NAME = "ctodashboard"


class _Tables:
    USERS = "users"
    WORKSPACES = "workspaces"
    ASSIGNMENTS = "assignments"
    CREDENTIALS = "credentials"
    AUDIT_LOGS = "audit_logs"
    SCHEMA_VERSION = "schema_version"
    ANALYTICS_EVENTS = "analytics_events"
    ANALYTICS_SESSIONS = "analytics_sessions"
    ANALYTICS_USER_PROFILES = "analytics_user_profiles"
    REPO_SNAPSHOTS = "repo_snapshots"
    REPO_FILE_INDEX = "repo_file_index"
    REPOSITORIES = "repositories"
    REPOSITORY_SNAPSHOTS = "repository_snapshots"
    REPOSITORY_COMMITS = "repository_commits"
    REPOSITORY_CODE_SYMBOLS = "repository_code_symbols"
    REPOSITORY_CODE_INDEX = "repository_code_index"
    REPOSITORY_BASELINE_METRICS = "repository_baseline_metrics"


TABLES = _Tables()

REQUIRED_TABLES: List[str] = [
    TABLES.USERS,
    TABLES.WORKSPACES,
    TABLES.ASSIGNMENTS,
    TABLES.CREDENTIALS,
    TABLES.AUDIT_LOGS,
]

DDL_STATEMENTS: List[str] = [
    f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}",
    f"COMMENT ON SCHEMA {SCHEMA_NAME} IS 'CTO Dashboard application data'",
    f"SET search_path TO {SCHEMA_NAME}, public",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.USERS} (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        display_name TEXT,
        encrypted_password_data BYTEA,
        workspaces TEXT,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'active',
        preferences TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.WORKSPACES} (
        id SERIAL PRIMARY KEY,
        workspace_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        settings TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.ASSIGNMENTS} (
        id SERIAL PRIMARY KEY,
        assignment_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        name TEXT,
        description TEXT,
        team_size INTEGER,
        monthly_burn_rate INTEGER,
        target_monthly_burn INTEGER,
        status TEXT DEFAULT 'active',
        portfolio_id TEXT DEFAULT 'default',
        metrics_config TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(assignment_id, workspace_id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.CREDENTIALS} (
        id SERIAL PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        connector_type TEXT NOT NULL,
        encrypted_credentials BYTEA NOT NULL,
        auth_configured BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(workspace_id, assignment_id, connector_type)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.AUDIT_LOGS} (
        id SERIAL PRIMARY KEY,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        user_email TEXT,
        workspace_id TEXT,
        connector_type TEXT,
        success BOOLEAN,
        error_message TEXT,
        ip_address TEXT,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.ANALYTICS_SESSIONS} (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ended_at TIMESTAMP,
        duration_seconds INTEGER,
        event_count INTEGER NOT NULL DEFAULT 0,
        last_event_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.ANALYTICS_EVENTS} (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        event_name TEXT NOT NULL,
        occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.ANALYTICS_USER_PROFILES} (
        user_id TEXT PRIMARY KEY,
        first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        has_activated BOOLEAN NOT NULL DEFAULT FALSE,
        first_activation_time TIMESTAMP
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_analytics_events_user_time ON {TABLES.ANALYTICS_EVENTS} (user_id, occurred_at)",
    f"CREATE INDEX IF NOT EXISTS idx_analytics_events_session ON {TABLES.ANALYTICS_EVENTS} (session_id)",
    f"CREATE INDEX IF NOT EXISTS idx_analytics_events_name_time ON {TABLES.ANALYTICS_EVENTS} (event_name, occurred_at)",
    f"CREATE INDEX IF NOT EXISTS idx_analytics_sessions_user_started ON {TABLES.ANALYTICS_SESSIONS} (user_id, started_at)",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.REPO_SNAPSHOTS} (
        snapshot_id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        repo_full_name TEXT NOT NULL,
        default_branch TEXT,
        commit_sha TEXT NOT NULL,
        captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'pending',
        error_message TEXT,
        repo_metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        language_bytes JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        tree_stats JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        index_version INTEGER NOT NULL DEFAULT 1
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_repo_snapshots_workspace ON {TABLES.REPO_SNAPSHOTS} (workspace_id, assignment_id, captured_at DESC)",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.REPO_FILE_INDEX} (
        id SERIAL PRIMARY KEY,
        snapshot_id TEXT NOT NULL REFERENCES {TABLES.REPO_SNAPSHOTS}(snapshot_id) ON DELETE CASCADE,
        path TEXT NOT NULL,
        git_sha TEXT NOT NULL,
        size_bytes BIGINT NOT NULL,
        node_type TEXT NOT NULL,
        extension TEXT,
        language TEXT,
        line_count INTEGER,
        content_sha256 TEXT,
        depth INTEGER NOT NULL DEFAULT 0,
        UNIQUE(snapshot_id, path)
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_repo_file_index_snapshot ON {TABLES.REPO_FILE_INDEX} (snapshot_id)",
    f"CREATE INDEX IF NOT EXISTS idx_repo_file_index_path ON {TABLES.REPO_FILE_INDEX} (snapshot_id, path)",

    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.REPOSITORIES} (
        repository_id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        owner TEXT NOT NULL,
        repo_name TEXT NOT NULL,
        repo_full_name TEXT NOT NULL,
        default_branch TEXT,
        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (workspace_id, assignment_id, repo_full_name)
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_repositories_workspace ON {TABLES.REPOSITORIES} (workspace_id, assignment_id)",
    f"CREATE INDEX IF NOT EXISTS idx_repositories_full_name ON {TABLES.REPOSITORIES} (repo_full_name)",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.REPOSITORY_SNAPSHOTS} (
        snapshot_id TEXT PRIMARY KEY,
        repository_id TEXT REFERENCES {TABLES.REPOSITORIES}(repository_id) ON DELETE CASCADE,
        workspace_id TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        owner TEXT NOT NULL,
        repo_name TEXT NOT NULL,
        repo_full_name TEXT NOT NULL,
        default_branch TEXT,
        head_commit_sha TEXT NOT NULL DEFAULT '',
        last_synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'pending',
        error_message TEXT,
        payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        snapshot_version INTEGER NOT NULL DEFAULT 1
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_repository_snapshots_workspace ON {TABLES.REPOSITORY_SNAPSHOTS} (workspace_id, assignment_id, last_synced_at DESC)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_snapshots_repository_time ON {TABLES.REPOSITORY_SNAPSHOTS} (repository_id, last_synced_at DESC)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_snapshots_repo_full_name ON {TABLES.REPOSITORY_SNAPSHOTS} (repo_full_name, last_synced_at DESC)",

    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.REPOSITORY_COMMITS} (
        id BIGSERIAL PRIMARY KEY,
        snapshot_id TEXT NOT NULL REFERENCES {TABLES.REPOSITORY_SNAPSHOTS}(snapshot_id) ON DELETE CASCADE,
        repository_id TEXT NOT NULL REFERENCES {TABLES.REPOSITORIES}(repository_id) ON DELETE CASCADE,
        commit_hash TEXT NOT NULL,
        author TEXT NOT NULL DEFAULT '',
        committed_at TIMESTAMPTZ NOT NULL,
        files_changed_count INTEGER NOT NULL DEFAULT 0,
        commit_payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        UNIQUE (snapshot_id, commit_hash)
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_repository_commits_repository_time ON {TABLES.REPOSITORY_COMMITS} (repository_id, committed_at DESC)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_commits_snapshot_time ON {TABLES.REPOSITORY_COMMITS} (snapshot_id, committed_at DESC)",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.REPOSITORY_CODE_INDEX} (
        id SERIAL PRIMARY KEY,
        snapshot_id TEXT NOT NULL REFERENCES {TABLES.REPOSITORY_SNAPSHOTS}(snapshot_id) ON DELETE CASCADE,
        repository_id TEXT REFERENCES {TABLES.REPOSITORIES}(repository_id) ON DELETE CASCADE,
        file_path TEXT NOT NULL,
        git_sha TEXT NOT NULL DEFAULT '',
        language TEXT NOT NULL DEFAULT '',
        index_payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        last_indexed TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        code_index_version INTEGER NOT NULL DEFAULT 1,
        UNIQUE(snapshot_id, file_path)
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_repository_code_index_snapshot ON {TABLES.REPOSITORY_CODE_INDEX} (snapshot_id)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_code_index_path ON {TABLES.REPOSITORY_CODE_INDEX} (snapshot_id, file_path)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_code_index_repository_path ON {TABLES.REPOSITORY_CODE_INDEX} (repository_id, file_path)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_code_index_payload ON {TABLES.REPOSITORY_CODE_INDEX} USING GIN (index_payload)",

    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.REPOSITORY_CODE_SYMBOLS} (
        id BIGSERIAL PRIMARY KEY,
        snapshot_id TEXT NOT NULL REFERENCES {TABLES.REPOSITORY_SNAPSHOTS}(snapshot_id) ON DELETE CASCADE,
        repository_id TEXT NOT NULL REFERENCES {TABLES.REPOSITORIES}(repository_id) ON DELETE CASCADE,
        file_path TEXT NOT NULL,
        symbol_kind TEXT NOT NULL CHECK (symbol_kind IN ('function', 'class', 'method')),
        symbol_name TEXT NOT NULL,
        parent_symbol TEXT,
        line INTEGER NOT NULL,
        language TEXT NOT NULL DEFAULT '',
        git_sha TEXT NOT NULL DEFAULT '',
        symbol_payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        last_indexed TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (snapshot_id, file_path, symbol_kind, symbol_name, line)
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_repository_code_symbols_repo_name ON {TABLES.REPOSITORY_CODE_SYMBOLS} (repository_id, symbol_name)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_code_symbols_snapshot_path ON {TABLES.REPOSITORY_CODE_SYMBOLS} (snapshot_id, file_path)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_code_symbols_repo_time ON {TABLES.REPOSITORY_CODE_SYMBOLS} (repository_id, last_indexed DESC)",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.REPOSITORY_BASELINE_METRICS} (
        snapshot_id TEXT PRIMARY KEY REFERENCES {TABLES.REPOSITORY_SNAPSHOTS}(snapshot_id) ON DELETE CASCADE,
        repo_full_name TEXT NOT NULL DEFAULT '',
        metrics_payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        metrics_version INTEGER NOT NULL DEFAULT 1
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_repository_baseline_metrics_repo ON {TABLES.REPOSITORY_BASELINE_METRICS} (repo_full_name)",
    f"CREATE INDEX IF NOT EXISTS idx_repository_baseline_metrics_repository_time ON {TABLES.REPOSITORY_BASELINE_METRICS} (repository_id, computed_at DESC)",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLES.SCHEMA_VERSION} (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    )
    """,
]


def apply_canonical_schema(connection, search_path: Optional[str] = None) -> None:
    """Apply all DDL on an open psycopg2 connection."""
    path = search_path or SCHEMA_NAME
    cursor = connection.cursor()
    try:
        for sql in DDL_STATEMENTS:
            cursor.execute(sql)
        cursor.execute(f"SET search_path TO {path}, public")
        connection.commit()
    finally:
        cursor.close()


def ensure_search_path(connection, search_path: Optional[str] = None) -> None:
    path = search_path or SCHEMA_NAME
    cursor = connection.cursor()
    try:
        cursor.execute(f"SET search_path TO {path}, public")
        connection.commit()
    finally:
        cursor.close()
