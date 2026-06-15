# Repo checkpoints

Tagged restore points before risky changes. Use these if a refactor goes south.

## Active checkpoints

| Tag | Date | Purpose | Restore |
|-----|------|---------|---------|
| `ctolens/phase-1-homepage-complete` | 2026-06-14 | CTOLens Phase 1 — honest homepage & unified signup funnel (`5b203cb`) | See below |
| `checkpoint/pre-cto-briefing-2026-06-06` | 2026-06-06 | Stable state before CTO Briefing flow redesign | See below |

### CTOLens Phase 1 — homepage complete (`ctolens/phase-1-homepage-complete`)

- Marketing homepage rebuilt: hero → integrations → pain → features → sample Overview → pricing → final CTA
- All CTAs: **Start Free Assessment** → `/dashboard?signup=1`
- Honest copy only (no fake reviews, no unsupported integrations)
- Deployed: `staging` + `master` on Railway
- **Phase doc:** [CTOLENS-PHASES.md](./CTOLENS-PHASES.md)
- **Next:** Phase 2 — conversion analytics, product proof, signup → first briefing

```bash
git fetch origin --tags
git checkout ctolens/phase-1-homepage-complete
```

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
