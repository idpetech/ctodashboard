# Hybrid Signal + Recommendation + Narrative Engine

See `services/signals/`, `services/recommendations/`, `services/executive_briefing/`, and `services/briefing_pipeline.py`.

Four layers: Signal → Recommendation → Executive Narrative (optional LLM polish) → Feedback.

Success criteria live in `services/executive_briefing/success_criteria.py` as `executive_focus` (biggest risk, opportunity, do first, why, confidence).

LLM guardrails: summarize only; `_apply_deterministic_truth()` restores ranked actions and focus from rules engine.

## Backlog: metrics enrichment & scheduled runs

Planned work (not implemented): fast vs enriched briefing runs, last-run visibility, collapsed diagnostics, workspace schedule.

- Plan + execution TODO: [backlog/CTOLENS-METRICS-ENRICHMENT-PLAN.md](./backlog/CTOLENS-METRICS-ENRICHMENT-PLAN.md)
- Jira CSV import: [backlog/CTOLENS-METRICS-ENRICHMENT-JIRA.csv](./backlog/CTOLENS-METRICS-ENRICHMENT-JIRA.csv)
