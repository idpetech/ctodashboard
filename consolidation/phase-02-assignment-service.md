# Phase 02 - Promote AssignmentService

**Task ID:** CONSOL-P2-ASSIGNMENT-SERVICE
**Phase:** 2 of 11
**Status:** PENDING — rename to `COMPLETED-phase-02-assignment-service.md` when human confirms testing passed.

## Why this phase exists

`routes/api_routes.py` currently reads assignment JSON files inline
with `os.listdir`+`json.load` in five different functions. The richer
`backend/assignment_service.py` (which supports create/update/archive)
is not used by the live app. Promoting it to `services/` and routing
the live app through it eliminates duplication and enables future
service-config CRUD without further refactoring.

## How this phase fits

Second behavior-neutral change. Implementation swap under unchanged
endpoint contracts.

---

## TASK PROMPT

### OBJECTIVE

Move `backend/assignment_service.py` to `services/assignment_service.py`.
Replace the inline `os.listdir`/`json.load` blocks in
`routes/api_routes.py` with calls to the service. Five endpoints,
five separate commits.

### PRECONDITION

- Phase 1 COMPLETED. Railway green.
- Branch: create `consolidation/phase-2-assignment-service` off `main`.
- `config/assignments/ideptech.json` exists.
- `backend/assignment_service.py` exists.

### FILES YOU MAY MODIFY

- `routes/api_routes.py`
- `services/assignment_service.py` (after move)

### FILES YOU MAY MOVE

- `backend/assignment_service.py` -> `services/assignment_service.py`

### FILES YOU MUST NOT MODIFY

- `backend/metrics_service.py`
- `backend/chatbot_service.py`
- `backend/main.py`
- Any `services/embedded/*` file.
- Any `*.md`, `railway.json`, `Procfile`, `requirements.txt`.

### STEPS

**Commit 1 — move the file**
- `git mv backend/assignment_service.py services/assignment_service.py`
- In the moved file, change the default `assignments_dir` to
  `config/assignments` (one line). Do not change any other line.
- Post-flight. Show diff. Commit.

**Commit 2 — add import, instantiate, do NOT use yet**
- In `routes/api_routes.py`, add:
      from services.assignment_service import AssignmentService
      assignment_service = AssignmentService()
  near the existing service instantiations.
- Post-flight: confirm app still boots and smoke is unchanged.
- Show diff. Commit.

**Commits 3–7 — one endpoint per commit**
In this exact order, swap inline assignment-loading logic for
service calls. After each commit, run smoke locally.

  3. `/api/assignments`
  4. `/api/github-metrics/<assignment_id>`
  5. `/api/jira-metrics/<assignment_id>`
  6. `/api/all-metrics/<assignment_id>`
  7. `/api/assignments/<assignment_id>/metrics`

For each: replace the `os.path.exists` + `open` + `json.load` block
with either `assignment_service.get_all_assignments()` (for the list
endpoint) or `assignment_service.get_assignment(assignment_id)`
(for single). Keep the 404 / "not enabled" branches as-is.

Do not change response shapes. Do not change error messages.

Commit message template:
```
CONSOL-P2: route /api/<endpoint> through AssignmentService

<one-line WHY>

Files: 1   Lines: +X/-Y
Refs: consolidation/MASTER-RULES.md, CONSOL-P2-ASSIGNMENT-SERVICE
```

### DEFINITION OF DONE

- 7 commits on the branch.
- All 5 swapped endpoints return byte-identical JSON for the seed
  assignments (`ideptech`, `il`) as before. Verify by diffing
  `curl localhost:3001/api/assignments` against the baseline in
  `_attic/contracts-baseline/`.
- Smoke: all PASS.
- Final report lists the 7 commit SHAs.

### DO NOT

- Add CRUD endpoints. `AssignmentService` has them; do not expose
  them yet. That belongs to a later, separate piece of work.
- Touch metrics services.
- Refactor anything in `routes/api_routes.py` beyond the 5 specific
  blocks named above.
- Begin Phase 3.

---

## When this phase is complete

Human says "Phase 2 testing passed" -> rename:
```
git mv consolidation/phase-02-assignment-service.md \
       consolidation/COMPLETED-phase-02-assignment-service.md
git commit -m "CONSOL-P2: mark phase 2 complete"
```

---

## EMBEDDED MASTER RULES

### ABSOLUTE PROHIBITIONS

1. Stop after this phase.
2. Whitelist-only file modifications.
3. No style/formatting/comment changes outside scope.
4. No new dependencies.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .railwayignore, .gitignore.
6. No `git push`.
7. No PRs or merges.
8. Smoke against localhost only.
9. No deletions; use `_attic/`.
10. No new tooling outside scope.
11. No bug-fixing outside scope.
12. No feature flags for implementation swaps.
13. Do NOT mark COMPLETED yourself.

### PRE-FLIGHT

- `git status` clean.
- Correct branch.
- Whitelist files exist.
- `_attic/` and `scripts/smoke.sh` exist.

### POST-FLIGHT

- App imports cleanly.
- Modified files py_compile clean.
- Local smoke all PASS.
- Show diff; wait for approval before commit.

### STOP CONDITIONS

Any check fail, smoke regression, out-of-whitelist diff, scope
expansion, unexpected API shape, or uncertainty -> STOP.

### REPORT FORMAT

1. Files changed + commit SHAs.
2. Out-of-scope findings.
3. Smoke PASS/FAIL.
4. Next phase ID.
5. What human verifies on Railway.
