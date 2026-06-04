# CTO Dashboard — Current Architecture (source of truth)

**Last updated:** 2026-06-04  
**Git baseline:** `origin/master` @ `322a4da` and later  
**Read this first.** It overrides stale bullets in root `CLAUDE.md` (InsightVault rules) and outdated sections in `.cursorrules`.

---

## What this app is

- **One Flask app:** `integrated_dashboard.py` (port 8520 locally)
- **UI:** Server-rendered HTML — `templates/dashboard.html`, Tailwind via CDN
- **Not in use:** React frontend (archived under `_attic/frontend/`)
- **Deploy target:** Railway with `DATABASE_URL` → PostgreSQL

---

## Data plane (Postgres only)

| Layer | Role |
|--------|------|
| `services/security/canonical_schema.py` | DDL only — `ctodashboard` schema |
| `services/security/database_adapter.py` | URL parsing, connections; **rejects SQLite** |
| `services/security/postgres_store.py` | `SecureDatabaseManager` — all SQL |
| `services/security/secure_database.py` | Thin re-export (`secure_db` singleton) |

**Tables:** `users`, `workspaces`, `assignments`, `credentials`, `audit_logs`, `schema_version`

**Not runtime data:**

- `config/users/*.json`, `config/workspaces/*.json` — removed; gitignored
- `secure_credentials.db` — legacy artifact; do not use
- Deleted scripts: see `DEPRECATION-MANIFEST.md`

**Still on disk (schemas only):**

- `config/connectors/*.json` — connector field definitions for forms, not user/workspace records

---

## Auth and workspaces

- **Auth:** `SecureUserService` → Postgres `users` (JWT + session cookie)
- **Alias:** `services/auth/user_service.py` re-exports `SecureUserService` only
- **Workspaces:** `WorkspaceService` → `postgres_backend` → `secure_db`
- **Secrets:** Postgres `credentials` table (Fernet). Do **not** read secrets from `metrics_config.auth_instance.credentials` (empty after save; use `CredentialService`).

---

## Metrics

- **Collect:** `collect_assignment_metrics()` in `routes/api_routes.py` (parallel fetches)
- **Config merge:** `services/assignment_metrics_config.py`
- **Slow path:** AWS; expect 30–90s for full “all metrics” unless connectors disabled

---

## Local run

```bash
source .env.local
export ENABLE_WORKSPACES=true
./venv/bin/python integrated_dashboard.py
# http://127.0.0.1:8520 — stick to one host for cookies
```

---

## Principles (still apply)

1. **Always working** — do not break login, workspaces, assignment CRUD
2. **KISS** — no new storage paths, no SQLite revival
3. **Feature-flag** new behavior
4. **Postgres is the only product datastore**

---

## Do not do (agents)

- Reintroduce JSON user/workspace runtime files
- Wire SQLite for product data
- Treat root `CLAUDE.md` (InsightVault) as this repo’s architecture
- Use deleted migration scripts as runbooks

---

## Related docs

| Doc | Purpose |
|-----|---------|
| `POSTGRES-SINGLE-SOURCE-PLAN.md` | Migration rationale, validation, backout |
| `DEPRECATION-MANIFEST.md` | Removed / archive candidates |

---

## Tomorrow checklist

- `git pull origin master`
- Restart Flask after pull
- Confirm Railway `DATABASE_URL` + `ctodashboard` search_path
- Re-save connector credentials if forms are empty
