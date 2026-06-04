# Deprecation Manifest

**Status:** Cutover complete (2026-06). Runtime data is Postgres `ctodashboard` schema only.

## Removed (deleted from repo)

- SQLite / volume migration scripts (`railway_schema_migration.py`, `migrate_to_secure_storage.py`, etc.)
- `secure_database.legacy.py`, `secure_database_backup.py`
- JSON user files under `config/users/` (misleading duplicate of Postgres)
- JSON workspace files under `config/workspaces/` (runtime data in Postgres)
- `services/workspace/secure_workspace_service.py` (unused duplicate)
- `validate_system.py`, `reset_admin_password.py` (JSON/SQLite assumptions)

## Still valid (not user/workspace data)

- `config/connectors/*.json` — connector field schemas for the UI
- `config/.jwt_secret` — dev JWT secret (gitignored)
- `scripts/init_postgres_schema.py` — applies schema via `ENABLE_DB_AUTO_INIT`

## Schema init

```bash
export DATABASE_URL='postgresql://...?options=-csearch_path%3Dctodashboard'
ENABLE_DB_AUTO_INIT=true python3 scripts/init_postgres_schema.py
```

## Legacy Postgres tables (do not write)

`secure_users`, `secure_workspaces`, `secure_assignments`, `secure_credentials`, `credential_audit`

## Canonical tables

`ctodashboard.users`, `workspaces`, `assignments`, `credentials`, `audit_logs`, `schema_version`
