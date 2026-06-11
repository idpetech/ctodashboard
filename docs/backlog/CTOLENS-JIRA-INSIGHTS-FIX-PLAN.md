# CTOLens — Fix Jira insight false positives

**Status:** Backlog (not implemented)  
**Created:** 2026-06-10

## Problem

Dashboard **Project Management Insights** uses naive thresholds on misleading metrics:

- **Resolution rate** = resolved ÷ issues **created** in last 30 days. New tickets cannot resolve in-window → always looks "low" on active projects (e.g. 58 created, 20 resolved = 34.5% 🔴).
- **High volume** fires at `> 50` created/month — normal for planning-heavy teams.
- **Generic bullets** (retrospectives, cycle time) always show — noise, not signal.

## Fix direction

1. **Metrics:** Use throughput (resolved in 30d), backlog age, open count — not created-vs-resolved in same window.
2. **Insights:** Only show when signal rules fire; remove always-on generic advice.
3. **Context:** Label metrics accurately ("Created last 30d", not implied health score).
4. **Thresholds:** Workspace-configurable or CTOLens signal engine — not hardcoded 70% / 50.

See [CTOLENS-JIRA-INSIGHTS-FIX-JIRA.csv](./CTOLENS-JIRA-INSIGHTS-FIX-JIRA.csv).
