# Phase 07 - Kill the React frontend

**Task ID:** CONSOL-P7-KILL-REACT
**Phase:** 7 of 11
**Status:** PENDING — rename to `COMPLETED-phase-07-kill-react.md` when human confirms testing passed.

## Why this phase exists

The Jinja template at `templates/dashboard.html` is canonical — it
is what Railway serves to users at `/`. The React SPA in `frontend/`
was an earlier attempt that is no longer wired into the live app.
Keeping both means every UI change has two places to update; users
get confused; readers of the repo get confused. The user has
explicitly decided: Jinja stays, React is retired.

This phase is quarantine, not deletion. The React code goes to
`_attic/` (Phase 11 deletes it).

## How this phase fits

First user-visible "what is this repo" cleanup. Removes ~25,000 lines
of dependencies (`frontend/node_modules` excluded from git, but
`frontend/src`, `frontend/dist`, etc. all go).

---

## TASK PROMPT

### OBJECTIVE

Quarantine the React SPA so it stops shipping in the repo. The
Railway deploy is unaffected — Railway never served the SPA.

### PRECONDITION

- Phase 6 COMPLETED. Railway green.
- Branch: `consolidation/phase-7-kill-react` off `main`.
- Verify the Jinja UI is what users see by curling Railway root
  and confirming it returns HTML containing the dashboard title
  string (from `templates/dashboard.html`). If it doesn't, STOP.

### FILES YOU MAY MODIFY

- `integrated_dashboard.py`
- `.railwayignore` (only to clean stale frontend references; do
  not add new entries)

### FILES YOU MAY MOVE

- `frontend/` -> `_attic/frontend/`
- `vercel.json` -> `_attic/vercel.json`
- `render.yaml` -> `_attic/render.yaml`
- `render-simple.yaml` -> `_attic/render-simple.yaml`
- `api/` -> `_attic/api/`

### FILES YOU MUST NOT MODIFY

- `routes/api_routes.py`
- `templates/dashboard.html`
- `services/*`
- `railway.json`, `Procfile`

### STEPS

**Commit 1 — neutralize the Flask static folder**
- In `integrated_dashboard.py`, change the Flask construction from:
      app = Flask(__name__,
                  static_folder=..., static_url_path='',
                  template_folder=...)
  to:
      app = Flask(__name__, template_folder='templates')
- Post-flight. Smoke. Commit.

**Commit 2 — quarantine the frontend**
- `git mv frontend _attic/frontend`
- Post-flight. Commit.

**Commit 3 — quarantine other-platform deploy configs**
- `git mv vercel.json _attic/`
- `git mv render.yaml _attic/`
- `git mv render-simple.yaml _attic/`
- `git mv api _attic/api`
- In `.railwayignore`, remove now-stale entries that referenced
  `frontend/`, `node_modules/`, etc., if any. Do not add new
  entries.
- Post-flight. Commit.

### DEFINITION OF DONE

- 3 commits.
- Repo no longer contains a top-level `frontend/`, `vercel.json`,
  `render.yaml`, `render-simple.yaml`, or `api/`.
- Railway root URL still returns the Jinja dashboard.
- Smoke: all PASS.

### DO NOT

- Delete anything outright. Use `_attic/`.
- Touch `templates/dashboard.html`.
- Touch the chatbot code paths.
- Modify `package.json` files anywhere.
- Begin Phase 8.

---

## When this phase is complete

Human says "Phase 7 testing passed" -> rename:
```
git mv consolidation/phase-07-kill-react.md \
       consolidation/COMPLETED-phase-07-kill-react.md
git commit -m "CONSOL-P7: mark phase 7 complete"
```

---

## EMBEDDED MASTER RULES

1. Stop after this phase.
2. Whitelist-only (note: `.railwayignore` is explicitly authorized
   here for cleanup of stale entries only — no new entries).
3. No style changes outside scope.
4. No new deps.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .gitignore.
6. No `git push`. No PRs. No merges.
7. Smoke localhost only.
8. No deletions; use `_attic/`.
9. No tooling outside scope.
10. No refactoring outside scope.
11. No feature flags.
12. Do NOT mark COMPLETED yourself.

PRE-FLIGHT: clean status, correct branch, Railway root returns
Jinja HTML.
POST-FLIGHT: import OK, smoke all PASS, diff approved.
STOP CONDITIONS: any check fail, smoke regression, out-of-whitelist
diff, scope expansion, uncertainty.
REPORT: files+SHAs, out-of-scope findings, smoke counts, next phase
ID, Railway verification notes (especially: confirm Jinja UI still
renders correctly on Railway after deploy).
