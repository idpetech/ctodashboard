# Phase 11 - Delete _attic/ (the final delete)

**Task ID:** CONSOL-P11-EMPTY-ATTIC
**Phase:** 11 of 11 (FINAL)
**Status:** PENDING — rename to `COMPLETED-phase-11-empty-attic.md` when human confirms testing passed.

## Why this phase exists

`_attic/` has held every retired file for the duration of the
consolidation. After at least 14 days of stable Railway operation
with zero rollbacks, the safety net is no longer needed. This phase
permanently deletes `_attic/`.

This is the ONLY phase that performs irreversible deletion. Triple-
gated. The `pre-consolidation` tag remains as the nuclear restore
point forever.

## How this phase fits

Final phase. Tags the repo `consolidation-complete`.

---

## TASK PROMPT

### OBJECTIVE

After at least 14 days of stable Railway operation with zero
rollbacks, delete `_attic/` permanently. Tag the repo
`consolidation-complete`.

### PRECONDITION (ALL must be true; verify each)

- Phase 10 marked COMPLETED at least 14 days ago. Confirm with:
  ```
  git log --since=14.days --grep=CONSOL-P10 --oneline
  ```
  Should return zero rows (i.e., P10's mark-complete commit is
  older than 14 days).
- Zero Railway rollbacks since Phase 10. The human asserts this
  in writing in the chat. If the human has not asserted, STOP.
- `pre-consolidation` tag still exists on origin:
  ```
  git ls-remote --tags origin | grep pre-consolidation
  ```
  If not, STOP.
- `consolidation-complete` tag does NOT yet exist. If it does,
  STOP — Phase 11 already ran.
- Branch: `consolidation/phase-11-empty-attic` off `main`.

### FILES YOU MAY DELETE

- `_attic/` (entire directory)

### FILES YOU MAY MODIFY

- `.railwayignore` (remove the `_attic/` line)

### FILES YOU MUST NOT MODIFY

- Everything else. Especially: do NOT "tidy up" anything else in
  this phase. Deletion only.

### STEPS

**Commit 1 — announce + remove**
- `git rm -r _attic/`
- Remove the `_attic/` line from `.railwayignore`.
- Post-flight: `integrated_dashboard.py` imports clean, smoke green.
- Show diff. Show file count delta (`git diff --stat | tail -1`).
- Commit:
  ```
  CONSOL-P11: remove _attic/ after 14d stable production

  Final delete. The pre-consolidation tag remains as the
  ultimate restore point.

  Files: -N   Lines: -X
  Refs: consolidation/MASTER-RULES.md, CONSOL-P11-EMPTY-ATTIC
  ```

**Commit 2 — tag completion (instruct human only)**
- The agent does NOT create tags. The final report MUST instruct
  the human to run:
  ```
  git tag consolidation-complete
  git push origin consolidation-complete
  ```

### DEFINITION OF DONE

- 1 commit deleting `_attic/`.
- Smoke: all PASS.
- Final report instructs the human to tag.

### DO NOT

- Delete the `pre-consolidation` tag.
- Touch any code outside the deletion.
- "Polish" remaining files.
- Suggest further phases without being asked.
- Create the `consolidation-complete` tag yourself.

---

## When this phase is complete

Human says "Phase 11 testing passed and tag pushed" -> rename:
```
git mv consolidation/phase-11-empty-attic.md \
       consolidation/COMPLETED-phase-11-empty-attic.md
git commit -m "CONSOL-P11: mark phase 11 complete"
```

At that point, the entire `consolidation/` directory exists only
as historical artifacts (all files have `COMPLETED-` prefix).
The human may choose to delete the directory entirely at any
future date — but that is a separate decision, not part of this
plan.

---

## EMBEDDED MASTER RULES

1. Stop after this phase. (There is no Phase 12.)
2. Whitelist-only. The whitelist is small: `_attic/` (delete) and
   `.railwayignore` (modify one line).
3. No style changes outside scope.
4. No new deps.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .gitignore.
6. No `git push`. No PRs. No merges. The human pushes.
7. Smoke localhost only.
8. This phase EXPLICITLY authorizes deletion of `_attic/`. No other
   deletions are authorized.
9. No tooling outside scope.
10. No refactoring outside scope.
11. No feature flags.
12. Do NOT create the `consolidation-complete` tag. Instruct the
    human to do so in your final report.
13. Do NOT mark COMPLETED yourself.

PRE-FLIGHT: all four preconditions above pass; human asserted
"zero rollbacks" in chat.
POST-FLIGHT: smoke all PASS; show file count delta.
STOP CONDITIONS: any precondition fails, smoke regression after
deletion, scope expansion, uncertainty.
REPORT: file count and line delta, commit SHA, explicit
instruction to human to run the two `git tag` commands.
