"""
Secure database entry point — re-exports PostgreSQL implementation.

Canonical DDL: canonical_schema.py
Implementation: postgres_store.py

Legacy dual-schema code: secure_database.legacy.py (DELETE after validation — see docs/DEPRECATION-MANIFEST.md)
"""

from .postgres_store import SecureDatabaseManager, get_secure_db, secure_db

__all__ = ["SecureDatabaseManager", "get_secure_db", "secure_db"]
