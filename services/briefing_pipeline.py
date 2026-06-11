"""
CTOLens briefing pipeline — Signals → Recommendations → Executive Briefing.

Orchestrates the three deterministic layers plus optional LLM summarization.
Persists results to workspace.settings.ctolens_briefing.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from config.logging_config import get_logger
from services.executive_briefing.feedback import feedback_summary
from services.executive_briefing.generator import ExecutiveBriefingGenerator, is_ai_briefing_enabled
from services.recommendations.engine import RecommendationEngine
from services.signals.engine import SignalEngine

logger = get_logger(__name__)


def is_ctolens_briefing_enabled() -> bool:
    return os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true"


def is_signal_engine_enabled() -> bool:
    return os.getenv("ENABLE_SIGNAL_ENGINE", "false").lower() == "true"


def is_recommendation_engine_enabled() -> bool:
    return os.getenv("ENABLE_RECOMMENDATION_ENGINE", "false").lower() == "true"


def ctolens_pipeline_active() -> bool:
    """True when any CTOLens layer flag is on (master or individual)."""
    return (
        is_ctolens_briefing_enabled()
        or is_signal_engine_enabled()
        or is_recommendation_engine_enabled()
        or is_ai_briefing_enabled()
    )


def build_metrics_overlays(
    workspace_id: str,
    assignments: List[Dict[str, Any]],
    *,
    fetch_metrics: bool = False,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Build delivery_metrics and connector_metrics maps keyed by assignment id.

    Returns connector_runs diagnostics (per assignment / enabled connector).
    When fetch_metrics is False, returns empty overlays (budget/team signals still fire).
    """
    if not fetch_metrics:
        return {}, {}, []

    from routes.api_routes import collect_assignment_metrics

    delivery: Dict[str, Dict[str, Any]] = {}
    connector: Dict[str, Dict[str, Any]] = {}
    connector_runs: List[Dict[str, Any]] = []

    for assignment in assignments or []:
        if (assignment.get("status") or "active") != "active":
            continue
        aid = str(assignment.get("id") or assignment.get("assignment_id") or "")
        if not aid:
            continue

        name = assignment.get("name") or aid
        metrics_config = assignment.get("metrics_config") or {}
        enabled_connectors = [
            k for k, cfg in metrics_config.items() if isinstance(cfg, dict) and cfg.get("enabled")
        ]

        raw = collect_assignment_metrics(workspace_id, aid, assignment)
        failures: List[str] = []
        successes: List[str] = []
        last_success: Optional[str] = None
        delivery_row: Dict[str, Any] = {}

        github_block = raw.get("github")
        if "github" in enabled_connectors:
            if isinstance(github_block, list):
                if (
                    github_block
                    and isinstance(github_block[0], dict)
                    and github_block[0].get("error")
                ):
                    failures.append("github")
                else:
                    c7 = sum(
                        int(r.get("commits_last_7_days") or 0)
                        for r in github_block
                        if isinstance(r, dict) and not r.get("error")
                    )
                    c14 = sum(
                        int(r.get("commits_last_14_days") or 0)
                        for r in github_block
                        if isinstance(r, dict) and not r.get("error")
                    )
                    cprior = sum(
                        int(r.get("commits_prior_7_days") or 0)
                        for r in github_block
                        if isinstance(r, dict) and not r.get("error")
                    )
                    delivery_row["commits_last_7_days"] = c7
                    delivery_row["commits_last_14_days"] = c14
                    delivery_row["commits_prior_7_days"] = cprior
                    successes.append("github")
                    last_success = _utc_now()

        jira_block = raw.get("jira")
        if "jira" in enabled_connectors:
            if isinstance(jira_block, dict):
                if jira_block.get("error"):
                    failures.append("jira")
                else:
                    issues_7 = jira_block.get("jira_issues_last_7_days")
                    if issues_7 is not None:
                        delivery_row["jira_issues_last_7_days"] = int(issues_7)
                    successes.append("jira")
                    last_success = last_success or _utc_now()

        for conn_name in enabled_connectors:
            if conn_name in ("github", "jira"):
                continue
            block = raw.get(conn_name)
            if isinstance(block, dict) and block.get("error"):
                failures.append(conn_name)
            elif (
                isinstance(block, list)
                and block
                and isinstance(block[0], dict)
                and block[0].get("error")
            ):
                failures.append(conn_name)
            elif block is not None:
                successes.append(conn_name)
                last_success = last_success or _utc_now()

        if delivery_row:
            delivery[aid] = delivery_row

        connector[aid] = {
            "failures": failures,
            "last_success_at": last_success if not failures else None,
        }

        for conn_name in enabled_connectors:
            status = (
                "ok"
                if conn_name in successes
                else ("error" if conn_name in failures else "skipped")
            )
            connector_runs.append(
                {
                    "assignment_id": aid,
                    "assignment_name": name,
                    "connector": conn_name,
                    "status": status,
                }
            )

    return delivery, connector, connector_runs


def assignments_fingerprint(assignments: List[Dict[str, Any]]) -> str:
    """Stable hash of active assignment fields that affect briefing output."""
    rows: List[Dict[str, Any]] = []
    for assignment in sorted(
        assignments or [],
        key=lambda item: str(item.get("id") or item.get("assignment_id") or ""),
    ):
        if (assignment.get("status") or "active") != "active":
            continue
        rows.append(
            {
                "id": str(assignment.get("id") or assignment.get("assignment_id") or ""),
                "status": assignment.get("status"),
                "monthly_burn_rate": assignment.get("monthly_burn_rate"),
                "target_monthly_burn": assignment.get("target_monthly_burn"),
                "previous_monthly_burn": assignment.get("previous_monthly_burn"),
                "team_size": assignment.get("team_size"),
                "owner": assignment.get("owner"),
                "metrics_config": assignment.get("metrics_config") or {},
            }
        )
    payload = json.dumps(rows, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def assess_briefing_staleness(
    briefing: Optional[Dict[str, Any]],
    assignments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare stored briefing fingerprint to current assignments."""
    current = assignments_fingerprint(assignments)
    if not briefing:
        return {
            "is_stale": False,
            "reason": None,
            "current_fingerprint": current,
            "stored_fingerprint": None,
        }

    stored = briefing.get("source_fingerprint")
    generated_at = briefing.get("generated_at")
    if not stored:
        return {
            "is_stale": True,
            "reason": "Briefing was generated before change tracking — update recommended.",
            "current_fingerprint": current,
            "stored_fingerprint": None,
            "generated_at": generated_at,
        }
    if stored != current:
        return {
            "is_stale": True,
            "reason": "Portfolio data changed since this briefing was generated.",
            "current_fingerprint": current,
            "stored_fingerprint": stored,
            "generated_at": generated_at,
        }
    return {
        "is_stale": False,
        "reason": None,
        "current_fingerprint": current,
        "stored_fingerprint": stored,
        "generated_at": generated_at,
    }


def run_ctolens_pipeline(
    workspace_id: str,
    assignments: List[Dict[str, Any]],
    *,
    fetch_metrics: bool = False,
    use_ai: Optional[bool] = None,
    run_source: str = "manual",
) -> Dict[str, Any]:
    """Run full pipeline and return storable briefing payload."""
    from services.ctolens_run_metadata import filter_signals_for_run_mode, new_run_id

    run_id = new_run_id()
    delivery_metrics, connector_metrics, connector_runs = build_metrics_overlays(
        workspace_id,
        assignments,
        fetch_metrics=fetch_metrics,
    )

    signal_engine = SignalEngine()
    raw_signals = signal_engine.evaluate_assignments(
        assignments,
        delivery_metrics=delivery_metrics,
        connector_metrics=connector_metrics,
    )
    signals = filter_signals_for_run_mode(raw_signals, fetch_metrics)
    signal_dicts = [s.to_dict() for s in signals]

    recommendations = RecommendationEngine().recommend(signals)
    rec_dicts = [r.to_dict() for r in recommendations]

    executive = ExecutiveBriefingGenerator().generate_from_assignments(
        assignments,
        delivery_metrics=delivery_metrics,
        connector_metrics=connector_metrics,
        use_ai=use_ai,
    )

    from services.executive_briefing.assembler import build_portfolio_metrics

    connectors_attempted = sorted(
        {r["connector"] for r in connector_runs if r.get("status") == "ok"}
    )

    return {
        "generated_at": executive.generated_at,
        "workspace_id": workspace_id,
        "source_fingerprint": assignments_fingerprint(assignments),
        "run_id": run_id,
        "run_source": run_source,
        "signals": signal_dicts,
        "recommendations": rec_dicts,
        "executive_briefing": executive.to_dict(),
        "portfolio_metrics": build_portfolio_metrics(assignments),
        "metrics_fetched": fetch_metrics,
        "generation_mode": executive.generation_mode,
        "connector_runs": connector_runs,
        "signals_evaluated_count": len(signal_dicts),
        "signals_shown_count": len(executive.to_dict().get("top_risks") or [])
        + len(executive.to_dict().get("opportunities") or []),
        "connectors_attempted": connectors_attempted,
    }


def store_ctolens_briefing(
    secure_db: Any,
    workspace_id: str,
    briefing: Dict[str, Any],
) -> bool:
    try:
        ws = secure_db.get_workspace(workspace_id)
        if not ws:
            return False
        settings = ws.get("settings") or {}
        settings["ctolens_briefing"] = briefing
        settings["ctolens_briefing_updated_at"] = briefing.get("generated_at")
        return secure_db.store_workspace(
            workspace_id,
            ws.get("name", workspace_id),
            ws.get("description", ""),
            settings=settings,
        )
    except Exception as exc:
        logger.error("Failed to store CTOLens briefing: %s", exc)
        return False


def get_stored_ctolens_briefing(
    secure_db: Any,
    workspace_id: str,
) -> Optional[Dict[str, Any]]:
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return None
    return (ws.get("settings") or {}).get("ctolens_briefing")


def get_ctolens_briefing_with_feedback(
    secure_db: Any,
    workspace_id: str,
) -> Optional[Dict[str, Any]]:
    briefing = get_stored_ctolens_briefing(secure_db, workspace_id)
    if not briefing:
        return None
    out = dict(briefing)
    out["feedback_summary"] = feedback_summary(secure_db, workspace_id)
    return out


def refresh_workspace_ctolens_briefing(
    workspace_id: str,
    assignments: List[Dict[str, Any]],
    secure_db: Any,
    *,
    fetch_metrics: bool = False,
    use_ai: Optional[bool] = None,
    run_source: str = "manual",
) -> Dict[str, Any]:
    import time

    from services.ctolens_run_metadata import (
        build_run_log_entry,
        build_run_status,
        persist_run_metadata,
    )

    run_type = "enriched" if fetch_metrics else "fast"
    active_count = len(
        [a for a in (assignments or []) if (a.get("status") or "active") == "active"]
    )
    logger.info(
        "briefing_run_started workspace_id=%s run_type=%s source=%s assignments=%s",
        workspace_id,
        run_type,
        run_source,
        active_count,
        extra={
            "operation": "briefing_run_started",
            "workspace_id": workspace_id,
            "run_type": run_type,
            "run_source": run_source,
        },
    )
    started = time.monotonic()
    error_msg = None
    status = "success"
    briefing: Dict[str, Any] = {}

    try:
        briefing = run_ctolens_pipeline(
            workspace_id,
            assignments,
            fetch_metrics=fetch_metrics,
            use_ai=use_ai,
            run_source=run_source,
        )
        if fetch_metrics and briefing.get("connector_runs"):
            failed = [r for r in briefing["connector_runs"] if r.get("status") == "error"]
            if failed and len(failed) < len(briefing["connector_runs"]):
                status = "partial"
            elif failed:
                status = "failed"
    except Exception as exc:
        error_msg = str(exc)
        status = "failed"
        logger.exception("CTOLens briefing run failed for %s", workspace_id)
        previous = get_stored_ctolens_briefing(secure_db, workspace_id)
        if previous:
            briefing = dict(previous)
            briefing["feedback_summary"] = feedback_summary(secure_db, workspace_id)
            duration = time.monotonic() - started
            run_status = build_run_status(
                run_id=briefing.get("run_id", "failed"),
                run_type=run_type,
                source=run_source,
                status=status,
                duration_seconds=duration,
                assignments_evaluated=active_count,
                connectors_attempted=briefing.get("connectors_attempted") or [],
                metrics_fetched=fetch_metrics,
            )
            persist_run_metadata(
                secure_db,
                workspace_id,
                run_status,
                build_run_log_entry(
                    run_id=run_status["last_run_id"],
                    run_type=run_type,
                    source=run_source,
                    status=status,
                    duration_seconds=duration,
                    assignments_evaluated=active_count,
                    connectors_attempted=briefing.get("connectors_attempted") or [],
                    metrics_fetched=fetch_metrics,
                    error=error_msg,
                ),
            )
            logger.info(
                "briefing_run_completed workspace_id=%s status=%s kept_previous=1",
                workspace_id,
                status,
            )
            return briefing
        raise

    duration = time.monotonic() - started
    run_status = build_run_status(
        run_id=briefing.get("run_id", ""),
        run_type=run_type,
        source=run_source,
        status=status,
        duration_seconds=duration,
        assignments_evaluated=active_count,
        connectors_attempted=briefing.get("connectors_attempted") or [],
        metrics_fetched=fetch_metrics,
        connector_runs=briefing.get("connector_runs"),
    )
    store_ctolens_briefing(secure_db, workspace_id, briefing)
    persist_run_metadata(
        secure_db,
        workspace_id,
        run_status,
        build_run_log_entry(
            run_id=briefing.get("run_id", ""),
            run_type=run_type,
            source=run_source,
            status=status,
            duration_seconds=duration,
            assignments_evaluated=active_count,
            connectors_attempted=briefing.get("connectors_attempted") or [],
            metrics_fetched=fetch_metrics,
            error=error_msg,
        ),
    )
    briefing["feedback_summary"] = feedback_summary(secure_db, workspace_id)
    logger.info(
        "briefing_run_completed workspace_id=%s run_type=%s status=%s duration=%.1fs",
        workspace_id,
        run_type,
        status,
        duration,
        extra={
            "operation": "briefing_run_completed",
            "workspace_id": workspace_id,
            "run_type": run_type,
            "status": status,
            "duration_seconds": round(duration, 1),
        },
    )
    return briefing


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
