# Portfolio Health Dashboard — Feasibility Review

**Reviewed doc:** `docs/portfolio-health-dashboard.md` (v1.0)
**Date:** 2026-06-05
**Reviewer goal:** Maximum CTO value, minimum code changes. No implementation.
**Method:** Each feature analyzed against the current codebase (Flask monolith, Postgres-only, server-rendered `templates/dashboard.html`).

---

## TL;DR

About **60% of the CTO value can ship as MVP with one additive column** (`target_monthly_burn`) and **zero new tables, zero background jobs** — by computing health/alerts/scores *live* from data the app already has, and reusing the existing connector `/test` endpoint for on-demand connector status.

The remaining 40% (trends, trajectories, "what changed", connector uptime history, risk prediction) is **fundamentally gated by two things the codebase does not have today**:

1. **Historical/time-series storage** — there is no `metrics`, `snapshot`, or `history` table; metrics are fetched live and discarded.
2. **A background job runner** — the app is a single gunicorn web process; nothing runs on a schedule.

Everything labeled "trend", "trajectory", "runway", "since last check", or "uptime" requires #1, and usually #2. Build those in Phase 2 once the snapshot table + scheduler exist.

---

## Current codebase capabilities (grounding)

| Capability | Status | Location |
|---|---|---|
| Assignment fields: `team_size`, `monthly_burn_rate`, `status`, `metrics_config` | Exists | `services/security/canonical_schema.py` |
| Overview aggregation: status counts, team-size sum, burn sum | Exists | dashboard Overview + `/api/assignments` |
| Live connector metrics (GitHub, Jira, AWS, OpenAI, Railway), parallel fetch | Exists | `collect_assignment_metrics()` in `routes/api_routes.py` |
| Connector credential validation / live test | Exists | `connectors/*/validator.py`, `/api/workspaces/<ws>/credentials/<type>/test` |
| Coarse audit log (action/entity/success) in Postgres | Exists | `audit_logs` table, `_audit_log()` in `postgres_store.py` |
| **Time-series metrics / history / snapshots** | Missing | (no table; metrics not persisted) |
| **`target_monthly_burn` / budget targets** | Missing | — |
| **Health score / attention-level fields** | Missing | — |
| **Connector health persistence (last sync, response time, failures)** | Missing | — |
| **Field-level change history (old→new) that persists on Railway** | Missing | file-based `AuditService` exists but writes to `config/audit/*.json` → ephemeral on Railway |
| **Background job / scheduler** | Missing | gunicorn web only; no APScheduler/Celery/cron |

### Architectural constraints that shape the plan
- **AWS metrics are slow (30–90s).** Any live health calc that touches AWS will be slow → strong reason to persist snapshots rather than compute on every page load.
- **Railway connector API is deprecated** (`services/embedded/railway_metrics.py` returns placeholders). "Failed deployments" should be sourced from **GitHub**, not Railway.
- **React component tree in the spec is N/A.** The product UI is server-rendered Flask templates (React is archived in `_attic/`). Implement via `dashboard.html` + JS, as the spec's "HTML/JavaScript" alternative already shows.
- **Change detection must use Postgres**, not the file-based `AuditService` (which won't survive a Railway redeploy).
- Per repo rules: feature-flag new behavior, keep additive/backward-compatible, no SQLite revival.

---

## Feature-by-feature analysis

Legend — **Tables?** = needs new DB tables · **History?** = needs historical data · **Jobs?** = needs background job · **Now?** = buildable with current code.

| # | Feature | Buildable now? | New tables? | Historical? | Background job? | Complexity | Phase |
|---|---|---|---|---|---|---|---|
| 1 | **Critical Alerts header** (budget exceeded, connector down, failed deploys) | Mostly (live-derived) | No (derive live); persistence optional | No | No (live) | Medium | **MVP** |
| 2 | **Portfolio Health Score** (point-in-time, sub-scores) | Yes, if `target_monthly_burn` added | No (1 column add) | No | No | Medium | **MVP** |
| 3 | **Assignment Health Score + attention level** (simplified, live) | Yes (financial + connector-up) | No | No | No | Medium | **MVP** |
| 4 | **Assignment Health Matrix** (table, no trend arrows) | Yes (UI over #2/#3) | No | No | No | Small–Medium | **MVP** |
| 5 | **Burn: current + variance vs target** | Yes (+`target_monthly_burn`) | No (1 column) | No | No | Small | **MVP** |
| 6 | **Connector Health (on-demand live status)** | Yes (reuse `/test` + validators) | No | No | No (live) | Medium | **MVP** |
| 7 | **Mobile-responsive layout / UX** | Yes (Tailwind templates) | No | No | No | Small–Medium | **MVP** |
| 8 | **Background scheduler (enabler)** (APScheduler in-process) | New infra | No | — | Is the job | Medium | **Phase 2** |
| 9 | **Connector Health monitoring** (last sync, response time, consecutive failures, auto-refresh) | Needs table + job | `connector_health_status` | Yes (recent) | Yes | Large | **Phase 2** |
| 10 | **Portfolio Health Snapshots + score trend** ("+5 this week") | Needs table + job | `portfolio_health_snapshots` | Yes | Yes | Medium | **Phase 2** |
| 11 | **Burn trajectory: trend % + runway** | Needs burn history | `portfolio_health_snapshots` (or burn history) | Yes | Yes | Medium | **Phase 2** |
| 12 | **Health Matrix trend indicators** (up/down arrows) | Needs history | uses #10 | Yes | Yes | Small (on top of #10) | **Phase 2** |
| 13 | **Recent Changes — assignment edits** (budget/team/status, event-on-write) | Partial (hook update path) | `portfolio_change_events` | Yes (stored events) | No (on write) | Medium | **Phase 2** |
| 14 | **Recent Changes — operational** (deploy failures, cost spikes via polling) | Needs job + history | `portfolio_change_events` | Yes | Yes | Large | **Phase 3** |
| 15 | **Full Risk Factor Detection** (velocity trend, team turnover, burnout) | Needs deep history | uses snapshots/history | Yes | Yes | Large | **Phase 3** |
| 16 | **Full weighted health score** (team velocity/stability inputs) | Needs history | uses #10 | Yes | Yes | Large | **Phase 3** |
| 17 | **Risk prediction** ("1–2 weeks before critical") | Needs trend modeling | uses history | Yes | Yes | Large | **Phase 3** |
| 18 | **Export health report** | Partial (export service exists) | No | Depends | No | Medium | **Phase 3** |
| 19 | **Alert notification system** (email/Slack push) | New integration + job | `alerts` (dedup/state) | No | Yes | Large | **Future** |
| 20 | **Schedule Review** (calendar) | New integration | Maybe | No | No | Medium | **Future** |
| 21 | **React component migration** (spec's component tree) | Against current arch | — | — | — | Large | **Future / Won't do** |

---

## Phase classification (value vs. change)

### MVP — live intelligence, ~1 column, no jobs, no history
**Features:** 1 Critical Alerts, 2 Portfolio Health Score (point-in-time), 3 Assignment Health Score + attention level, 4 Health Matrix (no trends), 5 Burn current + variance, 6 Connector Health (on-demand), 7 Mobile/UX.

**Only schema change:** add `target_monthly_burn INTEGER` to `assignments` (additive, default NULL → fall back to `monthly_burn_rate` so variance = 0 when unset). One column in `canonical_schema.py`, backward-compatible.

**Why it's high value / low cost:** delivers the "30-second decision" core — *what needs attention, who's healthy/at-risk, which connectors are down, what's my total burn vs budget* — entirely from data already in Postgres + live connector calls, with no new storage or scheduling.

**Watch-outs:**
- Compute scores from already-loaded assignment data; **don't trigger AWS on every Overview load** (too slow). Connector "down" detection should rely on cheap validators / cached test results, and AWS-dependent alerts should degrade gracefully.
- Connector health on-demand = a button or lazy async call, not a blocking page render.
- New endpoints should be additive (`/api/v1/portfolio/...`) behind a feature flag; leave existing Overview working.

### Phase 2 — persistence + scheduler unlocks trends
**Enabler first:** 8 background scheduler (in-process APScheduler is the KISS choice; Railway cron is the alternative). Then 9 connector health monitoring, 10 portfolio snapshots + score trend, 11 burn trajectory/runway, 12 matrix trend arrows, 13 change events on write.

**New tables:** `portfolio_health_snapshots`, `connector_health_status`, `portfolio_change_events` (add to `canonical_schema.py`, bump `schema_version`).

**Why now and not MVP:** every "trend / trajectory / runway / since last check / uptime" claim needs accumulated history, which needs a writer (job) and a place to write (tables). Snapshots also solve the AWS-slowness problem by decoupling display from live fetch.

### Phase 3 — operational intelligence
14 operational change detection, 15 full risk factors, 16 full weighted health, 17 risk prediction, 18 export health report. All depend on a meaningful history window (weeks) existing first, plus heavier detection/analytics logic.

### Future — outside current architecture
19 notifications (needs delivery infra + alert state), 20 schedule review (calendar integration), 21 React migration (contradicts the server-rendered architecture; the spec's React tree should be treated as illustrative, not a target).

---

## Direct answers to the 5 questions

**1. Buildable with current codebase (no new tables/jobs):**
Critical alerts (live-derived), point-in-time portfolio health score, simplified assignment health score + attention level, health matrix (no trend), burn current + variance (needs the one `target_monthly_burn` column), on-demand connector health (reuse `/test`), mobile/UX. → **MVP.**

**2. Require new database tables:**
- `portfolio_health_snapshots` (score/burn trend, runway)
- `connector_health_status` (uptime, last sync, response time, consecutive failures)
- `portfolio_change_events` (recent changes feed)
- Plus an additive column `assignments.target_monthly_burn` (and optionally cached `health_score`/`attention_level` columns if we want to avoid recompute).

**3. Require historical data:**
Health-score trend ("+5 this week"), burn trajectory %/runway, matrix trend arrows, recent-changes feed, all risk-trend factors (velocity, turnover), risk prediction. None of this is possible until snapshots start accumulating.

**4. Require background jobs:**
Connector health monitoring loop, periodic portfolio snapshotting, operational change detection (deploy/cost-spike polling), notification dispatch. (Assignment-edit change events are the exception — capturable on write, no job.)

**5. Complexity estimates:** see the table column — Small (<1d): #5, #7, #12. Medium (1–3d): #1, #2, #3, #4, #6, #8, #10, #11, #13, #18, #20. Large (>3d): #9, #14, #15, #16, #17, #19, #21.

---

## Recommended minimal-change path

1. **MVP (days, not weeks):** add `target_monthly_burn`; add feature-flagged `/api/v1/portfolio/health`, `/alerts`, `/assignments/health-matrix`, `/connectors/health` that compute live from existing assignment data + cheap connector checks; render the new Overview in `dashboard.html`. No jobs, no history tables. This captures the bulk of the "30-second CTO" value.
2. **Phase 2:** introduce APScheduler + the three history tables; snapshot portfolio/connector state on a schedule; layer trends/trajectory/uptime/change-feed onto the existing MVP cards.
3. **Phase 3+:** richer detection, prediction, exports, then notifications/calendar as genuinely new subsystems.

**Biggest risks to call out before building:** (a) AWS latency forcing premature caching — solve via snapshots, not synchronous calls; (b) treating the file-based `AuditService` as a change-history source — it won't persist on Railway, use Postgres; (c) scope-creeping the scheduler into MVP — keep MVP live-computed and stateless.
