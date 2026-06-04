# Postgres Single Source of Truth

**Status:** Complete (runtime cutover)  
**Date:** 2026-06-04  

## Decision

**Single schema:** `ctodashboard` — `users`, `workspaces`, `assignments`, `credentials`, `audit_logs`, `schema_version`.

**Code path:** `canonical_schema.py` → `database_adapter.py` → `postgres_store.py` → `secure_database.py`.

**Auth:** `SecureUserService` only (Postgres). `user_service.py` is a thin import alias.

**Workspaces:** `WorkspaceService` → `postgres_backend` → `secure_db`. Connector schemas: `config/connectors/*.json`.

## Local run

```bash
source .env.local
export ENABLE_WORKSPACES=true
ENABLE_DB_AUTO_INIT=true python3 scripts/init_postgres_schema.py
./venv/bin/python integrated_dashboard.py
```

## Validation

- Register → token + profile 200
- `secure_db.health_check()` → `database_type: postgresql`
- No runtime data in `config/users/` or `config/workspaces/`
