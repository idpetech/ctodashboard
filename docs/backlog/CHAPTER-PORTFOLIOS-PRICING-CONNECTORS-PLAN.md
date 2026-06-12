# Chapter Plan — Portfolios, Pricing (Pro), Backlog Catch-up, Connectors

**Status:** Draft for discussion (not approved for implementation)  
**Created:** 2026-06-11  
**Audience:** Founders + fractional CTOs (primary); consultancy deferred  
**Principle:** Path of least resistance — feature-flag first, no customer-visible change until Pro tier is ready

---

## Chapter summary (one arc)

| Act | Theme | Customer-visible? | Pricing |
|-----|--------|-------------------|---------|
| **1** | Portfolios in code (`ENABLE_PORTFOLIOS=false`) | No | Unchanged (Trial + Starter $49) |
| **2** | Attach portfolios to **Professional** ($149) | Yes | Three plans only: Trial, Starter, Pro |
| **3** | Return to core product backlog | Yes (fixes/features) | Frozen at three plans |
| **4** | Connector breadth (Azure, Railway, Vercel, Supabase) | Yes | Same plans — connectors are not a tier |

**Close chapter** when Act 4 connectors are in assignment setup + briefing overlays (KISS parity with GitHub/Jira/AWS).

---

## Current baseline (do not break)

- **Model today:** User → Workspace → Assignment  
- **Billing today:** 7-day trial → Starter **$49/mo** (Stripe); Professional **$149** exists in code but not checkout  
- **Briefing today:** Workspace-scoped (`workspace.settings` — attention + CTOLens); Overview aggregates all assignments  
- **`portfolio_service.py`:** Computes workspace rollup from assignments — **not** a Portfolio entity yet  

---

## Target model (end of Act 1)

```
User
 └── Workspace
      └── Portfolio          ← new grouping (client / company / product line)
           └── Assignment     ← existing; gains portfolio_id
```

**Briefing scopes (stored separately, same engines):**

| Scope | Input | Primary user |
|-------|--------|--------------|
| Workspace | All assignments in workspace | Fractional rollup |
| Portfolio | Assignments in one portfolio | Fractional daily client brief |
| Assignment | Single assignment | Founder + drill-down |

**Backward compatibility:** Every workspace gets implicit portfolio `default` ("Main"); all legacy assignments map to it → behavior identical to today when flag is off.

---

## Act 1 — Portfolios behind feature flag (no pricing change)

**Flag:** `ENABLE_PORTFOLIOS` (default `false` everywhere)

### Data (minimal)

- `workspace.settings.portfolios[]` — `{ id, name, description, sort_order }`
- `assignments.portfolio_id` — default `'default'` (prefer column + migration; document in discussion)
- Auto-create `default` portfolio on workspace read if missing

### Backend

- Portfolio CRUD in workspace settings API (flag-gated)
- Filtered runs of existing `portfolio_service` / `attention_engine` / `briefing_pipeline` by assignment subset
- Storage keys (proposal):
  - Workspace: existing (`attention_briefing`, CTOLens workspace snapshot)
  - Portfolio: `workspace.settings.portfolio_briefings[portfolio_id]`
  - Assignment: `workspace.settings.assignment_briefings[assignment_id]`

### UI

- **None in prod** while flag off
- Staging/dev: optional admin-only or flag-on QA

### Exit criteria

- [ ] Flag off → zero regression (login, workspaces, Overview, trial, Starter checkout)
- [ ] Flag on in staging → create portfolio, assign assignment, generate portfolio + assignment briefings
- [ ] Import/export includes portfolios + portfolio_id
- [ ] Tests for default portfolio migration and scoped briefing keys
- [ ] `docs/CURRENT-ARCHITECTURE.md` pointer (when implemented)

### Explicitly out of scope (Act 1)

- Pricing / Stripe changes  
- Landing page Pro column  
- Portfolio limits enforcement  
- Enriched cron per portfolio  

---

## Act 2 — Pricing: three plans; portfolios on Professional only

**Commercial model (keep it three — no fourth tier in this chapter):**

| Plan | Price | Portfolios | Positioning |
|------|-------|------------|-------------|
| **Trial** | $0 / 7 days | Starter-shaped (no portfolio UI, or 1 default only) | Try full briefing |
| **Starter** | $49/mo | **No multi-portfolio** — single company (default bucket only) | Founder / solo |
| **Professional** | $149/mo | **Multi-portfolio** + portfolio briefing + portfolio share (when ready) | Fractional / multi-client |

### Stripe / code

- Add `professional` to `CHECKOUT_PLANS` in `stripe_billing_service.py`
- Env: `STRIPE_PRICE_PROFESSIONAL` (or product id) on Railway
- Plan enforcement: create portfolio (beyond default), portfolio briefing APIs, portfolio switcher UI → require `plan === professional` (or active Pro subscription)
- Upgrade path: Profile → Billing (existing pattern) + landing CTA for Pro

### Landing / copy (discussion tomorrow)

- Starter: "One company · daily CTO briefing"  
- Pro: "Multiple clients · briefing per portfolio"  
- Trial: unchanged entry; consider showing Pro only on pricing page, not separate signup URL confusion  

### Exit criteria

- [ ] Starter users cannot create second portfolio (clear upgrade message)
- [ ] Pro checkout works staging + prod
- [ ] `ENABLE_PORTFOLIOS=true` only when user is Pro **or** flag used for gradual UI rollout tied to plan
- [ ] Billing portal shows correct plan name and renewal

### Open questions for discussion

1. Enable portfolio **UI** for Pro only, or flag on globally but API enforces plan?  
2. Trial users: strict Starter limits or full Pro preview for 7 days?  
3. Grandfather existing Starter users if they already have many assignments?  
4. Professional naming on landing: "Professional" vs "Pro" vs "Multi-client"  

---

## Act 3 — Return to core backlog (pricing frozen)

After Acts 1–2 ship, **pause** portfolio/pricing work except bugs. Resume product backlog:

| Priority | Item | Rationale |
|----------|------|-----------|
| 1 | Jira insights fix (`CTOLENS-JIRA-INSIGHTS-FIX-PLAN.md`) | Trust / false positives |
| 2 | Scheduler scale Phase A (`CTOLENS-SCHEDULED-ENRICHMENT-SCALE-PLAN.md`) | Pro users with many portfolios + cron |
| 3 | Metrics enrichment Phase 3 (`CTOLENS-METRICS-ENRICHMENT-PLAN.md`) | Deeper briefings |
| 4 | Repo issue actions (`CTOLENS-REPO-ISSUE-ACTIONS-PLAN.md`) | Actionable GitHub signal |
| 5 | Product analytics Phase 3 (`PRODUCT-ANALYTICS-PLAN.md`) | Starter → Pro conversion data |
| 6 | Mobile briefing shell (optional) | Fractional read path |

**Not in Act 3:** annual billing, consultancy seats, per-portfolio metering, persona signup fields.

---

## Act 4 — Connector chapter close

Extend existing assignment connector pattern (credentials + `metrics_config` + embedded metrics + briefing overlays):

| Connector | Priority | Notes |
|-----------|----------|--------|
| **Railway** | High | May exist in embedded services — productize in UI if incomplete |
| **Vercel** | High | Founder-heavy deploy signal |
| **Azure** | Medium | Infra/cost for enterprise-adjacent fractionals |
| **Supabase** | Medium | Optional; DB/auth/hosting for founder stack |

**Per connector (repeatable checklist):**

- [ ] `config/connectors/*.json` field schema  
- [ ] Credential storage + test connection  
- [ ] `metrics_config.{connector}.enabled`  
- [ ] Embedded metrics module + parallel fetch in `collect_assignment_metrics`  
- [ ] Briefing overlay mapping (fast path minimum)  
- [ ] Workspace settings + assignment edit UI  
- [ ] Feature flag if risky (`ENABLE_*_CONNECTOR` optional)  

**Pricing:** Connectors available on **both** Starter and Pro (same stack breadth); Pro sells **structure**, not connectors.

---

## Feature flags (summary)

| Flag | Act | Default |
|------|-----|---------|
| `ENABLE_PORTFOLIOS` | 1 | `false` |
| Plan gate `professional` | 2 | Stripe + preferences |
| Per-connector flags | 4 | `false` until tested |

---

## Sequencing & rough effort (for discussion)

| Act | Rough size | Depends on |
|-----|------------|------------|
| Act 1 | Medium (1–2 weeks focused) | Schema decision (column vs JSON-only) |
| Act 2 | Small–medium (3–5 days) | Stripe Pro price live, copy approval |
| Act 3 | Ongoing | Existing backlog estimates |
| Act 4 | Medium each connector | API access, credential patterns |

**Suggested order:** Act 1 → Act 2 → pick 2 backlog items → Act 4 (Railway + Vercel first).

---

## Out of scope for entire chapter

- Consultancy tier, team seats, white-label share  
- Annual billing  
- Cross-workspace portfolios  
- Separate `portfolios` Postgres table (unless Act 1 proves insufficient)  
- PWA / native mobile  
- Persona field at signup (portfolios + Pro replace this for v1)  

---

## Discussion agenda (tomorrow)

1. Approve Act 1 data model: `portfolio_id` column vs settings-only?  
2. Trial behavior under three-plan model  
3. Pro naming and landing page layout (2 vs 3 columns)  
4. When to turn `ENABLE_PORTFOLIOS` on in prod (with Pro vs before Pro)  
5. Act 3 priority order — confirm top 2 after pricing ships  
6. Act 4 connector order: Railway + Vercel first?  
7. Grandfathering / migration for existing power users on Starter  

---

## References

- `services/portfolio_service.py` — rollup math (reuse with filtered assignments)  
- `services/stripe_billing_service.py` — `PLANS`, `CHECKOUT_PLANS`  
- `services/trial_service.py` — trial preferences  
- `docs/CURRENT-ARCHITECTURE.md` — Postgres-only, feature flags  
- [Backlog README](./README.md)
