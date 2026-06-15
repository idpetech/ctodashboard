# CTOLens — Product Phases

**Source of truth** for CTOLens go-to-market and product maturity milestones.  
Read this before starting homepage, onboarding, or conversion work.

---

## Phase 1 — Honest landing & signup funnel ✅ COMPLETE

**Status:** Complete  
**Completed:** 2026-06-14  
**Git:** `5b203cb` on `master` / `staging` (deployed Railway)  
**Tag:** `ctolens/phase-1-homepage-complete`

### Goal

Ship a marketing homepage that reflects what CTOLens **actually does today**, with one clear conversion path: **Start Free Assessment** → `/dashboard?signup=1`.

### Delivered

| Area | Outcome |
|------|---------|
| **Hero** | Eyebrow, "5 minutes" headline, trust chips, Overview mock/screenshot slot, purple gradient, responsive layout |
| **Navigation** | Sticky header, mobile menu, Product / How it Works / Sample Report / Pricing / Resources (no fake Security section) |
| **Integrations bar** | GitHub, AWS, Jira, OpenAI, Railway only — no "+20 more" |
| **Pain section** | Founder/CTO pain cards; resolution copy tied to Overview briefing (not "continuous assessment") |
| **Features** | Five honest capability cards (security signals, cost, engineering health, insights, reports) |
| **Sample Report** | Shared `overview_dashboard_mock` — matches real Overview layout; illustrative disclaimer |
| **Pricing** | Free trial + Starter + Professional; unified CTAs; no unverifiable savings claims |
| **Final CTA** | Scroll-end band with "No credit card required" |
| **Honesty pass** | Removed fake stars/avatars; softened hero subhead; synced `homepage_routes.py` fallback |
| **Content system** | `config/homepage_content.json` + `templates/homepage.html` + `services/homepage_service.py` |

### Explicitly out of scope (Phase 1)

- New connectors (Slack, Datadog, Linear, etc.)
- Security/compliance product page
- Interactive CVE/cost tabbed "sample report"
- Pricing/checkout redesign beyond copy
- Hero photograph from production (slot exists: `hero.screenshot_url`)

### Verification checklist (done at ship)

- [x] All primary CTAs → **Start Free Assessment** / `/dashboard?signup=1`
- [x] No unverified social proof
- [x] Integrations list matches wired connectors
- [x] Local `app.test_client()` render passes
- [x] Pushed to `staging` and `master`

### Key files

- `config/homepage_content.json`
- `templates/homepage.html`
- `routes/homepage_routes.py`
- `docs/HOMEPAGE-SETUP.md`

---

## Phase 2 — Notch higher (NEXT)

**Status:** Not started  
**Theme:** Turn honest positioning into **measurable conversion and deeper product proof** — without overpromising features that are not shipped.

Direction (pick order by impact; not all required):

1. **Conversion & learning**
   - Enable `ENABLE_PRODUCT_ANALYTICS` in staging; track homepage → signup → first briefing
   - Funnel events: CTA clicks, signup start, first assignment, first refresh
   - See `docs/backlog/PRODUCT-ANALYTICS-PLAN.md`

2. **Product proof on the page**
   - Replace hero mock with real `hero.screenshot_url` from admin workspace
   - Optional short screen recording or before/after for Sample Report section

3. **Signup → first value**
   - Reduce time from signup to first Overview health score (onboarding nudges, default assignment template)
   - Align in-app empty states with homepage promises

4. **Briefing & metrics depth**
   - Continue metrics enrichment and Jira insight accuracy (product quality backs marketing)
   - See `docs/backlog/CTOLENS-METRICS-ENRICHMENT-PLAN.md`, `CTOLENS-JIRA-INSIGHTS-FIX-PLAN.md`

5. **Scale & reliability** (when traffic grows)
   - Scheduled enrichment caps — `docs/backlog/CTOLENS-SCHEDULED-ENRICHMENT-SCALE-PLAN.md`

### Phase 2 success criteria (draft)

- Homepage CTA → signup conversion measurable in analytics
- Median time to first real Overview briefing under 15 minutes for a new workspace
- Zero marketing claims on `/` that are not true in the dashboard for a standard connector set
- Staging validates changes before `master` / production

---

## How to mark a phase complete

1. Update this file (status, date, git SHA, checklist).
2. Add a row to `docs/CHECKPOINTS.md`.
3. Tag: `git tag -a ctolens/phase-N-<short-name> -m "..." <sha>`
4. Push branch + tag when deploying.

---

## Related docs

| Doc | Role |
|-----|------|
| [HOMEPAGE-SETUP.md](./HOMEPAGE-SETUP.md) | How to edit homepage JSON and admin UI |
| [CURRENT-ARCHITECTURE.md](./CURRENT-ARCHITECTURE.md) | Runtime architecture (Flask, Postgres, briefing) |
| [backlog/README.md](./backlog/README.md) | Execution backlog index |
