# Phase 09 - MCP revival (parallel track, cannot break Railway)

**Task ID:** CONSOL-P9-MCP-REVIVE
**Phase:** 9 of 11
**Status:** PENDING — rename to `COMPLETED-phase-09-mcp-revive.md` when human confirms testing passed.

## Why this phase exists

`mcp_server.py` currently has Python syntax errors (mismatched braces
and `properties=` kwarg syntax in dict-literal positions). It imports
from `backend/` modules that Phase 10 is about to retire. The human
needs MCP working for their separate "entrepreneur OS" project. This
phase fixes MCP, re-points it at `services/*`, and merges
`requirements-mcp.txt` into `requirements.txt` so there is one
dependency set.

Critical safety property: MCP is stdio-based and NOT deployed to
Railway. This phase cannot break production by construction.

## How this phase fits

Parallel track. Run any time after Phase 5 (when
`services/embedded/railway_metrics.py` exists). Independent of the
cleanup phases. Recommended order: after Phase 8 so the repo is
already lean, but Phase 10 must wait until Phase 9 is done (because
Phase 10 removes the `backend/` modules MCP currently imports from).

---

## TASK PROMPT

### OBJECTIVE

Restore `mcp_server.py` to working state. Fix syntax errors.
Re-point imports to `services/*`. Merge `requirements-mcp.txt`
into `requirements.txt`. MCP is NOT on Railway — this work cannot
break production.

### CONTEXT FOR THE AGENT

- MCP will power an "entrepreneur OS" project the user is building.
- MCP is stdio-based, run locally by an MCP client.
- The current `mcp_server.py` has tool definitions with broken
  Python syntax (mismatched braces, `properties=` kwarg syntax
  in dict literal positions). Fix mechanically — do NOT redesign
  tools.

### PRECONDITION

- Phase 8 COMPLETED (or at least Phase 5; see "How this phase fits").
  Railway green.
- Branch: `consolidation/phase-9-mcp-revive` off `main`.
- `mcp_server.py` exists at repo root.

### FILES YOU MAY MODIFY

- `mcp_server.py`
- `mcp_config.json`
- `requirements.txt`

### FILES YOU MAY CREATE

- `services/metrics_aggregator.py`

### FILES YOU MAY MOVE

- `requirements-mcp.txt` -> `_attic/requirements-mcp.txt`

### FILES YOU MUST NOT MODIFY

- `routes/api_routes.py`
- `integrated_dashboard.py`
- Anything under `services/embedded/`
- `services/chatbot_service.py`
- `services/assignment_service.py`
- `backend/` (still exists; Phase 10 removes it)

### STEPS

**Commit 1 — dependency consolidation**
- Compare `requirements.txt` vs `requirements-mcp.txt`.
- Add to `requirements.txt` ONLY the lines from
  `requirements-mcp.txt` that are NOT already present and that
  `mcp_server.py` actually imports (grep `mcp_server.py` for the
  modules first). Likely:
      mcp>=1.0.0
      aiofiles>=23.2.0   (only if imported)
- Do NOT change any existing pinned version in `requirements.txt`.
  If there's a conflict (e.g., flask version), keep the existing
  `requirements.txt` version — that is what runs on Railway.
- `git mv requirements-mcp.txt _attic/requirements-mcp.txt`
- Post-flight: `pip install -r requirements.txt` succeeds in a
  clean venv. (If you cannot create a clean venv, document the
  pip resolve output instead.)
- Commit.

**Commit 2 — create services/metrics_aggregator.py**
- Create a new file that composes the embedded metrics services
  (`assignment_service`, `EmbeddedAWSMetrics`,
  `EmbeddedGitHubMetrics`, `EmbeddedJiraMetrics`, `OpenAIMetrics`,
  `RailwayMetrics`) into one `MetricsAggregator` class with an
  async `get_all_metrics(config)` method matching the shape of
  `backend/metrics_service.py`'s `MetricsAggregator`.
- This file is consumed only by MCP. It does not change Flask
  behavior.
- Post-flight: `python -c "from services.metrics_aggregator
  import MetricsAggregator"` succeeds.
- Commit.

**Commit 3 — fix mcp_server.py syntax**
- Walk `mcp_server.py` top to bottom. For every `Tool(...)`
  definition, convert kwarg-style `properties=` inside dict
  literals to proper dict syntax with `"properties":`. Fix
  mismatched braces.
- DO NOT add or remove any tools. DO NOT rename tools. DO NOT
  change tool schemas semantically — only fix syntax to match
  each tool's original intent.
- Gate: `python -m py_compile mcp_server.py` succeeds.
- Commit.

**Commit 4 — re-point imports**
- In `mcp_server.py`, replace:
      from assignment_service import AssignmentService
      from metrics_service import MetricsAggregator, AWSMetrics, ...
      from chatbot_service import chatbot_service
  with:
      from services.assignment_service import AssignmentService
      from services.metrics_aggregator import MetricsAggregator
      from services.embedded.aws_metrics import EmbeddedAWSMetrics
          as AWSMetrics
      from services.embedded.github_metrics import
          EmbeddedGitHubMetrics as GitHubMetrics
      from services.embedded.jira_metrics import
          EmbeddedJiraMetrics as JiraMetrics
      from services.embedded.railway_metrics import RailwayMetrics
      from services.chatbot_service import process_question
- Update the chatbot call sites to use the function
  `process_question` instead of an object `chatbot_service`. Match
  call signatures carefully — show diff first.
- Gate: `python -m py_compile mcp_server.py`.
- Commit.

**Commit 5 — verify mcp_config.json**
- Confirm `mcp_config.json` has `command: "python"`,
  `args: ["mcp_server.py"]`, `PYTHONPATH: "."` — adjust ONLY if
  wrong. If correct, no commit needed.

### MANUAL VALIDATION (the human runs, not the agent)

- In a separate terminal, `python mcp_server.py` should start
  and block on stdio. No exceptions.
- Wire into Claude Desktop or `mcp-cli`; call `list_tools` and
  `get_assignments`. Verify both return.

### DEFINITION OF DONE

- Up to 5 commits.
- `python -m py_compile mcp_server.py` succeeds.
- `requirements-mcp.txt` is in `_attic/`.
- `mcp_server.py` imports only from `services/*`.
- Flask app on Railway is untouched and still green.

### DO NOT

- Add new MCP tools.
- Refactor MCP tool schemas semantically.
- Re-design how MCP handles errors.
- Touch any file under `backend/`.
- Touch Railway deploy config in any way.
- Begin Phase 10.

---

## When this phase is complete

Human says "Phase 9 testing passed" (which means MCP works end-to-end
via their preferred MCP client) -> rename:
```
git mv consolidation/phase-09-mcp-revive.md \
       consolidation/COMPLETED-phase-09-mcp-revive.md
git commit -m "CONSOL-P9: mark phase 9 complete"
```

---

## EMBEDDED MASTER RULES

1. Stop after this phase.
2. Whitelist-only.
3. No style changes outside scope.
4. New deps explicitly authorized here for `mcp>=1.0.0` and
   `aiofiles>=23.2.0` (if used). NOTHING ELSE.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .railwayignore, .gitignore.
6. No `git push`. No PRs. No merges.
7. Smoke is not relevant to MCP — MCP is not on Railway. Use
   `python -m py_compile` and the manual MCP client test instead.
8. No deletions; use `_attic/`.
9. No tooling outside scope.
10. No refactoring outside scope.
11. No feature flags.
12. Do NOT mark COMPLETED yourself.

PRE-FLIGHT: clean status, correct branch, mcp_server.py exists.
POST-FLIGHT: `python -m py_compile mcp_server.py` clean, services
imports resolve, `pip install -r requirements.txt` clean.
STOP CONDITIONS: syntax can't be mechanically resolved, tool
schemas would need redesign, any out-of-whitelist diff,
uncertainty.
REPORT: files+SHAs, out-of-scope findings (likely: tool
inventory in mcp_server.py vs what user actually needs), list of
MCP tools confirmed working via client.
