# Phase 01 - Move config out of backend/

**Task ID:** CONSOL-P1-CONFIG-MOVE
**Phase:** 1 of 11
**Status:** PENDING — rename to `COMPLETED-phase-01-config-move.md` when human confirms testing passed.

## Why this phase exists

`backend/` currently mixes code and configuration. The configuration
(assignment JSON files and the .env file) is consumed by the live app;
the code in `backend/` is not. Moving config out is the first step
toward emptying `backend/` (Phase 10).

## How this phase fits

First behavior-neutral change. After this phase, the live app reads
its config from `config/assignments/` and `.env` (root) instead of
`backend/assignments/` and `backend/.env`. JSON responses unchanged.

---

## TASK PROMPT

### OBJECTIVE

Move assignment JSON configs out of `backend/` to a top-level `config/`
directory. Update the three call sites that reference the old path.
No behavior change. No service-class changes. No metric changes.

### PRECONDITION

- Phase 0 marked COMPLETED (`COMPLETED-phase-00-setup.md` exists).
- Branch: create `consolidation/phase-1-config` off current `main`.
- Tag `pre-consolidation` exists (`git tag --list pre-consolidation`).
- `_attic/` directory exists.
- `scripts/smoke.sh` exists and is executable.

### FILES YOU MAY MODIFY

- `routes/api_routes.py`
- `services/chatbot_service.py`
- `integrated_dashboard.py`

### FILES YOU MAY MOVE (via `git mv` only)

- `backend/assignments/` -> `config/assignments/`
- `backend/.env` -> `.env` (repo root) — ONLY if root `.env` does
  not already exist. If it does, STOP and report.

### FILES YOU MUST NOT MODIFY

- Anything under `services/` except `services/chatbot_service.py`.
- Anything under `backend/` except the moves above.
- Any `*.md` file.
- `railway.json`, `Procfile`, `.railwayignore`, `.gitignore`,
  `requirements.txt`.
- Any file under `frontend/`, `mcp_*`, `*.log`.

### STEPS

1. Run pre-flight checks per master rules.
2. `git mv backend/assignments config/assignments`
3. `git mv backend/.env .env` (only if root `.env` is absent).
4. In `routes/api_routes.py`, replace every literal string
   `"backend/assignments"` with `"config/assignments"`. Count
   occurrences first; report the count. Expected: 5.
5. In `services/chatbot_service.py`, replace the single literal
   `"backend/assignments"` with `"config/assignments"`. Expected: 1.
6. In `integrated_dashboard.py`, change:
       load_dotenv(os.path.join('backend', '.env'))
   to:
       load_dotenv()
7. Run post-flight per master rules.
8. Show diff to human. WAIT for approval.
9. Commit as a single commit with message:
   ```
   CONSOL-P1: move assignment configs to config/

   Relocates backend/assignments/*.json to top-level config/ so
   backend/ contains only code. Updates 6 call sites; no logic
   change. Endpoint shapes unchanged.

   Files: 5   Lines: +X/-X
   Refs: consolidation/MASTER-RULES.md, CONSOL-P1-CONFIG-MOVE
   ```

### DEFINITION OF DONE

- One commit on branch `consolidation/phase-1-config`.
- Smoke test against localhost: all PASS.
- `/api/assignments` returns the same JSON as before the change.
- Final report produced per master rules.

### DO NOT

- Touch any service class.
- Promote AssignmentService (that is Phase 2).
- Create any new directory other than `config/`.
- Move anything else from `backend/`.
- Modify `.env` contents.
- Begin Phase 2.

---

## When this phase is complete

After the human pushes and confirms Railway is green and the smoke
test passes against Railway, they will say "Phase 1 testing passed".
At that point, rename this file:

```
git mv consolidation/phase-01-config-move.md \
       consolidation/COMPLETED-phase-01-config-move.md
git commit -m "CONSOL-P1: mark phase 1 complete"
```

Do NOT rename the file yourself.

---

## EMBEDDED MASTER RULES

### ABSOLUTE PROHIBITIONS

1. Do NOT proceed past the phase named in your prompt.
2. Do NOT modify any file outside the FILES YOU MAY MODIFY whitelist.
3. Do NOT "improve" code style, formatting, imports, comments outside
   the explicit scope.
4. Do NOT add new dependencies to requirements.txt.
5. Do NOT modify .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .railwayignore, .gitignore (Phase 0 is the only phase
   that touched .railwayignore).
6. Do NOT run `git push`. Stop at `git commit`.
7. Do NOT create PRs or merge.
8. Do NOT run smoke against Railway. Localhost only.
9. Do NOT delete files. Use `_attic/`.
10. Do NOT add tooling outside phase scope.
11. Do NOT refactor anything not explicitly named.
12. Do NOT use feature flags for implementation swaps.
13. Do NOT mark COMPLETED yourself.

### PRE-FLIGHT

- `git status` clean.
- Branch matches PRECONDITION.
- Whitelist files exist; forbidden files absent.
- `_attic/` and `scripts/smoke.sh` exist.

### POST-FLIGHT

- `python -c "import integrated_dashboard"` succeeds.
- `python -m py_compile` succeeds for each modified file.
- Local app boots; smoke against localhost all PASS.
- Show diff; wait for approval.

### STOP CONDITIONS

Any pre/post-flight fail, smoke regression, out-of-whitelist diff,
scope expansion, unexpected API shape, or uncertainty -> STOP.

### REPORT FORMAT

1. Files changed + commit SHAs.
2. Out-of-scope findings (do not fix).
3. Smoke PASS/FAIL counts.
4. Next phase ID (do not start).
5. What the human verifies on Railway.
