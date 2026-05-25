# CONSOLIDATION MASTER RULES

These rules apply to EVERY consolidation task. The phase-specific
prompt narrows scope further but never relaxes these rules.

Every phase file embeds a copy of these rules. If the embedded copy
disagrees with this file, THIS FILE WINS — but stop and report the
discrepancy before continuing.

## ABSOLUTE PROHIBITIONS

1. Do NOT proceed past the phase explicitly named in your prompt.
   Stop after completing it, even if you believe the next phase is
   trivial.
2. Do NOT modify any file outside the FILES YOU MAY MODIFY whitelist
   in your phase prompt. If you think a file outside the whitelist
   needs touching, STOP and report — do not edit it.
3. Do NOT "improve" code style, formatting, import order, type hints,
   comments, docstrings, or naming outside the explicit scope of
   your task. Mechanical changes only.
4. Do NOT add new dependencies to requirements.txt unless the phase
   prompt explicitly authorizes it.
5. Do NOT modify any of: .cursorrules, CLAUDE.md, README.md,
   ARCHITECTURE-OVERVIEW.md, railway.json, Procfile, .railwayignore,
   .gitignore — UNLESS the phase prompt explicitly authorizes it.
6. Do NOT run `git push`. Stop at `git commit`.
7. Do NOT create pull requests. Do NOT merge.
8. Do NOT run the smoke test against the Railway URL. Only against
   http://localhost:3001. The human runs the Railway smoke.
9. Do NOT delete files. Move them to `_attic/` instead.
   Deletion happens only in Phase 11, explicitly.
10. Do NOT add tests, CI configs, GitHub Actions, pre-commit hooks,
    linters, formatters, or any tooling outside the phase scope.
11. Do NOT refactor anything you are not explicitly told to refactor.
    If you find a bug outside scope, note it in your final report.
    Do not fix it.
12. Do NOT use feature flags for this work. These are implementation
    swaps under unchanged contracts, not new features.
13. Do NOT mark any phase as COMPLETED yourself. Only rename a file
    to `COMPLETED-...` when the human explicitly tells you
    "Phase N testing passed."

## REQUIRED PRE-FLIGHT (run before any edits)

Before any file modification:

a. `git status` — must be clean (no unstaged/uncommitted changes).
   If not clean, STOP and report.
b. `git rev-parse --abbrev-ref HEAD` — must match the branch named
   in the phase prompt's PRECONDITION. If not, STOP.
c. Verify every file in the FILES YOU MAY MODIFY whitelist exists.
   If any is missing, STOP — the previous phase didn't land.
d. Verify every file in the FILES THAT MUST NOT EXIST list (if any)
   is absent. If present, STOP — a prior phase was incomplete or
   reverted.
e. Verify `_attic/` exists and `scripts/smoke.sh` exists and is
   executable. If not, STOP and run Phase 00 first.

If any pre-flight check fails: STOP. Print which check failed.
Do not attempt remediation. Wait for human instruction.

## REQUIRED POST-FLIGHT (run after edits, before committing)

a. `python -c "import integrated_dashboard"` must succeed.
b. `python -m py_compile <every file you modified>` must succeed.
c. Start the app locally on port 3001 in the background, run
   `./scripts/smoke.sh http://localhost:3001`, stop the app.
   All checks must PASS.
d. `git diff --stat` — show the human the file list and line counts.
e. `git diff` — show the human the actual diff. WAIT for human
   approval before running `git add` or `git commit`.

If any post-flight check fails: STOP. Do not commit. Do not "try
another approach". Report the failure and wait.

## COMMIT DISCIPLINE

- One concern per commit. If your phase has multiple sub-commits
  listed, make them as separate commits, in the order listed.
- Commit message format (exact):

      <phase-id>: <imperative summary, <=60 chars>

      <one paragraph of WHY, <=500 chars>

      Files: <count>   Lines: +<add>/-<del>
      Refs: consolidation/MASTER-RULES.md, <phase-prompt-id>

- Do NOT use `git commit --amend` unless the phase prompt says so.
- Do NOT use `git rebase`, `git reset --hard`, or `git push --force`.

## STOP CONDITIONS

Stop immediately and report (do NOT attempt to fix) if:
- Pre-flight or post-flight check fails.
- A smoke test goes from PASS to FAIL.
- The diff includes any file outside the whitelist.
- You discover the scope is larger than the prompt described.
- Any AWS, GitHub, Jira, OpenAI, or Railway API call returns an
  unexpected shape that breaks an endpoint contract.
- You're unsure whether an action is in scope. Default to STOP.

## REPORT FORMAT (at end of every task)

Produce a short final report with:
1. What changed (file list, commit SHAs).
2. What you did NOT do that you noticed (out-of-scope findings).
3. Smoke test result (counts of PASS/FAIL).
4. Next phase to run (by ID only — do not start it).
5. Anything the human should verify on Railway after they push.

## ESCAPE HATCH

If at any time you (the agent) feel pressure to do "just one more
small thing" outside scope — that is the drift impulse. STOP.
Report the temptation in your final report. Let the human decide
in a separate task. There is no "small thing" that justifies
breaking the rollback property of this system.
