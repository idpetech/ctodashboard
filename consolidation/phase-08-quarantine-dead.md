# Phase 08 - Quarantine alternate Flask apps and scaffolding

**Task ID:** CONSOL-P8-QUARANTINE-DEAD
**Phase:** 8 of 11
**Status:** PENDING — rename to `COMPLETED-phase-08-quarantine-dead.md` when human confirms testing passed.

## Why this phase exists

The repo root contains nine alternate Flask app entrypoints
(`app.py`, `simple_app.py`, `working_app.py`, `minimal_app.py`,
`dashboard_app.py`, `final_dashboard.py`, `working_dashboard.py`,
`real_aws_dashboard.py`, `integrated_dashboard.py.backup`), four
scratch scaffolding files (`service_foundation.py`,
`service_layer_addition.py`, `service_endpoints_addition.py`,
`feature_flags_addition.py`), and seven log files. None of these
are imported by the live app. They exist only to confuse human
readers and AI agents looking at the repo.

## How this phase fits

Largest single-phase reduction in repo confusion. Lowest deployment
risk in the entire plan — none of these files run in production.

---

## TASK PROMPT

### OBJECTIVE

Move the nine alternate Flask app entrypoints, the four scratch
scaffolding files, and the seven log files into `_attic/`. Add
`*.log` to `.gitignore`.

### PRECONDITION

- Phase 7 COMPLETED. Railway green.
- Branch: `consolidation/phase-8-quarantine-dead` off `main`.
- Verify none of the listed files are imported by the live app:
  ```
  for f in app simple_app working_app minimal_app dashboard_app \
           final_dashboard working_dashboard real_aws_dashboard \
           service_foundation service_layer_addition \
           service_endpoints_addition feature_flags_addition; do
    grep -rn "import $f\|from $f" --include="*.py" \
      --exclude-dir=_attic --exclude-dir=venv --exclude-dir=backend
  done
  ```
  Expected: zero output. If any match, STOP and report.

### FILES YOU MAY MOVE (`git mv` into `_attic/` subfolders)

  `_attic/alternate_apps/`:
  - `app.py`
  - `simple_app.py`
  - `working_app.py`
  - `minimal_app.py`
  - `dashboard_app.py`
  - `final_dashboard.py`
  - `working_dashboard.py`
  - `real_aws_dashboard.py`
  - `integrated_dashboard.py.backup`

  `_attic/scaffolding/`:
  - `service_foundation.py`
  - `service_layer_addition.py`
  - `service_endpoints_addition.py`
  - `feature_flags_addition.py`

  `_attic/logs/`:
  - `app.log`, `app_ai.log`, `app_gpt4.log`, `app_new.log`,
    `app_stream.log`, `flask.log`, `flask_simple.log`

### FILES YOU MAY MODIFY

- `.gitignore` (one line addition: `*.log`)

### FILES YOU MUST NOT MODIFY

- Everything else.

### STEPS

**Commit 1 — alternate apps**
- `mkdir -p _attic/alternate_apps`
- `git mv` the 9 files listed.
- Post-flight. Smoke. Commit.

**Commit 2 — scaffolding**
- `mkdir -p _attic/scaffolding`
- `git mv` the 4 files listed.
- Post-flight. Smoke. Commit.

**Commit 3 — logs + gitignore**
- `mkdir -p _attic/logs`
- `git mv` the 7 log files.
- Append `*.log` to `.gitignore` (single line).
- Post-flight. Commit.

### DEFINITION OF DONE

- 3 commits.
- Repo root has only one Flask app: `integrated_dashboard.py`.
- Smoke: all PASS.
- `ls *.py | wc -l` in repo root drops by 13.

### DO NOT

- Touch `backend/` in this phase (Phase 10 empties `backend/`,
  after Phase 9 MCP revival).
- Delete anything. Only move.
- Begin Phase 9.

---

## When this phase is complete

Human says "Phase 8 testing passed" -> rename:
```
git mv consolidation/phase-08-quarantine-dead.md \
       consolidation/COMPLETED-phase-08-quarantine-dead.md
git commit -m "CONSOL-P8: mark phase 8 complete"
```

---

## EMBEDDED MASTER RULES

1. Stop after this phase.
2. Whitelist-only (note: `.gitignore` is explicitly authorized here
   for adding `*.log` — nothing else).
3. No style changes outside scope.
4. No new deps.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .railwayignore.
6. No `git push`. No PRs. No merges.
7. Smoke localhost only.
8. No deletions; use `_attic/`.
9. No tooling outside scope.
10. No refactoring outside scope.
11. No feature flags.
12. Do NOT mark COMPLETED yourself.

PRE-FLIGHT: clean status, correct branch, zero imports of the
named files outside `_attic/`, `venv/`, `backend/`.
POST-FLIGHT: import OK, smoke all PASS, diff approved.
STOP CONDITIONS: any check fail, smoke regression, out-of-whitelist
diff, any of the named files actually imported somewhere, uncertainty.
REPORT: files+SHAs, out-of-scope findings, smoke counts, next phase
ID, Railway verification notes.
