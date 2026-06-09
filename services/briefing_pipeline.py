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
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Build delivery_metrics and connector_metrics maps keyed by assignment id.

    When fetch_metrics is False, returns empty overlays (budget/team signals still fire).
    """
    if not fetch_metrics:
        return {}, {}

    from routes.api_routes import collect_assignment_metrics

    delivery: Dict[str, Dict[str, Any]] = {}
    connector: Dict[str, Dict[str, Any]] = {}

    for assignment in assignments or []:
        if (assignment.get("status") or "active") != "active":
            continue
        aid = str(assignment.get("id") or assignment.get("assignment_id") or "")
        if not aid:
            continue

        raw = collect_assignment_metrics(workspace_id, aid, assignment)
        failures: List[str] = []
        last_success: Optional[str] = None

        github_block = raw.get("github")
        jira_block = raw.get("jira")
        delivery_row: Dict[str, Any] = {}

        if isinstance(github_block, list):
            if github_block and isinstance(github_block[0], dict) and github_block[0].get("error"):
                failures.append("github")
            else:
                commits_30 = sum(
                    int(r.get("commits_last_30_days") or 0)
                    for r in github_block
                    if isinstance(r, dict) and not r.get("error")
                )
                if commits_30 == 0:
                    delivery_row["commits_last_7_days"] = 0
                    delivery_row["commits_last_14_days"] = 0
                last_success = _utc_now()

        if isinstance(jira_block, dict):
            if jira_block.get("error"):
                failures.append("jira")
            else:
                issues_30 = jira_block.get("total_issues_last_30_days")
                if issues_30 is not None:
                    delivery_row.setdefault("jira_issues_last_7_days", int(issues_30))
                last_success = last_success or _utc_now()

        for name, block in raw.items():
            if name in ("github", "jira"):
                continue
            if isinstance(block, dict) and block.get("error"):
                failures.append(name)
            elif isinstance(block, list) and block and isinstance(block[0], dict) and block[0].get("error"):
                failures.append(name)
            elif block is not None:
                last_success = last_success or _utc_now()

        if delivery_row:
            delivery[aid] = delivery_row

        connector[aid] = {
            "failures": failures,
            "last_success_at": last_success if not failures else None,
        }

    return delivery, connector


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
) -> Dict[str, Any]:
    """Run full pipeline and return storable briefing payload."""
    delivery_metrics, connector_metrics = build_metrics_overlays(
        workspace_id,
        assignments,
        fetch_metrics=fetch_metrics,
    )

    signal_engine = SignalEngine()
    signals = signal_engine.evaluate_assignments(
        assignments,
        delivery_metrics=delivery_metrics,
        connector_metrics=connector_metrics,
    )
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

    return {
        "generated_at": executive.generated_at,
        "workspace_id": workspace_id,
        "source_fingerprint": assignments_fingerprint(assignments),
        "signals": signal_dicts,
        "recommendations": rec_dicts,
        "executive_briefing": executive.to_dict(),
        "portfolio_metrics": build_portfolio_metrics(assignments),
        "metrics_fetched": fetch_metrics,
        "generation_mode": executive.generation_mode,
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
) -> Dict[str, Any]:
    briefing = run_ctolens_pipeline(
        workspace_id,
        assignments,
        fetch_metrics=fetch_metrics,
        use_ai=use_ai,
    )
    store_ctolens_briefing(secure_db, workspace_id, briefing)
    briefing["feedback_summary"] = feedback_summary(secure_db, workspace_id)
    return briefing


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
