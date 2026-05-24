# Phase 00 - Day 0 Setup

**Task ID:** CONSOL-P0-SETUP
**Phase:** 0 of 11 (foundation; run once)
**Status:** PENDING — rename to `COMPLETED-phase-00-setup.md` when human confirms testing passed.

## Why this phase exists

The consolidation depends on three pieces of infrastructure: a baseline
git tag for nuclear restore, an `_attic/` quarantine zone, and a smoke
test script. This phase creates all three. Nothing else.

After this phase the repo can run any later phase. Before this phase
no later phase is safe.

---

## TASK PROMPT

### OBJECTIVE

Create the minimal infrastructure needed for the consolidation:
1. A `pre-consolidation` git tag on current `main`.
2. An `_attic/` directory with a README.
3. `_attic/` added to `.railwayignore`.
4. `scripts/smoke.sh` (executable) that hits the live endpoints.
5. A baseline snapshot of API contract keys for drift detection.

This phase introduces no behavior change. Railway deployment is
untouched. The Flask app does not change.

### PRECONDITION

- Branch: you must be on `main` (or whatever the user's primary
  branch is — verify with `git rev-parse --abbrev-ref HEAD`).
- Working tree clean (`git status` shows no changes).
- The Railway URL is reachable. If unknown, ask the human for it
  and the user must provide it before you proceed.

### FILES YOU MAY CREATE

- `_attic/README.md`
- `scripts/smoke.sh`
- `scripts/baseline_contracts.sh` (optional helper)
- `_attic/contracts-baseline/*.txt` (snapshot files)

### FILES YOU MAY MODIFY

- `.railwayignore` — append one line: `_attic/`

### FILES YOU MUST NOT MODIFY

- Everything else.

### STEPS

1. **Snapshot:** create the rollback tag.
   ```
   git tag pre-consolidation
   ```
   Do NOT push the tag. Tell the human to push it manually:
       git push origin pre-consolidation

2. **Create `_attic/`:**
   ```
   mkdir -p _attic
   ```
   Write `_attic/README.md` with content:
   ```
   # _attic

   Files quarantined for retirement. Nothing here is imported by
   the live application. Phase 11 of the consolidation deletes this
   directory entirely after >=14 days of stable Railway operation.

   Do not edit files here. Do not move files out of here without
   explicit human instruction.
   ```

3. **Update `.railwayignore`:**
   Append the line `_attic/` (with trailing newline). Do not modify
   any other line. Verify with `git diff .railwayignore`.

4. **Create `scripts/smoke.sh`:** content below. `chmod +x` it.
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   BASE="${1:-http://localhost:3001}"
   PASS=0; FAIL=0

   check() {
     local name="$1" url="$2" jq_filter="${3:-.}"
     local body status
     body=$(curl -sS -w "\n%{http_code}" "$BASE$url")
     status=$(echo "$body" | tail -n1)
     body=$(echo "$body" | sed '$d')
     if [[ "$status" != "200" ]]; then
       echo "FAIL $name ($status) $url"; FAIL=$((FAIL+1)); return
     fi
     if ! echo "$body" | jq -e "$jq_filter" >/dev/null 2>&1; then
       echo "FAIL $name (jq) $url"; FAIL=$((FAIL+1)); return
     fi
     echo "PASS $name"; PASS=$((PASS+1))
   }

   check health           "/health"                          '.status'
   check feature-flags    "/api/feature-flags"               '.multi_tenancy != null'
   check assignments      "/api/assignments"                 'length >= 2'
   check ideptech-metrics "/api/all-metrics/ideptech"        '.aws or .github or .jira'
   check aws-metrics      "/api/aws-metrics"                 '. != null'
   check github-metrics   "/api/github-metrics/ideptech"     '. != null'
   check jira-metrics     "/api/jira-metrics/ideptech"       '. != null'

   echo "---"
   echo "PASS=$PASS FAIL=$FAIL"
   [[ $FAIL -eq 0 ]]
   ```

5. **Snapshot API contract keys:** Ask the human for the Railway URL,
   then run (do NOT commit these snapshots — they live in `_attic/`
   which is gitignored via `.railwayignore` but should still be in
   the working tree):
   ```
   mkdir -p _attic/contracts-baseline
   for ep in /health /api/feature-flags /api/assignments \
             /api/all-metrics/ideptech /api/aws-metrics \
             /api/github-metrics/ideptech /api/jira-metrics/ideptech; do
     fname=$(echo "$ep" | tr '/' '_')
     curl -sS "${RAILWAY_URL}${ep}" \
       | jq -S 'paths | map(tostring) | join(".")' \
       > "_attic/contracts-baseline${fname}.keys.txt" 2>/dev/null || true
   done
   ```
   If `jq` is not installed, STOP and ask the human to install it
   (it is a hard dependency of the smoke test).

6. **Verify smoke script:** run it locally against Railway as a
   one-shot test:
   ```
   ./scripts/smoke.sh https://<railway-url>
   ```
   Expected: PASS for all 7 checks. If any fail, STOP and report —
   the baseline cannot be established when production is unhealthy.

7. **Commit:** single commit containing `_attic/`, `scripts/smoke.sh`,
   `.railwayignore` change. Do NOT include the contracts-baseline
   files (they will be ignored because they're inside `_attic/`,
   but verify with `git status`).

   Commit message:
   ```
   CONSOL-P0: add _attic quarantine, smoke test, baseline tag

   Foundation for the consolidation. pre-consolidation tag marks
   the nuclear-restore point. _attic/ quarantines retiring files.
   scripts/smoke.sh validates endpoint contracts.

   Files: 3   Lines: +XX/-0
   Refs: consolidation/MASTER-RULES.md, CONSOL-P0-SETUP
   ```

### DEFINITION OF DONE

- `git tag --list | grep pre-consolidation` returns the tag.
- `_attic/README.md` exists.
- `.railwayignore` has `_attic/` line.
- `scripts/smoke.sh` exists, is executable, and passes against
  Railway.
- `_attic/contracts-baseline/` has 7 `.keys.txt` files.
- One commit on `main` (or the user's chosen base branch).
- Human has pushed the tag and the commit themselves.

### DO NOT

- Push anything. The human pushes.
- Create a feature branch. This phase commits directly to the
  base branch because it adds infrastructure, not behavior.
- Modify any code in `services/`, `routes/`, `backend/`,
  `frontend/`, `templates/`, `integrated_dashboard.py`.
- Begin Phase 1.

---

## When this phase is complete

After the human pushes the commit and confirms Railway is still
green, they will say "Phase 0 testing passed". At that point, and
ONLY at that point, rename this file:

```
git mv consolidation/phase-00-setup.md \
       consolidation/COMPLETED-phase-00-setup.md
git commit -m "CONSOL-P0: mark phase 0 complete"
```

Do NOT rename the file yourself. Wait for the explicit signal.

---

## EMBEDDED MASTER RULES (canonical: consolidation/MASTER-RULES.md)

### ABSOLUTE PROHIBITIONS

1. Do NOT proceed past the phase explicitly named in your prompt.
2. Do NOT modify any file outside the FILES YOU MAY MODIFY whitelist.
3. Do NOT "improve" code style, formatting, imports, comments, or
   naming outside the explicit scope.
4. Do NOT add new dependencies to requirements.txt unless the phase
   prompt authorizes it.
5. Do NOT modify .cursorrules, CLAUDE.md, README.md,
   ARCHITECTURE-OVERVIEW.md, railway.json, Procfile, .railwayignore,
   or .gitignore UNLESS the phase prompt authorizes it.
6. Do NOT run `git push`. Stop at `git commit`.
7. Do NOT create pull requests. Do NOT merge.
8. Do NOT run the smoke test against the Railway URL (except where a
   phase explicitly requires it, like this Phase 0). The human runs
   the Railway smoke for normal phases.
9. Do NOT delete files. Move them to `_attic/` instead.
10. Do NOT add tests, CI configs, hooks, linters, formatters outside
    phase scope.
11. Do NOT refactor anything not explicitly named. Bugs out of scope
    get noted, not fixed.
12. Do NOT use feature flags for this work.
13. Do NOT mark any phase COMPLETED yourself. Wait for the human.

### STOP CONDITIONS

- Pre-flight or post-flight check fails.
- Smoke test goes from PASS to FAIL.
- Diff includes any file outside the whitelist.
- Scope is larger than the prompt described.
- API call returns unexpected shape.
- Unsure whether an action is in scope -> STOP.

### REPORT FORMAT

1. What changed (files, commit SHAs).
2. What you did NOT do that you noticed (out-of-scope findings).
3. Smoke test PASS/FAIL counts.
4. Next phase ID (do not start it).
5. What the human should verify on Railway.
