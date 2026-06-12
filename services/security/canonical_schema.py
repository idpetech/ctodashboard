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
