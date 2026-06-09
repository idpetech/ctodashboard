# Deployment & CI/CD

**Last updated:** 2026-06-05

Three tiers:

| Tier | Git | Railway | CI |
|------|-----|---------|-----|
| **Local** | Uncommitted / feature work | — | `pytest tests/ -q` |
| **Staging** | `staging` branch | Staging service | Full test suite |
| **Production** | `master` branch | Production service | Smoke tests only |

---

## Git workflow

```
local work → commit → push staging → validate on Railway Staging
                              ↓
                    PR staging → master → Railway Production
```

- **Do not** push unreviewed CTOLens work directly to `master`.
- Production hotfixes: branch from `origin/master`, merge to `master`, push.

---

## GitHub Actions (CI)

Workflow: `.github/workflows/ci.yml`

| Event | Branch | Tests |
|-------|--------|-------|
| Push | `master` | `tests/test_smoke.py` |
| Push | `staging` | smoke + full `tests/` |
| Pull request | → `master` or `staging` | smoke + full `tests/` |

CI must pass before merging PRs to `master` (enable branch protection).

---

## Railway setup (one-time)

### 1. Production service (existing)

- Connect repo: `idpetech/ctodashboard`
- **Branch:** `master`
- **Root directory:** `/`
- **Start command:** from `Procfile` (`gunicorn ... integrated_dashboard:app`)
- **Postgres:** dedicated production database
- Enable **Wait for CI** (Settings → Deploy → wait for GitHub checks)

### 2. Staging service (new)

Duplicate the production service or add a new service in the same project:

| Setting | Value |
|---------|--------|
| Branch | `staging` |
| Service name | `cto-dashboard-staging` (example) |
| Postgres | **Separate** staging database (never share prod `DATABASE_URL`) |
| Wait for CI | On |

### 3. Environment variables

Copy production vars to staging, then adjust:

| Variable | Staging | Production |
|----------|---------|------------|
| `DATABASE_URL` | staging Postgres | prod Postgres |
| `ENABLE_CTOLENS_BRIEFING` | `true` | as needed |
| `ENABLE_STRIPE_BILLING` | test mode keys | live keys |
| `STRIPE_*` | Stripe test keys | Stripe live keys |

Run DB init once per new Postgres:

```bash
railway link   # select staging service
railway run python railway_db_init.py
```

---

## Local commands

```bash
source venv/bin/activate
python integrated_dashboard.py          # port 8520
pytest tests/test_smoke.py -q           # prod baseline
pytest tests/ -q                        # full suite (CTOLens)
```

---

## Branch bootstrap

If `staging` does not exist on GitHub yet:

```bash
git checkout -b staging
git push -u origin staging
```

Railway staging service should track this branch.

---

## Rollback

**Production:** Railway → Deployments → redeploy previous successful deployment.

**Git:** revert commit on `master`, push, CI runs smoke tests, Railway redeploys.

---

## Related docs

- `docs/backlog/CTOLENS-METRICS-ENRICHMENT-PLAN.md` — scheduled metrics enrichment (future)
- `docs/CURRENT-ARCHITECTURE.md` — application architecture
