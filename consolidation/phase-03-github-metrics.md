# Phase 03 - Promote GitHubMetrics (fixes a live bug)

**Task ID:** CONSOL-P3-GITHUB-METRICS
**Phase:** 3 of 11
**Status:** PENDING — rename to `COMPLETED-phase-03-github-metrics.md` when human confirms testing passed.

## Why this phase exists

`services/embedded/github_metrics.py` has a live bug:
`datetime.now() - datetime.timedelta(days=30)` — `datetime.timedelta`
is not a valid attribute (only `timedelta`, and `timedelta` is not
imported). This raises `AttributeError`, which the outer `except`
catches, so `commits_last_30_days` is silently 0 or error in
production.

`backend/metrics_service.py::GitHubMetrics` is correct and also
returns `total_prs`. Promoting it fixes the bug and adds data.

## How this phase fits

Single-file change. Highest-payoff phase — fixes a real production
data quality issue.

---

## TASK PROMPT

### OBJECTIVE

Replace the `get_repo_metrics` implementation in
`services/embedded/github_metrics.py` with the corrected version
from `backend/metrics_service.py::GitHubMetrics`. The class name
(`EmbeddedGitHubMetrics`) and `get_metrics(config)` adapter
signature MUST be preserved so `routes/api_routes.py` needs no
changes.

### PRECONDITION

- Phase 2 COMPLETED. Railway green.
- Branch: `consolidation/phase-3-github-metrics` off `main`.
- `backend/metrics_service.py` still exists (it will until Phase 10).

### FILES YOU MAY MODIFY

- `services/embedded/github_metrics.py`

### FILES YOU MUST NOT MODIFY

- Anything else. This is a single-file change.

### STEPS

**Commit 1 — add corrected method alongside the broken one**
- Add `from datetime import timedelta` to the imports.
- Add a new method `_get_repo_metrics_v2(org, repo, headers)` that
  contains the corrected logic from
  `backend/metrics_service.py::GitHubMetrics.get_repo_metrics`,
  adapted to use the existing instance attributes (`self.token`,
  `self.base_url`). It should return per-repo dicts including
  `total_prs` and corrected `commits_last_30_days`.
- Do NOT remove or modify the existing `get_repo_metrics` yet.
- Post-flight. Commit.

**Commit 2 — switch get_metrics to use _v2**
- Modify `get_repo_metrics` to delegate to `_get_repo_metrics_v2`.
- Run smoke. Verify `commits_last_30_days` is now an integer (not
  an error) for at least one active repo. (If both ideptech repos
  have zero commits in 30d, fall back to verifying `total_prs` key
  is present.)
- Post-flight. Commit.

**Commit 3 — inline and remove dead code**
- Move the `_v2` body into `get_repo_metrics`. Remove `_v2`. Remove
  any `import datetime` line no longer needed.
- Post-flight. Commit.

Commit messages: `CONSOL-P3: <imperative summary>` per master rules.

### DEFINITION OF DONE

- 3 commits on the branch.
- `/api/github-metrics/ideptech` returns a payload where
  `commits_last_30_days` is an integer (not an error string) and
  the `total_prs` key is present.
- Smoke: all PASS.

### DO NOT

- Change the class name (`EmbeddedGitHubMetrics`).
- Change the `get_metrics` signature.
- Touch `backend/metrics_service.py`.
- Add caching, retries, or rate-limit handling.
- Begin Phase 4.

---

## When this phase is complete

Human says "Phase 3 testing passed" -> rename:
```
git mv consolidation/phase-03-github-metrics.md \
       consolidation/COMPLETED-phase-03-github-metrics.md
git commit -m "CONSOL-P3: mark phase 3 complete"
```

---

## EMBEDDED MASTER RULES

### ABSOLUTE PROHIBITIONS

1. Stop after this phase.
2. Whitelist-only file modifications.
3. No style/formatting changes outside scope.
4. No new dependencies.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .railwayignore, .gitignore.
6. No `git push`.
7. No PRs or merges.
8. Smoke localhost only.
9. No deletions; use `_attic/`.
10. No tooling outside scope.
11. No bug-fixing outside scope (this phase IS the bug fix; it is
    in scope).
12. No feature flags.
13. Do NOT mark COMPLETED yourself.

### PRE-FLIGHT

- `git status` clean. Correct branch. Whitelist files exist.

### POST-FLIGHT

- App imports cleanly. py_compile clean. Smoke all PASS.
- Show diff; wait for approval.

### STOP CONDITIONS

Any check fail, smoke regression, out-of-whitelist diff, scope
expansion, unexpected API shape, or uncertainty -> STOP.

### REPORT FORMAT

1. Files changed + commit SHAs.
2. Out-of-scope findings.
3. Smoke PASS/FAIL.
4. Next phase ID.
5. What human verifies on Railway (especially: confirm
   `commits_last_30_days` is now non-zero in real responses).
