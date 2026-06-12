# CTO Dashboard — Current Architecture (source of truth)

**Last updated:** 2026-06-11  
**Git baseline:** `origin/master` @ `322a4da` and later  
**Read this first.** It overrides stale bullets in root `CLAUDE.md` (InsightVault rules) and outdated sections in `.cursorrules`.

---

## CTO Briefing (Daily Brief)

Feature-flagged via `ENABLE_ATTENTION_ENGINE` (+ `ENABLE_PORTFOLIO_DASHBOARD` for live panels).

**Full flow map:** [`docs/CTO-BRIEFING-FLOW.md`](CTO-BRIEFING-FLOW.md) — read before changing briefing, attention, or Overview panels.

| Layer | Module |
|--------|--------|
| Scoring | `services/portfolio_service.py` |
| Briefing build | `services/attention_engine.py` |
| Executive copy | `services/executive_language.py` |
| Storage | `workspace.settings.attention_briefing` (Postgres JSONB) |
| API | `routes/api_routes.py` `/attention/*`, `/api/portfolio/summary` |
| UI | `templates/dashboard.html` Overview panels |


---

## What this app is

- **One Flask app:** `integrated_dashboard.py` (port 8520 locally)
- **UI:** Server-rendered HTML — `templates/dashboard.html` (~1.4k lines shell + modals), Tailwind via CDN
- **Dashboard client JS:** `static/js/dashboard/00-state.js` … `11-export-import.js` (load order in template); re-extract via `scripts/extract_dashboard_js.py` from rollback tag if needed
- **Dashboard templates:** `templates/dashboard.html` shell + `templates/dashboard/_*.html` partials; re-split via `scripts/split_dashboard_partials.py`
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

## Portfolio Dashboard (MVP, feature-flagged)

**Flag:** `ENABLE_PORTFOLIOS` (default `false`). Portfolio entity layer (Act 1): `workspace.settings.portfolios[]`,
`assignments.portfolio_id` (Postgres column, default `default`), scoped briefing keys in settings.
API: `/api/workspaces/<id>/portfolios` (+ scoped attention/CTOLens refresh). No dashboard UI until Act 2.
See `services/portfolio_scope_service.py`, `routes/api/portfolios.py`.

**Flag:** `ENABLE_PORTFOLIO_DASHBOARD` (default `false`). Wired in `integrated_dashboard.py`,
`services/service_manager.py`, and surfaced via `/api/feature-flags`.

- **Schema:** one additive column `assignments.target_monthly_burn INTEGER` (nullable).
  Applied to fresh DBs via `canonical_schema.py` and to existing DBs via an idempotent
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` in `postgres_store._ensure_database_ready()`.
  No new tables.
- **Compute:** `services/portfolio_service.py` — pure, on-demand. Derives six read-only
  views (summary, health score, connector health, attention center, assignment ranking,
  budget variance) from current assignment rows. No snapshots, jobs, schedulers, history,
  trends, or AI.
- **API:** `GET /api/portfolio/summary` (403 when flag off) in `routes/api_routes.py`.
- **UI:** `templates/dashboard.html` Overview tab renders a `#portfolio-dashboard-section`
  only when the flag is on; existing Overview is unchanged. Assignment create/edit forms
  gained a "Target Monthly Burn" input.
- **Note:** Connector health is config-derived (enabled vs credentials present), not a live
  probe, to keep the Overview fast and avoid background polling.

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

---

## CSV/Excel Import + Attention Engine (feature-flagged)

**Flags:** `ENABLE_CSV_IMPORT`, `ENABLE_ATTENTION_ENGINE` (both default `false`).

### CSV/Excel Import Pipeline
- **Parser:** `services/import_parser.py` — pure CSV/XLSX parsing with flexible
  column aliases; per-row errors; no DB I/O.
- **Orchestration:** `services/data_import_service.import_from_spreadsheet()` —
  parses → maps to assignment dicts → reuses existing `import_workspace_data()`.
- **API:** `POST /api/workspaces/<id>/import/file` (multipart `file` field).
  JSON import unchanged at `POST /api/workspaces/<id>/import`.
- **Idempotency:** SHA-256 file hash stored in `workspace.settings.import_history`;
  duplicate uploads skipped in `create_new` mode unless `force=true`.
- **Storage:** Assignments in Postgres; import metadata + parsed row cache in
  `workspace.settings.last_import` (no new tables).
- **Dependency:** `openpyxl` for `.xlsx`.

### Attention Engine
- **Service:** `services/attention_engine.py` — deterministic, rule-based CTO
  briefing. Reuses `portfolio_service` computations. No external APIs.
- **Outputs (JSON):** executive briefing, risk signals, opportunity signals,
  system health score (0–100), CTO narrative (5–10 sentences).
- **Storage:** `workspace.settings.attention_briefing` (no new tables).
- **API:**
  - `GET /api/workspaces/<id>/attention/briefing` — retrieve stored briefing
  - `POST /api/workspaces/<id>/attention/refresh` — regenerate from current data
- **Triggers:** Runs automatically after CSV/Excel import (when flag on); manual
  refresh via Overview UI button or refresh endpoint.
- **UI:** `#attention-briefing-section` in Overview tab; import dialog accepts
  `.json`, `.csv`, `.xlsx` with drag-and-drop.
---

## API routes (modular)

**Entry:** `routes/api_routes.py` re-exports `register_routes` for backward compatibility.

**Implementation:** `routes/api/` — domain modules registered from `routes/api/__init__.py`:

| Module | Responsibility |
|--------|----------------|
| `deps.py` | Shared services, auth decorators, metrics collection |
| `pages.py` | Dashboard pages, health, public share links |
| `system.py` | Feature flags, legacy service stubs |
| `assignments.py` | Assignments CRUD, portfolio summary, connector metrics |
| `chatbot.py` | Chatbot streaming endpoints |
| `auth_billing.py` | Auth, trial, Stripe billing |
| `workspaces.py` | Workspaces, connectors, credentials, import/export |
| `credentials.py` | Connector credential validation helpers |
| `briefing.py` | Attention engine + CTOLens briefing API |
| `audit.py` | Assignment export, history, audit log |
| `import_export.py` | Import validation, templates, static files |
| `analytics.py` | Product analytics API |

**Pattern:** Each module exposes `register_*_routes(app)`; no route logic in `integrated_dashboard.py`.

## Product analytics (MVP, feature-flagged)

**Flag:** `ENABLE_PRODUCT_ANALYTICS` (default `false`).

- **Module:** `services/analytics/` — `track_event`, sessions, activation (`report_generated`)
- **Tables:** `analytics_events`, `analytics_sessions`, `analytics_user_profiles`
- **API:** `POST /api/analytics/events`, `GET /api/analytics/users/me/activity`, `GET /api/analytics/summary` (admin), `POST /api/analytics/page-view` (anonymous)
- **Client:** dashboard beacons (`page_view`, `insight_viewed`, `feature_used`); homepage anonymous page-view script
- **Queries:** `services/analytics/queries.py` — platform summary + retention cohorts
- **Plan:** [backlog/PRODUCT-ANALYTICS-PLAN.md](./backlog/PRODUCT-ANALYTICS-PLAN.md)

