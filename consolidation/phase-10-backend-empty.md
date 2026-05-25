# Phase 10 - Empty backend/ and slim docs

**Task ID:** CONSOL-P10-BACKEND-EMPTY
**Phase:** 10 of 11
**Status:** PENDING — rename to `COMPLETED-phase-10-backend-empty.md` when human confirms testing passed.

## Why this phase exists

After Phases 1–9, nothing imports from `backend/`. The directory holds
only the now-superseded original service stack (`main.py`,
`metrics_service.py`, `chatbot_service.py`, `simple_server.py`, etc.).
Quarantining `backend/` removes the last source of "which file is
canonical?" confusion. The doc slim is optional but reduces the
cognitive load of repo navigation.

## How this phase fits

Penultimate phase. No code in `backend/` is referenced anywhere live.

---

## TASK PROMPT

### OBJECTIVE

Now that nothing imports from `backend/`, quarantine the remaining
files in `backend/` to `_attic/`. Optionally also collapse the
markdown documentation proliferation.

### PRECONDITION

- Phase 9 COMPLETED. Railway green. MCP confirmed working locally.
- Branch: `consolidation/phase-10-backend-empty` off `main`.
- Run:
  ```
  grep -rn "from backend\|backend\." --include="*.py" \
    --exclude-dir=_attic --exclude-dir=venv --exclude-dir=backend
  grep -rn "from assignment_service\|from metrics_service\|\
from chatbot_service" --include="*.py" \
    --exclude-dir=_attic --exclude-dir=venv --exclude-dir=backend
  ```
  Expected: zero matches outside `backend/` itself. If non-zero,
  STOP.

### FILES YOU MAY MOVE

- `backend/main.py`             -> `_attic/backend/main.py`
- `backend/simple_server.py`    -> `_attic/backend/simple_server.py`
- `backend/test_server.py`      -> `_attic/backend/test_server.py`
- `backend/test_main.py`        -> `_attic/backend/test_main.py`
- `backend/debug_github.py`     -> `_attic/backend/debug_github.py`
- `backend/metrics_service.py`  -> `_attic/backend/metrics_service.py`
- `backend/chatbot_service.py`  -> `_attic/backend/chatbot_service.py`
- `backend/requirements.txt`    -> `_attic/backend/requirements.txt`
- `backend/activate.sh`         -> `_attic/backend/activate.sh`
- `backend/repo_generation_prompt copy.txt` -> `_attic/backend/`
- `backend/.github/`            -> `_attic/backend/.github/`

### FILES YOU MAY DELETE OUTRIGHT

(These are caches/virtualenvs, not source.)

- `backend/.pytest_cache/`
- `backend/.venv/`
- `backend/__pycache__/`

After moves, `backend/` should be empty:
```
rmdir backend
```

### FILES YOU MAY MODIFY

- None for the move work.

### OPTIONAL: doc slim (separate commits, can be deferred)

- Move all root `*.md` EXCEPT these to `_attic/docs/`:
    - `README.md`
    - `CHANGELOG.md`
    - `LICENSE` (if present)
- Do NOT create new docs in this phase. `ARCHITECTURE.md`,
  `ROADMAP.md`, `DEPLOYMENT.md`, `CONTRIBUTING.md` authorship is
  out of scope here — belongs to a documentation phase the human
  owns separately.

### FILES YOU MUST NOT MODIFY

- `.cursorrules` — even though it's stale, the human owns rewriting it.
- Anything under `services/`, `routes/`, `templates/`, `config/`,
  `_attic/`.

### STEPS

**Commit 1 — move backend source files**
- `mkdir -p _attic/backend`
- `git mv` each file listed.
- Post-flight. Smoke. Commit.

**Commit 2 — clean caches and dirs**
- `rm -rf backend/.pytest_cache backend/.venv backend/__pycache__`
- `git mv backend/.github _attic/backend/.github` (if it exists)
- `rmdir backend` (only if now empty; if not, STOP and list contents)
- Post-flight. Smoke. Commit.

**Commit 3 (optional, can defer to a later session): doc move**
- `mkdir -p _attic/docs`
- `git mv` all `*.md` at repo root EXCEPT `README.md`,
  `CHANGELOG.md`, `LICENSE` — into `_attic/docs/`.
- Post-flight. Commit.

### DEFINITION OF DONE

- 2 or 3 commits.
- `backend/` directory no longer exists at repo root.
- Smoke: all PASS.
- `mcp_server.py` still `py_compile`-clean.

### DO NOT

- Rewrite `.cursorrules`.
- Author new README/ARCHITECTURE content.
- Touch `frontend/`, `config/`, `services/`, `routes/`.
- Begin Phase 11.

---

## When this phase is complete

Human says "Phase 10 testing passed" -> rename:
```
git mv consolidation/phase-10-backend-empty.md \
       consolidation/COMPLETED-phase-10-backend-empty.md
git commit -m "CONSOL-P10: mark phase 10 complete"
```

---

## EMBEDDED MASTER RULES

1. Stop after this phase.
2. Whitelist-only (note: this phase is one of two phases authorized
   to delete files — but only caches/virtualenvs, not source).
3. No style changes outside scope.
4. No new deps.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .railwayignore, .gitignore.
6. No `git push`. No PRs. No merges.
7. Smoke localhost only.
8. Source-file deletions still forbidden; use `_attic/`. Only
   caches/`.venv`/`__pycache__`/`.pytest_cache` may be `rm -rf`-ed.
9. No tooling outside scope.
10. No refactoring outside scope.
11. No feature flags.
12. Do NOT mark COMPLETED yourself.

PRE-FLIGHT: clean status, correct branch, zero imports referencing
`backend/` outside `backend/` or `_attic/`.
POST-FLIGHT: import OK, smoke all PASS, `py_compile mcp_server.py`
clean.
STOP CONDITIONS: any check fail, smoke regression, out-of-whitelist
diff, any `backend/` import discovered outside `backend/`,
uncertainty.
REPORT: files+SHAs, out-of-scope findings, smoke counts, next phase
ID (Phase 11 — but it must wait >=14 days), Railway verification.
