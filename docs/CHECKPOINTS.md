# Repo checkpoints

Tagged restore points before risky changes. Use these if a refactor goes south.

## Active checkpoints

| Tag | Date | Purpose | Restore |
|-----|------|---------|---------|
| `checkpoint/pre-cto-briefing-2026-06-06` | 2026-06-06 | Stable state before CTO Briefing flow redesign | See below |

### What this checkpoint includes

- Working dashboard header, connector modals, Jira test connection fixes
- Attention engine + portfolio health panels (`ENABLE_ATTENTION_ENGINE`, `ENABLE_PORTFOLIO_DASHBOARD`)
- Briefing annotation: `docs/CTO-BRIEFING-FLOW.md`
- Latest commit on `master` at tag time

### How to restore (read-only inspect)

```bash
git fetch origin --tags
git checkout checkpoint/pre-cto-briefing-2026-06-06
```

### How to reset `master` to this checkpoint (destructive)

**Warning:** discards all commits after the checkpoint on your local branch.

```bash
git fetch origin --tags
git checkout master
git reset --hard checkpoint/pre-cto-briefing-2026-06-06
```

To update remote (only if you intend to roll back production):

```bash
git push origin master --force-with-lease
```

### Safer alternative: branch from checkpoint

```bash
git fetch origin --tags
git checkout -b recovery/from-checkpoint-2026-06-06 checkpoint/pre-cto-briefing-2026-06-06
```

Deploy or merge from that branch instead of force-pushing `master`.
