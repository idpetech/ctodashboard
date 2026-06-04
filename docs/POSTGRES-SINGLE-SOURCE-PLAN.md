# Postgres Single Source of Truth — Plan

**Status:** Implemented (canonical schema + consolidated access layer)  
**Date:** 2026-05-31  

## Problem

Three competing persistence models ran in parallel: JSON under `config/workspaces/`, wrong adapter DDL (`secure_assignments` with `id` PK and no `metrics_config`), and correct migration DDL in `railway_schema_migration.py` that was not wired at runtime. SQL in `store_assignment` targeted columns the adapter never created.

## Decision

**Keep:** `ctodashboard` schema — `users`, `workspaces`, `assignments`, `credentials`, `audit_logs`, `schema_version`.

**Rationale:** Matches WorkspaceService assignment JSON, dashboard UI fields, `SecureUserService`, and existing `store_assignment` / `store_assignment_credentials` column sets.

**Reject:** Adapter legacy `secure_assignments` DDL, SQLite paths in services, hardcoded Postgres URLs, silent auto-admin without env flag.

## Implementation

1. `services/security/canonical_schema.py` — only DDL.
2. `PostgreSQLAdapter.create_tables()` — calls canonical apply only.
3. `SecureDatabaseManager` — PostgreSQL-only, canonical table names, `ENABLE_DB_AUTO_INIT` gated.
4. Import/export — `secure_db` methods only, no parallel `?` SQL.
5. This manifest + deprecation headers on one-off scripts.

## Backout

1. `git revert` the SSOT commit(s).
2. Unset `ENABLE_DB_AUTO_INIT` if enabled for testing.
3. Old `secure_*` tables remain on disk; reverted code may read them if `search_path` is not `ctodashboard`.
4. Assignment backup: JSON under `config/workspaces/` or export files.
5. Railway: redeploy previous release; verify `DATABASE_URL`.

## Validation checklist

- App starts with `DATABASE_URL` set.
- `health_check()` reports schema_version >= 1 and counts from `users` / `assignments`.
- Assignment store/load round-trip via `secure_db`.
- Import uses `store_assignment` (no raw SQLite SQL).

## Deferred

- Full WorkspaceService → Postgres cutover in API routes.
- Deleting files listed in `DEPRECATION-MANIFEST.md`.

## Phase 2 (2026-05-31): Workspace cutover

- `WorkspaceService` CRUD delegates to `postgres_backend` → `secure_db`
- `CredentialService` reads from `credentials` table only
- Connector form loads credentials via `GET .../auth/<connector_type>` (authenticated)
- `GET /api/assignments` lists from Postgres workspaces, not `config/workspaces/` dirs
