# Product Backlog (local)

Backlog items for Jira import and execution tracking.

| File | Purpose |
|------|---------|
| [CTOLENS-METRICS-ENRICHMENT-PLAN.md](./CTOLENS-METRICS-ENRICHMENT-PLAN.md) | Full plan + execution TODO checklist |
| [CTOLENS-METRICS-ENRICHMENT-JIRA.csv](./CTOLENS-METRICS-ENRICHMENT-JIRA.csv) | Jira bulk import (Epic + Stories) |

| [CTOLENS-PRODUCT-ANALYTICS-JIRA.csv](./CTOLENS-PRODUCT-ANALYTICS-JIRA.csv) | Jira import — Product analytics epic (HIGH) |
| [PRODUCT-ANALYTICS-PLAN.md](./PRODUCT-ANALYTICS-PLAN.md) | Product analytics MVP plan + execution |
| [CTOLENS-REPO-ISSUE-ACTIONS-JIRA.csv](./CTOLENS-REPO-ISSUE-ACTIONS-JIRA.csv) | Jira import — Repo issue attention & actions |
| [CTOLENS-REPO-ISSUE-ACTIONS-PLAN.md](./CTOLENS-REPO-ISSUE-ACTIONS-PLAN.md) | Repo issue UX plan |
| [CTOLENS-JIRA-INSIGHTS-FIX-JIRA.csv](./CTOLENS-JIRA-INSIGHTS-FIX-JIRA.csv) | Jira import — Fix insight false positives (HIGH) |
| [CTOLENS-JIRA-INSIGHTS-FIX-PLAN.md](./CTOLENS-JIRA-INSIGHTS-FIX-PLAN.md) | Jira metrics/insights accuracy plan |


## Jira import

1. Jira → **Settings** → **System** → **External system import** → **CSV**
2. Import `CTOLENS-METRICS-ENRICHMENT-JIRA.csv`
3. Map columns: Summary → Summary, Issue Type → Issue Type, Description → Description, etc.
4. If your project uses **Epic Name** instead of **Epic Link**, rename the CSV header before import.
5. After import, link the Epic and set your project fix version/sprint as needed.

## Status

All items: **Backlog — not implemented** (as of 2026-06-10).
