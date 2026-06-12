# Product Backlog (local)

Backlog items for Jira import and execution tracking.

## Active chapter (discussion draft)

| File | Purpose |
|------|---------|
| [CHAPTER-PORTFOLIOS-PRICING-CONNECTORS-PLAN.md](./CHAPTER-PORTFOLIOS-PRICING-CONNECTORS-PLAN.md) | **Draft** — Portfolios (flag) → Pro pricing → backlog catch-up → connectors |

## CTOLens & briefing

| File | Purpose |
|------|---------|
| [CTOLENS-METRICS-ENRICHMENT-PLAN.md](./CTOLENS-METRICS-ENRICHMENT-PLAN.md) | Full plan + execution TODO checklist (Phases 0–2 shipped; Phase 3 backlog) |
| [CTOLENS-METRICS-ENRICHMENT-JIRA.csv](./CTOLENS-METRICS-ENRICHMENT-JIRA.csv) | Jira bulk import (Epic + Stories) |
| [CTOLENS-SCHEDULED-ENRICHMENT-SCALE-PLAN.md](./CTOLENS-SCHEDULED-ENRICHMENT-SCALE-PLAN.md) | Scalable scheduler: due-time filtering, per-tick caps, single cron |

## Product analytics

| File | Purpose |
|------|---------|
| [CTOLENS-PRODUCT-ANALYTICS-JIRA.csv](./CTOLENS-PRODUCT-ANALYTICS-JIRA.csv) | Jira import — Product analytics epic (HIGH) |
| [PRODUCT-ANALYTICS-PLAN.md](./PRODUCT-ANALYTICS-PLAN.md) | Product analytics MVP plan (Phases 1–2 shipped; Phase 3 pending) |

## Signals & GitHub

| File | Purpose |
|------|---------|
| [CTOLENS-REPO-ISSUE-ACTIONS-JIRA.csv](./CTOLENS-REPO-ISSUE-ACTIONS-JIRA.csv) | Jira import — Repo issue attention & actions |
| [CTOLENS-REPO-ISSUE-ACTIONS-PLAN.md](./CTOLENS-REPO-ISSUE-ACTIONS-PLAN.md) | Repo issue UX plan |
| [CTOLENS-JIRA-INSIGHTS-FIX-JIRA.csv](./CTOLENS-JIRA-INSIGHTS-FIX-JIRA.csv) | Jira import — Fix insight false positives (HIGH) |
| [CTOLENS-JIRA-INSIGHTS-FIX-PLAN.md](./CTOLENS-JIRA-INSIGHTS-FIX-PLAN.md) | Jira metrics/insights accuracy plan |

## Jira import

1. Jira → **Settings** → **System** → **External system import** → **CSV**
2. Import the relevant `*-JIRA.csv` for the epic you are executing
3. Map columns: Summary → Summary, Issue Type → Issue Type, Description → Description, etc.
4. If your project uses **Epic Name** instead of **Epic Link**, rename the CSV header before import.
5. After import, link the Epic and set your project fix version/sprint as needed.

## Status notes

- **Chapter plan (portfolios/pricing/connectors):** Draft — not approved (2026-06-11)
- **Metrics enrichment / analytics:** Partially shipped — see individual plan files for phase checkboxes
- **Scheduler scale, Jira fix, repo actions:** Backlog — not implemented
