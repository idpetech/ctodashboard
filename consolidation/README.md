# Consolidation Task System

Operational task files for the CTO Dashboard consolidation. Each file
is a self-contained, guardrailed prompt for a single phase. Designed
to be executed across many sessions over weeks without context drift.

## How to use this system

1. **You** (the human) decide it is time to run a phase.
2. **You** verify the current Railway deployment is healthy and that
   you have time to babysit the work.
3. **You** instruct the agent: "Run phase 3" (or whatever number).
4. **The agent** finds the file `phase-03-*.md` in this directory,
   reads it top-to-bottom, and executes ONLY what it says.
5. **The agent stops** after completing the phase. It does NOT push,
   it does NOT merge, it does NOT begin the next phase.
6. **You** review the diff, push, watch Railway redeploy, run the
   smoke test, and exercise the app for real.
7. **You** tell the agent: "Phase 3 testing passed."
8. **The agent** renames the file by prepending `COMPLETED-` to the
   filename. Example:
       phase-03-github-metrics.md  ->  COMPLETED-phase-03-github-metrics.md
9. Repeat for the next phase, in a new chat session.

## File layout

```
consolidation/
├── README.md                          # this file
├── MASTER-RULES.md                    # canonical rules (mirrored into each phase)
├── phase-00-setup.md                  # one-time Day 0 setup
├── phase-01-config-move.md
├── phase-02-assignment-service.md
├── phase-03-github-metrics.md
├── phase-04-aws-metrics.md
├── phase-05-railway-metrics.md
├── phase-06-strip-inline.md
├── phase-07-kill-react.md
├── phase-08-quarantine-dead.md
├── phase-09-mcp-revive.md
├── phase-10-backend-empty.md
└── phase-11-empty-attic.md
```

After completion, files are renamed in place:

```
COMPLETED-phase-01-config-move.md
COMPLETED-phase-02-assignment-service.md
phase-03-github-metrics.md           <- next to run
phase-04-aws-metrics.md
...
```

`COMPLETED-` sorts before `phase-` alphabetically, so `ls` shows
finished work at the top and pending work at the bottom.

## Why every file embeds the master rules

Sessions are weeks apart. Context resets. A cold-start agent reading
`phase-04-aws-metrics.md` must not need to also read `MASTER-RULES.md`
to know what it cannot do. So every phase file embeds the rules
inline. `MASTER-RULES.md` is the canonical source — if the rules
change, regenerate the embedded copies.

## Decisions already made (do not re-debate)

- **Deployment target:** Railway, gunicorn, `integrated_dashboard:app`.
- **UI:** Jinja template (`templates/dashboard.html`). React SPA is
  being retired (Phase 7).
- **MCP:** Will be revived (Phase 9) and re-pointed to `services/*`.
  It will power a separate "entrepreneur OS" project.
- **Service layer:** `services/` is canonical. `backend/` is being
  emptied. Duplicate inline classes in `integrated_dashboard.py` are
  being deleted.
- **Quarantine before delete:** `_attic/` holds retired files for
  >=14 days before Phase 11 permanently deletes them.
- **Single dependency file:** `requirements.txt`. `requirements-mcp.txt`
  is merged into it and retired.

If a phase prompt seems to contradict one of these decisions: STOP
and ask the human. Do not re-decide.

## Status board

Cold-start agents: run `ls consolidation/` to see which phases are
already done (`COMPLETED-` prefix). Do not re-run completed phases.
