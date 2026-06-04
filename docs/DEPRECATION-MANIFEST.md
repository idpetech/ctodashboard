# Deprecation Manifest

Remove or archive **after** Postgres SSOT validation (`POSTGRES-SINGLE-SOURCE-PLAN.md`).

## Delete / archive (scripts)

- railway_schema_migration.py
- migrate_to_secure_storage.py
- railway_migrate_db.py
- railway_setup_volume.py
- railway_debug_persistence.py
- railway_hotfix.py
- debug_db_path.py
- SQLiteAdapter in database_adapter.py

## Rewrite later (still live)

- services/workspace/workspace_service.py (JSON)
- services/auth/user_service.py (JSON parent)
- services/auth/credential_service.py (JSON metrics_config)
- config/workspaces/**

## Legacy Postgres tables (do not write)

secure_users, secure_workspaces, secure_assignments (wrong shape), secure_credentials, credential_audit

## Active canonical tables

ctodashboard.users, workspaces, assignments, credentials, audit_logs, schema_version
