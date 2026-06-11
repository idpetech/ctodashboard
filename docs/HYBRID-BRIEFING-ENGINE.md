# Hybrid Signal + Recommendation + Narrative Engine

See `services/signals/`, `services/recommendations/`, `services/executive_briefing/`, and `services/briefing_pipeline.py`.

Four layers: Signal → Recommendation → Executive Narrative (optional LLM polish) → Feedback.

Success criteria live in `services/executive_briefing/success_criteria.py` as `executive_focus` (biggest risk, opportunity, do first, why, confidence).

LLM guardrails: summarize only; `_apply_deterministic_truth()` restores ranked actions and focus from rules engine.

## Metrics enrichment & scheduled runs (Phases 0–2)

**Status:** Phases 0–2 implemented (2026-06-05). Phase 3 (PR/build overlays, import hook, caps) remains backlog.

- **Fast vs enriched runs:** dashboard buttons *Update briefing (fast)* vs *Refresh live metrics*; GET briefing never fetches connectors.
- **Run metadata:** `workspace.settings.ctolens_run_status` and rolling `ctolens_run_log` (max 10); collapsed diagnostics panel on dashboard.
- **Export/share:** `strip_briefing_for_export()` removes raw `signals[]`, diagnostics, and run internals from PDF/share paths.
- **Schedule:** workspace settings UI + `GET/PUT /api/workspaces/<id>/ctolens/schedule`; cron via `POST /api/internal/ctolens/scheduled-refresh` with header `X-CTOLens-Cron-Secret` (env `CTOLENS_CRON_SECRET` or `INTERNAL_CRON_SECRET`). Feature flag: `ENABLE_CTOLENS_SCHEDULED_ENRICHMENT` (default false).

- Plan + execution TODO: [backlog/CTOLENS-METRICS-ENRICHMENT-PLAN.md](./backlog/CTOLENS-METRICS-ENRICHMENT-PLAN.md)
- Jira CSV import: [backlog/CTOLENS-METRICS-ENRICHMENT-JIRA.csv](./backlog/CTOLENS-METRICS-ENRICHMENT-JIRA.csv)
