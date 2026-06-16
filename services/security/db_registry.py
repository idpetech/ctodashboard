"""Singleton database manager registry (Postgres implementation)."""

from __future__ import annotations

from services.security.postgres_store import SecureDatabaseManager, get_secure_db, secure_db

__all__ = ["SecureDatabaseManager", "get_secure_db", "secure_db"]
