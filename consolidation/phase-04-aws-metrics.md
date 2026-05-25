# Phase 04 - Promote AWSMetrics (largest change)

**Task ID:** CONSOL-P4-AWS-METRICS
**Phase:** 4 of 11
**Status:** PENDING — rename to `COMPLETED-phase-04-aws-metrics.md` when human confirms testing passed.

## Why this phase exists

The deployed `services/embedded/aws_metrics.py` (~214 lines) only
provides basic cost totals and a flat resource inventory. The richer
`backend/metrics_service.py::AWSMetrics` (~470 lines) provides
Lightsail bundle pricing, Route 53 zones, S3 details, EC2 tags,
RDS multi-AZ/storage, and `get_comprehensive_aws_report()`. The
React frontend (being retired) referenced an endpoint
`/api/assignments/<id>/cto-insights` that consumes the comprehensive
report; the Jinja dashboard can use it too once it exists.

## How this phase fits

Largest implementation swap. Six commits. Most ceremony. Preserves
existing endpoint contracts as supersets.

---

## TASK PROMPT

### OBJECTIVE

Replace `services/embedded/aws_metrics.py::EmbeddedAWSMetrics` with
the richer `backend/metrics_service.py::AWSMetrics`. Preserve the
existing `get_metrics()` contract. Add a new endpoint
`/api/assignments/<id>/cto-insights`.

### PRECONDITION

- Phase 3 COMPLETED. Railway green.
- Branch: `consolidation/phase-4-aws-metrics` off `main`.
- AWS credentials in env are valid; basic `ce:GetCostAndUsage` call
  succeeds locally. If not, STOP.

### FILES YOU MAY MODIFY

- `services/embedded/aws_metrics.py`
- `services/embedded/aws_metrics_v2.py` (new, temporary)
- `routes/api_routes.py`

### FILES YOU MAY MOVE

- `services/embedded/aws_metrics.py` -> `_attic/aws_metrics_old.py`
  (in Commit 6 only)
- `services/embedded/aws_metrics_v2.py` ->
  `services/embedded/aws_metrics.py` (in Commit 6 only)

### FILES YOU MUST NOT MODIFY

- `backend/metrics_service.py`
- Any other `services/embedded/*.py`
- `frontend/`, `templates/`, any `*.md`.

### STEPS

**Commit 1 — additive: drop in v2 file**
- Create `services/embedded/aws_metrics_v2.py`.
- Copy the `AWSMetrics` class AND its private helpers
  (`_get_aws_client`, `_get_cost_analysis`, `_get_lightsail_details`,
  `_get_ec2_details`, `_get_rds_details`, `_get_route53_details`,
  `_get_s3_details`, `_format_bytes`,
  `_get_cost_optimization_recommendations`, `get_cost_metrics`,
  `get_comprehensive_aws_report`) verbatim from
  `backend/metrics_service.py`.
- Rename the class to `EmbeddedAWSMetricsV2` to avoid collision.
- Do NOT import it anywhere yet.
- Post-flight. Commit.

**Commit 2 — add adapter**
- On `EmbeddedAWSMetricsV2`, add method `get_metrics()` that returns
  the same dict shape as the existing
  `EmbeddedAWSMetrics.get_metrics()` (read the existing file first
  and match it). The adapter calls `get_cost_metrics()` internally.
- Post-flight. Commit.

**Commit 3 — switch /api/aws-metrics only**
- In `routes/api_routes.py`, change ONLY the `/api/aws-metrics`
  endpoint to use a new instance of `EmbeddedAWSMetricsV2`. All
  other endpoints keep using the existing instance.
- Run smoke. Diff `/api/aws-metrics` output against the contract
  baseline. Top-level keys must be a superset of baseline.
- Post-flight. Show diff. Commit.

**Commit 4 — switch remaining call sites**
- Migrate the AWS branches in `/api/all-metrics/<id>` and
  `/api/assignments/<id>/metrics` to `EmbeddedAWSMetricsV2`.
- Post-flight. Commit.

**Commit 5 — add /cto-insights endpoint**
- Add to `routes/api_routes.py`:
      @app.route("/api/assignments/<assignment_id>/cto-insights")
      def cto_insights(assignment_id): ...
  that loads the assignment via `assignment_service`, checks
  `metrics_config.aws.enabled`, and returns
  `aws_metrics_v2.get_comprehensive_aws_report()` merged with
  `assignment_info` (`id`, `name`, `monthly_burn_rate`, `team_size`).
  Mirror the shape used in `backend/main.py`'s existing
  `get_cto_insights()` (read it for reference, do not import it).
- Run smoke + a manual curl of the new endpoint.
- Post-flight. Commit.

**Commit 6 — promote v2 to canonical**
- `git mv services/embedded/aws_metrics.py _attic/aws_metrics_old.py`
- `git mv services/embedded/aws_metrics_v2.py
        services/embedded/aws_metrics.py`
- Rename the class inside back to `EmbeddedAWSMetrics`.
- Update the import in `routes/api_routes.py` (and only there) to
  use `EmbeddedAWSMetrics` again (drop the V2 suffix).
- Run full smoke. Post-flight. Commit.

### DEFINITION OF DONE

- 6 commits.
- `/api/aws-metrics` shape is a superset of baseline (no removed
  keys).
- `/api/assignments/ideptech/cto-insights` returns 200 with keys
  including `cost_analysis`, `lightsail_resources`,
  `ec2_resources`, `rds_resources`, `route53_resources`,
  `s3_resources`, `recommendations`.
- Smoke: all PASS.

### DO NOT

- Touch `backend/metrics_service.py`.
- Add new top-level keys to `/api/aws-metrics` that change shape vs
  baseline (only additive at deeper levels is allowed).
- Add caching or retries.
- Begin Phase 5.

---

## When this phase is complete

Human says "Phase 4 testing passed" -> rename:
```
git mv consolidation/phase-04-aws-metrics.md \
       consolidation/COMPLETED-phase-04-aws-metrics.md
git commit -m "CONSOL-P4: mark phase 4 complete"
```

---

## EMBEDDED MASTER RULES

1. Stop after this phase.
2. Whitelist-only modifications.
3. No style changes outside scope.
4. No new deps.
5. No edits to .cursorrules, CLAUDE.md, README.md, railway.json,
   Procfile, .railwayignore, .gitignore.
6. No `git push`. No PRs. No merges.
7. Smoke localhost only.
8. No deletions; use `_attic/`.
9. No tooling outside scope.
10. No bug-fixing outside scope.
11. No feature flags.
12. Do NOT mark COMPLETED yourself.

PRE-FLIGHT: clean status, correct branch, whitelist exists.
POST-FLIGHT: import OK, py_compile OK, smoke all PASS, diff approved.
STOP CONDITIONS: any check fail, smoke regression, out-of-whitelist
diff, scope expansion, unexpected API shape, uncertainty.
REPORT: files+SHAs, out-of-scope findings, smoke counts, next phase
ID, Railway verification notes.
