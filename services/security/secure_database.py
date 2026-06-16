"""
Secure database entry point — backward-compatible re-export.

Prefer domain facades:
  db_workspaces, db_credentials, db_assignments, db_users, db_system
"""

from services.security.db_registry import SecureDatabaseManager, get_secure_db, secure_db

__all__ = ["SecureDatabaseManager", "get_secure_db", "secure_db"]
