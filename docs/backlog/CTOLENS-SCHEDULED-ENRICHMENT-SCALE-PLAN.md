# CTOLens Scheduled Enrichment — Scalable Scheduler (Backlog)

**Status:** Backlog — not implemented  
**Created:** 2026-06-11  
**Priority:** Medium (required before many workspaces / mixed schedules)  
**Related:** `routes/api/briefing.py` (`ctolens_scheduled_refresh`), `services/ctolens_run_metadata.py`, `docs/DEPLOYMENT.md`

**Parent epic:** [CTOLENS-METRICS-ENRICHMENT-PLAN.md](./CTOLENS-METRICS-ENRICHMENT-PLAN.md) (Phase 2 shipped; this is Phase 2.5 / scale follow-up)

---

## Problem

The shipped MVP uses **one Railway cron → one HTTP POST → sequential loop over all workspaces** where `ctolens_schedule.enabled = true`.

That works for a **small number of workspaces on a shared schedule**, but does not scale because:

1. **`time_utc`, `frequency`, and `day_of_week` are stored but not enforced** — every cron tick runs all enabled workspaces, not only those “due now”.
2. **Per-workspace schedules cannot differ** without multiple Railway crons + `workspace_id` in the body (operational burden, not product-scale).
3. **One long synchronous HTTP request** — each enriched run may take 90+ seconds; N workspaces → timeout risk and no partial progress recovery.
4. **No job queue** — failure mid-loop does not enqueue retries for remaining workspaces.

**Clarification (common misconception):** Production today does **not** require one Railway cron per workspace. One cron is enough; the gap is **in-app scheduling and async execution**, not more Railway services.

---

## Goal

Support **many workspaces with independent schedules** using:

- **One platform cron** (e.g. every 15–60 minutes)
- **In-app “due now” filter** per workspace schedule
- **Bounded, resumable work** (no single request processing unlimited tenants)

---

## Recommended approach (phased)

### Phase A — Due-time filtering (minimal, high value)

Add `should_run_enriched_now(schedule, last_enriched_run_at, now_utc) -> bool` in `services/ctolens_run_metadata.py`:

- Respect `frequency`: `daily` | `weekly` | `manual_only`
- Respect `time_utc` (UTC) and `day_of_week` for weekly
- Skip if already ran within the same calendar window (idempotency)
- Cron endpoint: only call `refresh_workspace_ctolens_briefing` when due

**Railway:** Single cron, e.g. `*/15 * * * *` (every 15 minutes). App decides who runs.

**Acceptance:**

- [ ] Workspace set to daily 06:00 UTC runs at most once per day near that time
- [ ] Workspace with `enabled: false` never runs
- [ ] `manual_only` never runs from cron (manual / on_import only)
- [ ] Tests for daily, weekly, already-ran-today, timezone edge cases

### Phase B — Request budget + async handoff (scale)

Avoid one HTTP request doing all work:

1. Cron POST returns **202 quickly** after enqueueing due workspace IDs
2. Process workspaces with a **per-tick cap** (e.g. max 3 enriched runs per invocation)
3. Store `ctolens_run_queue` or use a simple `pending_enriched_run_at` flag in workspace settings
4. Optional: background thread / Railway worker process (same repo, separate service) consuming queue

**Acceptance:**

- [ ] Cron HTTP completes in <10s even with 50+ enabled workspaces
- [ ] Remaining due workspaces picked up on next tick
- [ ] Run log records skipped/deferred with reason

### Phase C — Observability (ops)

- [ ] Admin or workspace settings: “next scheduled run”, “last error”, queue depth
- [ ] Structured logs: `scheduled_enrichment_tick`, `workspace_due`, `workspace_deferred`, `workspace_completed`
- [ ] Alert hook when enriched run fails N times in a row (future)

---

## Non-goals (this backlog item)

- Separate cron job per workspace (explicitly rejected)
- Distributed job system (Redis, Celery, etc.) — defer until proven need
- Sub-minute scheduling precision

---

## Current behavior (document for operators)

Until Phase A ships, operators should:

1. Use **one Railway cron** aligned with the **shared** UTC time workspaces expect
2. Only enable schedule on workspaces that need live metrics
3. Use `{"workspace_id": "..."}` body only for manual/testing or intentional split loads

See `docs/DEPLOYMENT.md` — CTOLens scheduled enrichment section.

---

## Open decisions

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | Cron tick interval | Every 15 minutes |
| 2 | Missed window (app down at 06:00) | Run on next tick if not yet run today |
| 3 | Max workspaces per tick | 3 (configurable env `CTOLENS_SCHEDULED_MAX_PER_TICK`) |
| 4 | Parallel enriched runs | Sequential per tick initially; parallel per assignment already exists inside one workspace |

---

## Suggested env vars (future)

| Variable | Default | Purpose |
|----------|---------|---------|
| `CTOLENS_SCHEDULED_MAX_PER_TICK` | `3` | Cap workspaces processed per cron invocation |

Existing: `ENABLE_CTOLENS_SCHEDULED_ENRICHMENT`, `CTOLENS_CRON_SECRET`.

---

## Validation checklist (when implementing)

- [ ] 10 workspaces, mixed daily/weekly schedules — only due ones run on each tick
- [ ] No duplicate enriched run same day after success
- [ ] Cron with 20 enabled workspaces completes without gateway timeout (Phase B)
- [ ] Failed workspace does not block others
- [ ] All existing `tests/` pass; new unit tests for `should_run_enriched_now`

---

## References

- `POST /api/internal/ctolens/scheduled-refresh` — `routes/api/briefing.py`
- `get_workspace_schedule`, `DEFAULT_SCHEDULE` — `services/ctolens_run_metadata.py`
- Workspace schedule UI — `templates/workspace_settings.html`
