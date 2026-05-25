# Phase 06 - Strip inline dead code from integrated_dashboard.py

**Task ID:** CONSOL-P6-STRIP-INLINE
**Phase:** 6 of 11
**Status:** PENDING — rename to `COMPLETED-phase-06-strip-inline.md` when human confirms testing passed.

## Why this phase exists

`integrated_dashboard.py` contains ~430 lines of inline class
definitions (`FEATURE_FLAGS`, `ServiceManager`, `WorkstreamService`,
`ServiceConfigService`, `TenantService`, `EmbeddedAWSMetrics`,
`EmbeddedGitHubMetrics`, `EmbeddedJiraMetrics`) that are shadowed by
the imports in `routes/api_routes.py`. They are dead code that
confuses every reader of the file. After phases 1–5, all live
behavior is sourced from `services/*`, so the inline copies can be
quarantined to `_attic/`.

Target: `integrated_dashboard.py` shrinks to a ~50–80 line WSGI
boot file.

## How this phase fits

First "cleanup" phase. No behavior change. Pure code-removal under
unchanged contracts.

---

## TASK PROMPT

### OBJECTIVE

Remove the inline class definitions in `integrated_dashboard.py`
that are shadowed by imports in `routes/api_routes.py`. Move them
to `_attic/` rather than deleting.

Classes to retire:
- `FEATURE_FLAGS` dict
- `ServiceManager`
- `WorkstreamService`
- `ServiceConfigService`
- `TenantService`
- `EmbeddedAWSMetrics`
- `EmbeddedGitHubMetrics`
- `EmbeddedJiraMetrics`
- Module-level instances at bottom: `aws_metrics`, `github_metrics`,
  `jira_metrics`, `service_manager`.

### PRECONDITION

- Phases 1–5 COMPLETED. Railway green.
- Branch: `consolidation/phase-6-strip-inline` off `main`.
- Run this verification BEFORE editing:
      grep -rn "from integrated_dashboard import" .
  Expected: zero matches. If non-zero, STOP and report.

### FILES YOU MAY MODIFY

- `integrated_dashboard.py`

### FILES YOU MAY CREATE

- `_attic/integrated_dashboard_inline_classes.py`

### FILES YOU MUST NOT MODIFY

- Everything else.

### STEPS

**Commit 1 — quarantine**
- Cut the listed classes and module-level instances out of
  `integrated_dashboard.py`.
- Paste them into
  `_attic/integrated_dashboard_inline_classes.py` with a header
  comment explaining what they are and when they were retired.
- `integrated_dashboard.py` should now contain only:
    * imports (`os`, `Flask`, `CORS`, `load_dotenv`)
    * `load_dotenv()` call
    * Flask app construction (with `template_folder`)
    * CORS configuration
    * `from routes.api_routes import register_routes`
    * `register_routes(app)`
    * `if __name__ == "__main__":` block
  Target length: <80 lines.
- Do NOT touch the `EmbeddedAWSMetrics` class etc. anywhere else
  (they are imported by `routes/api_routes.py` from
  `services/embedded/`, not from `integrated_dashboard`).
- Post-flight. The smoke test MUST be fully green.
- Commit.

### DEFINITION OF DONE

- 1 commit.
- `wc -l integrated_dashboard.py` < 80.
- Smoke: all PASS.
- App boots locally without errors.

### DO NOT

- Delete the classes from `integrated_dashboard.py` without copying
  them to `_attic/`.
- Modify `routes/api_routes.py` or any `services/*` file.
- "Clean up" imports beyond removing those now-unused.
- Begin Phase 7.

---

## When this phase is complete

Human says "Phase 6 testing passed" -> rename:
```
git mv consolidation/phase-06-strip-inline.md \
       consolidation/COMPLETED-phase-06-strip-inline.md
git commit -m "CONSOL-P6: mark phase 6 complete"
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

PRE-FLIGHT: clean status, correct branch, whitelist exists,
zero `from integrated_dashboard import` matches.
POST-FLIGHT: import OK, py_compile OK, smoke all PASS, diff approved.
STOP CONDITIONS: any check fail, smoke regression, out-of-whitelist
diff, scope expansion, unexpected API shape, uncertainty.
REPORT: files+SHAs, out-of-scope findings, smoke counts, next phase
ID, Railway verification notes.
