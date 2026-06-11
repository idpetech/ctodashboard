"""
PostgreSQL data layer — single source of truth for persisted app data.

See docs/POSTGRES-SINGLE-SOURCE-PLAN.md. DDL lives in canonical_schema.py only.
"""

import base64
import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.logging_config import get_logger

from .canonical_schema import REQUIRED_TABLES, SCHEMA_NAME
from .database_adapter import create_database_adapter, parse_database_url

logger = get_logger(__name__)

CONNECTOR_TYPES = ("github", "jira", "aws", "openai", "railway")


def _row_val(row, key: str, index: int = 0):
    if hasattr(row, "keys"):
        return row[key]
    return row[index]


def _bytea_to_bytes(value):
    """PostgreSQL BYTEA may be returned as memoryview."""
    if value is None:
        return None
    if isinstance(value, memoryview):
        return bytes(value)
    return value


def _extract_count(result) -> int:
    if not result:
        return 0
    row = result[0]
    if hasattr(row, "keys"):
        return int(row.get("count") or list(row.values())[0])
    return int(row[0])


class SecureDatabaseManager:
    """PostgreSQL-only secure storage. All SQL uses canonical_schema table names."""

    def __init__(self, db_path: str = None):
        self.db_url = self._determine_database_url(db_path)
        self.db_type, self.connection_config = parse_database_url(self.db_url)
        if self.db_type != "postgresql":
            raise RuntimeError("Only PostgreSQL is supported")

        self._fernet = self._get_encryption_key()
        self.adapter = create_database_adapter(self.db_type, self.connection_config, self._fernet)

        if not self.adapter.connect():
            raise RuntimeError("Failed to connect to PostgreSQL")

        self._ensure_database_ready()
        logger.info(
            "SecureDatabaseManager initialized",
            extra={"operation": "db_init", "db_type": self.db_type},
        )

    @staticmethod
    def _determine_database_url(db_path: str = None) -> str:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL must be set to a PostgreSQL connection string "
                "(include search_path=ctodashboard)."
            )
        return SecureDatabaseManager._ensure_ctodashboard_search_path(url)

    @staticmethod
    def _ensure_ctodashboard_search_path(url: str) -> str:
        if "search_path" in url or "ctodashboard" in url:
            return url
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}options=-csearch_path%3Dctodashboard"

    def _get_encryption_key(self) -> Fernet:
        import platform

        master_key = os.getenv("CREDENTIAL_MASTER_KEY")
        if not master_key:
            machine_info = f"{platform.node()}{platform.machine()}{platform.processor()}"
            master_key = hashlib.sha256(machine_info.encode()).hexdigest()
            logger.warning(
                "Using development credential key. Set CREDENTIAL_MASTER_KEY for production."
            )
        salt = b"ctodashboard_salt_v1"
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)

    def _ensure_database_ready(self) -> None:
        if not self._database_exists_and_ready():
            self.adapter.create_tables()
            self.adapter.set_schema_version(1, "Canonical ctodashboard schema")
            logger.info("Database initialized from canonical_schema")
        elif self.adapter.get_schema_version() < 1:
            self.adapter.create_tables()
            self.adapter.set_schema_version(1, "Canonical ctodashboard schema")

        # Additive, idempotent migration for Portfolio Dashboard MVP.
        # No-op if the column already exists; runs once at boot (not a job/scheduler).
        try:
            self.adapter.execute_update(
                "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS target_monthly_burn INTEGER"
            )
        except Exception as e:
            logger.warning("target_monthly_burn migration skipped: %s", e)
        # Product analytics tables (idempotent; gated at runtime by ENABLE_PRODUCT_ANALYTICS).
        try:
            from services.security.canonical_schema import TABLES

            analytics_ddls = [
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
            ]
            for ddl in analytics_ddls:
                self.adapter.execute_update(ddl)
        except Exception as e:
            logger.warning("analytics tables migration skipped: %s", e)

        if os.getenv("ENABLE_DB_AUTO_INIT", "false").lower() == "true":
            self._auto_initialize_if_empty()

    def _database_exists_and_ready(self) -> bool:
        return all(self.adapter.check_table_exists(t) for t in REQUIRED_TABLES)

    def _auto_initialize_if_empty(self) -> None:
        try:
            result = self.adapter.execute_query("SELECT COUNT(*) AS count FROM users")
            if _extract_count(result) > 0:
                return
            admin_data = {
                "display_name": "admin",
                "workspaces": ["admin_workspace"],
                "role": "admin",
                "status": "active",
                "preferences": {"theme": "light", "timezone": "UTC"},
                "password_hash": "$2b$12$K8gU2XtWx4YM9V7pGn1qJ.F4rKGQ8n3Z2mR5sT9xV6wP4bC1dA7hO",
                "salt": "fixed_salt_for_demo",
            }
            audit = {"user_email": "system", "ip_address": "127.0.0.1", "user_agent": "auto_init"}
            self.store_user_credentials("admin@ctodashboard.app", admin_data, audit)
            logger.info("Default admin user created (ENABLE_DB_AUTO_INIT=true)")
        except Exception as e:
            logger.error("Auto-initialization failed: %s", e)

    def store_user_credentials(
        self, email: str, user_data: Dict[str, Any], audit_info: Dict[str, Any] = None
    ) -> bool:
        try:
            sensitive = {
                "password_hash": user_data.get("password_hash"),
                "salt": user_data.get("salt"),
            }
            encrypted = self.adapter.encrypt_data(sensitive) if any(sensitive.values()) else None
            query = """
                INSERT INTO users
                (email, display_name, encrypted_password_data, workspaces, role, status,
                 preferences, last_login, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (email) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    encrypted_password_data = EXCLUDED.encrypted_password_data,
                    workspaces = EXCLUDED.workspaces,
                    role = EXCLUDED.role,
                    status = EXCLUDED.status,
                    preferences = EXCLUDED.preferences,
                    last_login = EXCLUDED.last_login,
                    updated_at = NOW()
            """
            params = (
                email,
                user_data.get("display_name"),
                encrypted,
                json.dumps(user_data.get("workspaces", [])),
                user_data.get("role", "user"),
                user_data.get("status", "active"),
                json.dumps(user_data.get("preferences", {})),
                user_data.get("last_login"),
            )
            self.adapter.execute_update(query, params)
            self._audit_log("store_user", "user", email, audit_info, True)
            return True
        except Exception as e:
            self._audit_log("store_user", "user", email, audit_info, False, str(e))
            logger.error("store_user_credentials failed: %s", e)
            return False

    def get_user_credentials(
        self, email: str, audit_info: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            rows = self.adapter.execute_query("SELECT * FROM users WHERE email = %s", (email,))
            if not rows:
                self._audit_log("get_user", "user", email, audit_info, False, "User not found")
                return None
            row = rows[0]
            enc = _bytea_to_bytes(row["encrypted_password_data"])
            sensitive = self.adapter.decrypt_data(enc) if enc else {}
            user_data = {
                "email": row["email"],
                "display_name": row["display_name"],
                "workspaces": json.loads(row["workspaces"] or "[]"),
                "role": row["role"],
                "status": row["status"],
                "preferences": json.loads(row["preferences"] or "{}"),
                "created_at": row["created_at"],
                "last_login": row["last_login"],
                **sensitive,
            }
            self._audit_log("get_user", "user", email, audit_info, True)
            return user_data
        except Exception as e:
            self._audit_log("get_user", "user", email, audit_info, False, str(e))
            return None

    def store_workspace(
        self,
        workspace_id: str,
        name: str,
        description: str = "",
        settings: Optional[Dict[str, Any]] = None,
    ) -> bool:
        try:
            query = """
                INSERT INTO workspaces (workspace_id, name, description, settings, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (workspace_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    settings = EXCLUDED.settings,
                    updated_at = NOW()
            """
            self.adapter.execute_update(
                query,
                (workspace_id, name, description, json.dumps(settings or {})),
            )
            return True
        except Exception as e:
            logger.error("store_workspace failed: %s", e)
            return False

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        try:
            rows = self.adapter.execute_query(
                "SELECT workspace_id, name, description, settings, created_at, updated_at "
                "FROM workspaces WHERE workspace_id = %s",
                (workspace_id,),
            )
            if not rows:
                return None
            row = rows[0]
            return {
                "workspace_id": row["workspace_id"],
                "name": row["name"],
                "description": row["description"],
                "settings": json.loads(row["settings"] or "{}"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        except Exception as e:
            logger.error("get_workspace failed: %s", e)
            return None

    def store_assignment(self, assignment_data: Dict[str, Any]) -> bool:
        try:
            metrics = assignment_data.get("metrics_config", {})
            metrics_json = json.dumps(metrics) if metrics else None
            aid = assignment_data.get("assignment_id") or assignment_data.get("id")
            query = """
                INSERT INTO assignments
                (assignment_id, workspace_id, name, description, team_size, monthly_burn_rate,
                 target_monthly_burn, status, metrics_config, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (assignment_id, workspace_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    team_size = EXCLUDED.team_size,
                    monthly_burn_rate = EXCLUDED.monthly_burn_rate,
                    target_monthly_burn = EXCLUDED.target_monthly_burn,
                    status = EXCLUDED.status,
                    metrics_config = EXCLUDED.metrics_config,
                    updated_at = NOW()
            """
            params = (
                aid,
                assignment_data.get("workspace_id"),
                assignment_data.get("name"),
                assignment_data.get("description"),
                assignment_data.get("team_size"),
                assignment_data.get("monthly_burn_rate"),
                assignment_data.get("target_monthly_burn"),
                assignment_data.get("status", "active"),
                metrics_json,
            )
            self.adapter.execute_update(query, params)
            return True
        except Exception as e:
            logger.error("store_assignment failed: %s", e)
            return False

    def get_assignment(self, workspace_id: str, assignment_id: str) -> Optional[Dict[str, Any]]:
        try:
            rows = self.adapter.execute_query(
                """SELECT assignment_id, workspace_id, name, description, team_size,
                          monthly_burn_rate, target_monthly_burn, status, metrics_config,
                          created_at, updated_at
                   FROM assignments WHERE workspace_id = %s AND assignment_id = %s""",
                (workspace_id, assignment_id),
            )
            if not rows:
                return None
            row = rows[0]
            metrics = row["metrics_config"]
            if isinstance(metrics, str) and metrics:
                metrics = json.loads(metrics)
            return {
                "assignment_id": row["assignment_id"],
                "id": row["assignment_id"],
                "workspace_id": row["workspace_id"],
                "name": row["name"],
                "description": row["description"],
                "team_size": row["team_size"],
                "monthly_burn_rate": row["monthly_burn_rate"],
                "target_monthly_burn": row["target_monthly_burn"],
                "status": row["status"],
                "metrics_config": metrics or {},
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        except Exception as e:
            logger.error("get_assignment failed: %s", e)
            return None

    def delete_assignment(self, workspace_id: str, assignment_id: str) -> bool:
        """Permanently remove an assignment and its credentials from this workspace."""
        try:
            self.adapter.execute_update(
                "DELETE FROM credentials WHERE workspace_id = %s AND assignment_id = %s",
                (workspace_id, assignment_id),
            )
            self.adapter.execute_update(
                "DELETE FROM assignments WHERE workspace_id = %s AND assignment_id = %s",
                (workspace_id, assignment_id),
            )
            self._audit_log(
                "delete",
                "assignment",
                assignment_id,
                success=True,
                workspace_id=workspace_id,
            )
            return True
        except Exception as e:
            logger.error("delete_assignment failed: %s", e)
            self._audit_log(
                "delete",
                "assignment",
                assignment_id,
                success=False,
                error=str(e),
                workspace_id=workspace_id,
            )
            return False

    def get_workspace_assignments(self, workspace_id: str) -> List[Dict[str, Any]]:
        try:
            rows = self.adapter.execute_query(
                "SELECT * FROM assignments WHERE workspace_id = %s", (workspace_id,)
            )
            assignments = []
            for row in rows:
                metrics = row.get("metrics_config")
                if isinstance(metrics, str) and metrics:
                    metrics = json.loads(metrics)
                aid = row["assignment_id"]
                assignment = {
                    "id": aid,
                    "assignment_id": aid,
                    "workspace_id": row["workspace_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "team_size": row["team_size"],
                    "monthly_burn_rate": row["monthly_burn_rate"],
                    "target_monthly_burn": row.get("target_monthly_burn"),
                    "status": row["status"],
                    "metrics_config": metrics or {},
                    "created_at": row["created_at"],
                }
                assignment["credentials"] = self.list_assignment_credentials(workspace_id, aid)
                assignments.append(assignment)
            return assignments
        except Exception as e:
            logger.error("get_workspace_assignments failed: %s", e)
            return []

    def store_assignment_credentials(
        self,
        workspace_id: str,
        assignment_id: str,
        connector_type: str,
        credentials: Dict[str, Any],
        audit_info: Dict[str, Any] = None,
    ) -> bool:
        try:
            encrypted = self.adapter.encrypt_data(credentials)
            query = """
                INSERT INTO credentials
                (workspace_id, assignment_id, connector_type, encrypted_credentials, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (workspace_id, assignment_id, connector_type) DO UPDATE SET
                    encrypted_credentials = EXCLUDED.encrypted_credentials,
                    updated_at = NOW()
            """
            self.adapter.execute_update(
                query, (workspace_id, assignment_id, connector_type, encrypted)
            )
            self._audit_log(
                "store_credentials",
                "credential",
                f"{workspace_id}/{assignment_id}/{connector_type}",
                audit_info,
                True,
                connector_type=connector_type,
                workspace_id=workspace_id,
            )
            return True
        except Exception as e:
            self._audit_log(
                "store_credentials",
                "credential",
                f"{workspace_id}/{assignment_id}/{connector_type}",
                audit_info,
                False,
                str(e),
            )
            return False

    def get_assignment_credentials(
        self,
        workspace_id: str,
        assignment_id: str,
        connector_type: str,
        audit_info: Dict[str, Any] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            rows = self.adapter.execute_query(
                """SELECT encrypted_credentials FROM credentials
                   WHERE workspace_id = %s AND assignment_id = %s AND connector_type = %s""",
                (workspace_id, assignment_id, connector_type),
            )
            if not rows:
                return None
            return self.adapter.decrypt_data(_bytea_to_bytes(rows[0]["encrypted_credentials"]))
        except Exception as e:
            logger.error("get_assignment_credentials failed: %s", e)
            return None

    def delete_assignment_credentials(
        self,
        workspace_id: str,
        assignment_id: str,
        connector_type: str,
        audit_info: Dict[str, Any] = None,
    ) -> bool:
        try:
            n = self.adapter.execute_update(
                """DELETE FROM credentials
                   WHERE workspace_id = %s AND assignment_id = %s AND connector_type = %s""",
                (workspace_id, assignment_id, connector_type),
            )
            return n > 0
        except Exception as e:
            logger.error("delete_assignment_credentials failed: %s", e)
            return False

    def list_assignment_credentials(self, workspace_id: str, assignment_id: str) -> Dict[str, bool]:
        try:
            rows = self.adapter.execute_query(
                """SELECT connector_type FROM credentials
                   WHERE workspace_id = %s AND assignment_id = %s""",
                (workspace_id, assignment_id),
            )
            configured = {r["connector_type"] for r in rows} if rows else set()
            return {c: c in configured for c in CONNECTOR_TYPES}
        except Exception as e:
            logger.error("list_assignment_credentials failed: %s", e)
            return {c: False for c in CONNECTOR_TYPES}

    def record_audit_event(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        workspace_id: str = None,
        success: bool = True,
        audit_info: Dict[str, Any] = None,
    ) -> None:
        info = dict(audit_info or {})
        if workspace_id:
            info["workspace_id"] = workspace_id
        self._audit_log(action, entity_type, entity_id, info, success)

    def _audit_log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        audit_info: Dict[str, Any] = None,
        success: bool = True,
        error: str = None,
        connector_type: str = None,
        workspace_id: str = None,
    ) -> None:
        try:
            audit_info = audit_info or {}
            query = """
                INSERT INTO audit_logs
                (action, entity_type, entity_id, user_email, workspace_id, connector_type,
                 success, error_message, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.adapter.execute_update(
                query,
                (
                    action,
                    entity_type,
                    entity_id,
                    audit_info.get("user_email", "system"),
                    workspace_id or audit_info.get("workspace_id"),
                    connector_type or audit_info.get("connector_type"),
                    success,
                    error,
                    audit_info.get("ip_address"),
                    audit_info.get("user_agent"),
                ),
            )
        except Exception as e:
            logger.error("audit_log failed: %s", e)

    def get_audit_logs(self, limit: int = 100, entity_type: str = None) -> List[Dict[str, Any]]:
        try:
            if entity_type:
                rows = self.adapter.execute_query(
                    """SELECT * FROM audit_logs WHERE entity_type = %s
                       ORDER BY created_at DESC LIMIT %s""",
                    (entity_type, limit),
                )
            else:
                rows = self.adapter.execute_query(
                    "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("get_audit_logs failed: %s", e)
            return []

    def list_all_users(self) -> List[Dict[str, Any]]:
        """List users (email/display_name only). Used by admin inspect scripts."""
        try:
            rows = self.adapter.execute_query(
                "SELECT email, display_name, role, status, created_at FROM users ORDER BY email"
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("list_all_users failed: %s", e)
            return []

    def health_check(self) -> Dict[str, Any]:
        try:
            users = _extract_count(
                self.adapter.execute_query("SELECT COUNT(*) AS count FROM users")
            )
            creds = _extract_count(
                self.adapter.execute_query("SELECT COUNT(*) AS count FROM credentials")
            )
            assignments = _extract_count(
                self.adapter.execute_query("SELECT COUNT(*) AS count FROM assignments")
            )
            audit_recent = _extract_count(
                self.adapter.execute_query(
                    "SELECT COUNT(*) AS count FROM audit_logs "
                    "WHERE created_at > NOW() - INTERVAL '24 hours'"
                )
            )
            return {
                "database_connected": True,
                "database_type": self.db_type,
                "schema": SCHEMA_NAME,
                "schema_version": self.adapter.get_schema_version(),
                "statistics": {
                    "users": users,
                    "credentials": creds,
                    "assignments": assignments,
                    "recent_audit_events": audit_recent,
                },
                "security": {
                    "encryption_enabled": True,
                    "audit_logging": True,
                    "master_key_configured": bool(os.getenv("CREDENTIAL_MASTER_KEY")),
                },
            }
        except Exception as e:
            return {"database_connected": False, "error": str(e)}

    @property
    def db_path(self) -> Path:
        return Path("postgresql://ctodashboard")

    def _get_connection(self):
        return self.adapter._connection

    def _encrypt_data(self, data):
        return self.adapter.encrypt_data(data)

    def _decrypt_data(self, encrypted_data):
        return self.adapter.decrypt_data(encrypted_data)

    def list_workspaces(self) -> List[Dict[str, Any]]:
        try:
            rows = self.adapter.execute_query(
                "SELECT workspace_id, name, description, settings, created_at, updated_at "
                "FROM workspaces ORDER BY workspace_id"
            )
            result = []
            for row in rows:
                assignment_count = _extract_count(
                    self.adapter.execute_query(
                        "SELECT COUNT(*) AS count FROM assignments WHERE workspace_id = %s",
                        (row["workspace_id"],),
                    )
                )
                result.append(
                    {
                        "id": row["workspace_id"],
                        "name": row["name"],
                        "description": row.get("description") or "",
                        "assignment_count": assignment_count,
                        "status": "active",
                        "created_at": row.get("created_at"),
                    }
                )
            return result
        except Exception as e:
            logger.error("list_workspaces failed: %s", e)
            return []

    def delete_workspace(self, workspace_id: str) -> bool:
        try:
            self.adapter.execute_update(
                "DELETE FROM credentials WHERE workspace_id = %s", (workspace_id,)
            )
            self.adapter.execute_update(
                "DELETE FROM assignments WHERE workspace_id = %s", (workspace_id,)
            )
            n = self.adapter.execute_update(
                "DELETE FROM workspaces WHERE workspace_id = %s", (workspace_id,)
            )
            return n > 0
        except Exception as e:
            logger.error("delete_workspace failed: %s", e)
            return False

    def find_assignment(
        self, assignment_id: str, workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return list of {workspace_id, assignment} matches."""
        try:
            if workspace_id:
                a = self.get_assignment(workspace_id, assignment_id)
                return [{"workspace_id": workspace_id, "assignment": a}] if a else []
            rows = self.adapter.execute_query(
                "SELECT workspace_id FROM assignments WHERE assignment_id = %s",
                (assignment_id,),
            )
            matches = []
            for row in rows:
                ws = row["workspace_id"]
                a = self.get_assignment(ws, assignment_id)
                if a:
                    matches.append({"workspace_id": ws, "assignment": a})
            return matches
        except Exception as e:
            logger.error("find_assignment failed: %s", e)
            return []

    def get_workspace_api_dict(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Workspace shape expected by dashboard API."""
        row = self.get_workspace(workspace_id)
        if not row:
            return None
        settings = row.get("settings") or {}
        assignments = self.get_workspace_assignments(workspace_id)
        return {
            "id": workspace_id,
            "name": row["name"],
            "description": row.get("description") or "",
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "assignments": [a["id"] for a in assignments],
            "connector_templates": settings.get("connector_templates", {}),
            "settings": settings,
            "status": settings.get("status", "active"),
        }


_secure_db_instance = None
_secure_db_lock = threading.Lock()


def get_secure_db() -> SecureDatabaseManager:
    global _secure_db_instance
    if _secure_db_instance is None:
        with _secure_db_lock:
            if _secure_db_instance is None:
                _secure_db_instance = SecureDatabaseManager()
    return _secure_db_instance


class _SecureDbProxy:
    def __getattr__(self, name):
        return getattr(get_secure_db(), name)


secure_db = _SecureDbProxy()
