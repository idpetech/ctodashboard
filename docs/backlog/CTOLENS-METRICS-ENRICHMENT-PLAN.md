# CTOLens Metrics Enrichment — Plan & Execution TODO

**Status:** Backlog (not implemented)  
**Created:** 2026-06-05  
**Related:** `services/briefing_pipeline.py`, `routes/api_routes.py` (`collect_assignment_metrics`), CTOLens dashboard panel  
**Jira import:** `docs/backlog/CTOLENS-METRICS-ENRICHMENT-JIRA.csv`

---

## Problem

Users cannot tell whether connectors ran during briefing generation. Today:

- Default briefing paths use `fetch_metrics=false` (no live connector calls).
- **+ live metrics** is the only path that fetches connectors (slow, ~90s+).
- `metrics_fetched` is stored but not shown in the UI.
- `build_metrics_overlays()` maps minimal GitHub/Jira fields; new opportunity overlay fields are not wired.
- Reports may include raw `signals[]` unless explicitly stripped.
- Staleness tracks assignment fingerprint only, not metrics refresh age.

**Unconfigured connectors:** not enabled in assignment `metrics_config` → ignore silently (not an issue).

---

## Design principles

1. **Read never blocks** — login/dashboard load reads last stored briefing only.
2. **Two run types** — fast (assignment/budget) vs enriched (live connectors).
3. **Executive surface stays small** — capped risks/opportunities/actions.
4. **Diagnostics opt-in** — collapsed dashboard section; excluded from share/PDF.
5. **Always show last run** — one line in briefing header.
6. **Scheduled enrichment off critical path** — workspace-configurable periodic full run.
7. **Log operational runs** — app logs + rolling run history in workspace settings.

---

## Two run types

### A. Fast briefing (default)

| | |
|---|---|
| **Input** | Assignment rows (burn, team, owner, metrics_config flags) |
| **Signals** | Financial, portfolio, operational; connector failure if prior run recorded failures |
| **When** | Login load, assignment staleness refresh, import hook |
| **Duration** | Sub-second to few seconds |
| **UX label** | "Briefing updated · assignment data only" |

### B. Enriched briefing (scheduled or manual)

| | |
|---|---|
| **Input** | Assignments + `collect_assignment_metrics()` per active assignment (enabled connectors only) |
| **Signals** | A + delivery/opportunity when overlay mapping exists |
| **When** | Workspace schedule OR explicit "Refresh live metrics" |
| **Duration** | Up to ~90s+ (parallel per assignment) |
| **UX label** | "Last live metrics run: {time} · {N} assignments · {connectors} OK" |

---

## Workspace settings schema (planned)

Key: `workspace.settings.ctolens_schedule`

```json
{
  "enabled": false,
  "frequency": "manual_only",
  "time_utc": "06:00",
  "day_of_week": "monday",
  "on_import": false
}
```

Run metadata key: `workspace.settings.ctolens_run_status`

```json
{
  "last_fast_run_at": "ISO",
  "last_enriched_run_at": "ISO",
  "last_enriched_run_source": "scheduled|manual|import",
  "metrics_fetched": true,
  "assignments_evaluated": 4,
  "connectors_attempted": ["github", "jira"],
  "duration_seconds": 47,
  "status": "success|partial|failed"
}
```

Rolling log key: `workspace.settings.ctolens_run_log` (last 10 entries)

---

## UX surfaces

### Always visible (briefing header)

- Last briefing generated at
- Whether last run used live metrics (`metrics_fetched`)
- Next scheduled run (if enabled)
- Separate staleness: assignment changed vs metrics age

### Collapsed diagnostics (dashboard only, NOT in reports)

`<details>` panel: "Signal & connector details"

- Run id, timestamps, duration, source
- Per active assignment: enabled connectors attempted, success/error (one line)
- Skip unconfigured/disabled connectors
- Signal counts: evaluated N · shown in briefing M
- Link to last 10 runs in workspace log

### Button labels (planned rename)

| Current | Planned |
|---------|---------|
| Update briefing | Update briefing (fast) |
| + live metrics | Refresh live metrics |

---

## Report / PDF boundary

Strip from `normalize_briefing_for_export()` and PDF:

- Raw `signals[]`
- `ctolens_run_status`, `ctolens_run_log`
- Collapsed diagnostics payload

Keep in exports: executive summary, top risks, opportunities (summarized), recommended actions, executive_focus.

---

## Signal overwhelm guardrails

- Keep `pre_sorted` caps (opportunities max 8).
- Consider: delivery/opportunity signals in executive view only when `metrics_fetched=true` for that generation.
- Diagnostics panel holds full evaluated signal list.
- Unconfigured connectors never shown as warnings.

---

## Phased rollout — EXECUTION TODO

### Phase 0 — Clarify today (low risk)

- [ ] Show `generated_at` + `metrics_fetched` in CTOLens panel header
- [ ] Rename refresh buttons (fast vs live metrics)
- [ ] Strip diagnostics/raw signals from share/PDF export path
- [ ] Confirm GET `/ctolens/briefing` never calls `fetch_metrics=true`
- [ ] Document behavior pointer in `docs/HYBRID-BRIEFING-ENGINE.md`

### Phase 1 — Run metadata + collapsed diagnostics

- [ ] Persist `ctolens_run_status` on every fast/enriched run
- [ ] Persist rolling `ctolens_run_log` (max 10)
- [ ] Collapsed diagnostics UI in `dashboard.html`
- [ ] Separate staleness: assignment fingerprint vs metrics age
- [ ] Fix `build_metrics_overlays()` GitHub/Jira core mapping (7d/14d/prior commits, jira 7d)
- [ ] Structured app logs: `briefing_run_started` / `briefing_run_completed`

### Phase 2 — Workspace schedule + Railway cron

- [ ] Workspace settings UI for schedule (frequency, time UTC, on_import)
- [ ] API: GET/PUT schedule in workspace settings
- [ ] Protected endpoint: `POST /api/internal/ctolens/scheduled-refresh` (secret header)
- [ ] Railway cron service hitting endpoint per deployment
- [ ] On scheduled failure: keep last good briefing, log partial status
- [ ] Feature flag: `ENABLE_CTOLENS_SCHEDULED_ENRICHMENT` (default false)

### Phase 3 — Polish

- [ ] Map PR/build/release overlay fields when connector payloads support them
- [ ] Per-workspace cap on assignments per enriched run
- [ ] Optional enriched run after import (`on_import`, default off)
- [ ] Metrics staleness warning threshold (configurable, e.g. 24h/7d)

---

## Open decisions (resolve before Phase 2)

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | Auto-generate briefing on first GET? | Empty state + user click (or keep fast auto-generate only) |
| 2 | Default schedule for new workspaces? | Off (`manual_only`) |
| 3 | Enriched staleness warn threshold? | 7 days |
| 4 | Failed scheduled run UX? | Keep previous briefing + log error |
| 5 | Cron auth? | Shared secret header on internal endpoint |

---

## Prerequisites

Enriched runs are only valuable after **Phase 1 overlay mapping** is fixed.

---

## Validation checklist (when implementing)

- [ ] Login/dashboard load completes without connector HTTP calls
- [ ] Fast refresh completes in <5s typical workspace
- [ ] Live metrics refresh shows progress and updates last run line
- [ ] Collapsed panel not present in share URL or PDF
- [ ] Unconfigured connectors absent from diagnostics
- [ ] All existing `tests/` pass (58+)
- [ ] New tests for run metadata persistence and export stripping

---

## References

- `services/briefing_pipeline.py` — `build_metrics_overlays`, `run_ctolens_pipeline`
- `routes/api_routes.py` — `collect_assignment_metrics`, CTOLens API routes
- `services/briefing_resolver.py` — `normalize_briefing_for_export`, `ensure_stored_briefing`
- `templates/dashboard.html` — CTOLens panel, refresh buttons
- `templates/workspace_settings.html` — future schedule UI
