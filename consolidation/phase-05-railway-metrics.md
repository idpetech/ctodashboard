# Phase 05 - Add RailwayMetrics (purely additive)

**Task ID:** CONSOL-P5-RAILWAY-METRICS
**Phase:** 5 of 11
**Status:** PENDING — rename to `COMPLETED-phase-05-railway-metrics.md` when human confirms testing passed.

## Why this phase exists

`backend/metrics_service.py::RailwayMetrics` provides Railway
deployment metrics with a graceful fallback when Railway's public
API is unavailable (currently it returns 404 everywhere). The live
app does not have this class wired in at all. Adding it requires
no existing endpoint changes — purely additive.

## How this phase fits

Lowest-risk implementation addition. Two commits.

---

## TASK PROMPT

### OBJECTIVE

Add Railway deployment metrics to the live app. Lift `RailwayMetrics`
from `backend/metrics_service.py` into a new file
`services/embedded/railway_metrics.py`. Wire into the two aggregator
endpoints. Purely additive — no existing behavior changes.

### PRECONDITION

- Phase 4 COMPLETED. Railway green.
- Branch: `consolidation/phase-5-railway-metrics` off `main`.

### FILES YOU MAY MODIFY

- `services/embedded/railway_metrics.py` (new)
- `routes/api_routes.py`

### FILES YOU MUST NOT MODIFY

- Everything else.

### STEPS

**Commit 1 — create the new file**
- Create `services/embedded/railway_metrics.py` containing only the
  `RailwayMetrics` class lifted verbatim from
  `backend/metrics_service.py` (lines ~615–765 in current main).
- Ensure all imports the class uses are present (`aiohttp`, `ssl`,
  `asyncio`, `requests`, `os`).
- Do NOT import it from anywhere yet.
- Post-flight. Commit.

**Commit 2 — wire into endpoints**
- In `routes/api_routes.py`, add:
      from services.embedded.railway_metrics import RailwayMetrics
      railway_metrics = RailwayMetrics()
- In `/api/all-metrics/<id>` and `/api/assignments/<id>/metrics`,
  add an `if assignment.get('metrics_config', {}).get('railway', {})
  .get('enabled')` branch that calls `railway_metrics`. Because the
  call is async, run it via `asyncio.run()` inside a `try/except`
  that returns the error dict on failure. Match the pattern of
  other branches in the same function.
- Run smoke. Curl `/api/all-metrics/ideptech` and verify a `railway`
  key is now present with `status` field (either `"success"` or
  `"api_unavailable"` — both acceptable; do NOT treat
  `api_unavailable` as a failure).
- Post-flight. Commit.

### DEFINITION OF DONE

- 2 commits.
- `/api/all-metrics/ideptech` response now has a `railway` key.
- All existing keys unchanged.
- Smoke: all PASS.

### DO NOT

- Touch `backend/metrics_service.py`.
- Try to "fix" Railway's API or change endpoints. The fallback
  path is the expected behavior.
- Add caching or polling.
- Begin Phase 6.

---

## When this phase is complete

Human says "Phase 5 testing passed" -> rename:
```
git mv consolidation/phase-05-railway-metrics.md \
       consolidation/COMPLETED-phase-05-railway-metrics.md
git commit -m "CONSOL-P5: mark phase 5 complete"
```

---

## EMBEDDED MASTER RULES

1. Stop after this phase.
2. Whitelist-only.
3. No style changes outside scope.
4. No new deps.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .railwayignore, .gitignore.
6. No `git push`. No PRs. No merges.
7. Smoke localhost only.
8. No deletions; use `_attic/`.
9. No tooling outside scope.
10. No refactoring outside scope.
11. No feature flags.
12. Do NOT mark COMPLETED yourself.

PRE-FLIGHT: clean status, correct branch, whitelist exists.
POST-FLIGHT: import OK, py_compile OK, smoke all PASS, diff approved.
STOP CONDITIONS: any check fail, smoke regression, out-of-whitelist
diff, scope expansion, unexpected API shape, uncertainty.
REPORT: files+SHAs, out-of-scope findings, smoke counts, next phase
ID, Railway verification notes.
