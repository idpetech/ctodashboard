# CTO Lens Product Analytics Layer — Implementation Plan (MVP)

**Priority:** High (ASAP)  
**Status:** Phase 1–2 implemented (2026-06-10); Phase 3 pending  
**Jira import:** [CTOLENS-PRODUCT-ANALYTICS-JIRA.csv](./CTOLENS-PRODUCT-ANALYTICS-JIRA.csv)  
**Feature flag:** `ENABLE_PRODUCT_ANALYTICS` (default `false`)

---

## Goal

Answer with internal data (no Mixpanel/PostHog in MVP):

- How many users **activated**?
- How long do they stay per **session**?
- Do users **return** after first use?
- What **features** are actually used?

---

## Architecture (CTO Lens aligned)

| Constraint | Decision |
|------------|----------|
| Single Flask app | All routes in `routes/api_routes.py` (or thin `routes/analytics_routes.py` registered from `integrated_dashboard.py`) |
| Postgres only | New tables in `services/security/canonical_schema.py` + idempotent `ALTER`/create in `postgres_store._ensure_database_ready()` |
| No new runtime | Same gunicorn process; analytics writes are fast INSERTs, no background workers in MVP |
| Feature-flagged | `ENABLE_PRODUCT_ANALYTICS=false` → no writes, summary returns 403 or empty |
| User identity | Use existing auth user **email** as `user_id` (string) to match JWT/session; optional link to `users.id` in metadata |

**Module layout** (prompt adapted to repo conventions):

```
services/analytics/
  __init__.py
  models.py           # constants, event names, typed dicts
  event_tracker.py    # track_event()
  session_manager.py  # start/end/get session, inactivity timeout
  store.py            # Postgres CRUD via secure_db / adapter
  queries.py          # summary + retention SQL helpers
```

Do **not** add FastAPI — this is a Flask monolith.

---

## Data model (Postgres)

### `analytics_events`

| Column | Type | Notes |
|--------|------|--------|
| id | UUID PK | `gen_random_uuid()` |
| user_id | TEXT NOT NULL | email from auth |
| session_id | UUID NOT NULL | FK logical to sessions |
| event_name | TEXT NOT NULL | e.g. `user_login`, `report_generated` |
| occurred_at | TIMESTAMPTZ NOT NULL | default now() |
| metadata | JSONB | workspace_id, connector, panel, etc. |

Indexes: `(user_id, occurred_at)`, `(session_id)`, `(event_name, occurred_at)`.

### `analytics_sessions`

| Column | Type | Notes |
|--------|------|--------|
| session_id | UUID PK | |
| user_id | TEXT NOT NULL | |
| started_at | TIMESTAMPTZ NOT NULL | |
| ended_at | TIMESTAMPTZ | null until closed |
| duration_seconds | INTEGER | set on end |
| event_count | INTEGER DEFAULT 0 | incremented on each event |
| last_event_at | TIMESTAMPTZ | for 30min inactivity close |

Index: `(user_id, started_at)`.

### `analytics_user_profiles`

Minimal analytics profile (do **not** overload `users` table in MVP):

| Column | Type | Notes |
|--------|------|--------|
| user_id | TEXT PK | email |
| first_seen | TIMESTAMPTZ | first event |
| last_seen | TIMESTAMPTZ | updated every event |
| has_activated | BOOLEAN DEFAULT false | |
| first_activation_time | TIMESTAMPTZ | set once on `report_generated` |

Existing `users.created_at` / `last_login` remain source of truth for auth; analytics profile is product-behavior only.

---

## Core API (Python)

```python
track_event(user_id, event_name, session_id=None, metadata=None)
start_session(user_id) -> session_id
end_session(session_id)
get_current_session(user_id) -> session | None
get_user_activity_summary(user_id) -> dict
```

**Session rules**

- On `track_event` without `session_id`: reuse open session for user if `last_event_at` within **30 minutes**, else start new.
- On `end_session` or timeout: set `ended_at`, `duration_seconds`, increment nothing else.
- `event_count` += 1 per event.

**Activation**

- `ACTIVATION_EVENT = "report_generated"`
- On first `report_generated` for user: set `has_activated=true`, `first_activation_time=now`.
- Emit from: CTOLens briefing generate, attention refresh, share link create, PDF export (one event name, metadata distinguishes type).

---

## HTTP API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/analytics/events` | optional auth | Client beacon: `{ event_name, session_id?, metadata? }` |
| GET | `/api/analytics/users/me/activity` | user | `get_user_activity_summary` |
| GET | `/api/analytics/summary` | admin | 7d aggregates |

Flag off → POST returns 204 no-op (or 403); no DB write.

---

## Auto-instrumentation map

| Event | Where to hook |
|-------|----------------|
| `user_signup` | `POST /api/auth/register` success |
| `user_login` | `POST /api/auth/login` success |
| `dashboard_view` | `GET /dashboard` after auth, or JS once on dashboard load |
| `page_view` | homepage + dashboard JS `trackAnalytics('page_view', { path })` |
| `feature_used` | fallback from JS with `{ feature: '...' }` |
| `report_generated` | CTOLens/attention briefing generate, share, PDF export |
| `insight_viewed` | Overview briefing panel expand / CTOLens tab first view |
| `integration_connected` | credential PUT success or connector test success |

---

## Phased implementation

### Phase 1 — Foundation (ship first)

1. Schema + migration + feature flag  
2. `event_tracker` + `session_manager` + store  
3. Server hooks: signup, login, dashboard  
4. Activation on `report_generated` (backend only first)

**Exit:** Events rows appear in Postgres on staging with flag on.

### Phase 2 — Client + summaries

5. JS `trackAnalytics()` + session cookie/localStorage  
6. `GET /api/analytics/summary` (admin)  
7. `GET /api/analytics/users/me/activity`  
8. Remaining instrumentation (connectors, insight_viewed)  
9. Tests + docs

**Exit:** Success criteria questions answerable from SQL + admin endpoint.

### Phase 3 — Retention helpers (optional same sprint if time)

10. `queries.py` cohort helpers (D1/D7/D30 return counts)  
11. Document sample SQL in this plan for ops/analyst

---

## Non-goals (MVP)

- Kafka, Redis, warehouse, Mixpanel/PostHog  
- Real-time dashboards or charts in product UI  
- IP/geo tracking, cross-domain pixels  
- Blocking request path on analytics failure (try/except + log)

---

## Success criteria checklist

- [ ] Count users with `has_activated = true`
- [ ] Avg `duration_seconds` from `analytics_sessions`
- [ ] Returning users: distinct `user_id` with sessions in week 2 after first_seen
- [ ] Top `event_name` counts last 7 days
- [ ] Flag off: zero regression on login/dashboard
- [ ] `pytest tests/test_analytics.py` + full suite green

---

## Rollout

1. Deploy schema to **staging** with flag **off**  
2. Enable `ENABLE_PRODUCT_ANALYTICS=true` on staging only  
3. Internal dogfood 1 week; verify activation on share/PDF  
4. Production: flag off → deploy → flag on for admin test → full enable  

Env:

```bash
ENABLE_PRODUCT_ANALYTICS=true
ANALYTICS_SESSION_TIMEOUT_MINUTES=30
```

---

## Jira story mapping

| Phase | Stories (import CSV) |
|-------|----------------------|
| 1 | Schema, core module, feature flag, server instrumentation, activation |
| 2 | Client helper, admin summary, user activity API, connectors/insight events, tests, deploy docs |
| 2–3 | Retention queries story |

---

## Estimated effort

| Phase | Points (from CSV) | Calendar (1 dev) |
|-------|-------------------|------------------|
| Phase 1 | ~17 | 2–3 days |
| Phase 2 | ~13 | 2 days |
| **Total MVP** | **~30** | **~4–5 days** |

