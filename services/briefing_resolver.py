"""
Resolve stored briefing for export/share — CTOLens or legacy attention engine.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)


def briefing_features_enabled() -> bool:
    return (
        os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true"
        or os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() == "true"
    )


def ctolens_enabled() -> bool:
    return os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true"


def get_stored_briefing_raw(secure_db: Any, workspace_id: str) -> Optional[Dict[str, Any]]:
    """Return CTOLens briefing when enabled, else legacy attention briefing."""
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return None
    settings = ws.get("settings") or {}
    if ctolens_enabled():
        briefing = settings.get("ctolens_briefing")
        if briefing:
            return briefing
    from services.attention_engine import get_stored_briefing

    return get_stored_briefing(secure_db, workspace_id)


def ensure_stored_briefing(
    secure_db: Any,
    workspace_id: str,
    assignments: List[Dict[str, Any]],
    *,
    fetch_metrics: bool = False,
    use_ai: Optional[bool] = None,
) -> Dict[str, Any]:
    """Return stored briefing, generating a fast deterministic one if missing."""
    existing = get_stored_briefing_raw(secure_db, workspace_id)
    if existing:
        return existing

    if ctolens_enabled():
        from services.briefing_pipeline import refresh_workspace_ctolens_briefing

        return refresh_workspace_ctolens_briefing(
            workspace_id,
            assignments,
            secure_db,
            fetch_metrics=fetch_metrics,
            use_ai=False if use_ai is None else use_ai,
        )

    from services.attention_engine import (
        build_attention_briefing,
        store_briefing_in_workspace,
    )

    last_import = (
        (secure_db.get_workspace(workspace_id) or {}).get("settings", {}).get("last_import")
    )
    briefing = build_attention_briefing(
        assignments,
        import_metadata=last_import,
    )
    store_briefing_in_workspace(secure_db, workspace_id, briefing)
    return briefing


def is_ctolens_briefing(briefing: Dict[str, Any]) -> bool:
    eb = briefing.get("executive_briefing") or {}
    return bool(eb.get("executive_summary") and eb.get("recommended_actions") is not None)


def normalize_briefing_for_export(briefing: Dict[str, Any]) -> Dict[str, Any]:
    """Map CTOLens or legacy briefing into a shared export view."""
    from services.ctolens_run_metadata import strip_briefing_for_export

    if not is_ctolens_briefing(briefing):
        return briefing

    briefing = strip_briefing_for_export(briefing)
    eb = briefing.get("executive_briefing") or {}
    portfolio_metrics = briefing.get("portfolio_metrics") or {}
    health = portfolio_metrics.get("health_score") or {}

    risk_signals = [
        {
            "severity": r.get("severity", "warning"),
            "detail": r.get("summary") or "",
            "title": r.get("project_name") or "",
        }
        for r in eb.get("top_risks") or []
    ]
    opportunity_signals = [
        {
            "detail": o.get("summary") or "",
            "title": o.get("project_name") or "",
        }
        for o in eb.get("opportunities") or []
    ]
    recommended_actions = eb.get("recommended_actions") or []
    top_recommendations = [
        {
            "detail": f"{a.get('title', '')}: {a.get('description', '')}".strip(": "),
            "title": a.get("title") or "",
        }
        for a in recommended_actions[:3]
    ]

    attention_items: List[Dict[str, Any]] = []
    for r in eb.get("top_risks") or []:
        sev = r.get("severity")
        if sev not in ("critical", "warning"):
            continue
        attention_items.append(
            {
                "severity": sev,
                "message": f"{r.get('project_name', '')}: {r.get('summary') or ''}".strip(": "),
            }
        )

    band = (health.get("band") or "healthy").replace("_", " ").title()
    if band.lower() == "healthy":
        portfolio_status = "Healthy"
    elif "risk" in band.lower() or band.lower() == "critical":
        portfolio_status = "Critical" if "critical" in band.lower() else "Needs Attention"
    else:
        portfolio_status = band

    summary_text = eb.get("executive_summary") or ""
    return {
        **briefing,
        "risk_signals": risk_signals,
        "opportunity_signals": opportunity_signals,
        "recommended_actions": recommended_actions,
        "top_recommendations_export": top_recommendations,
        "projects_requiring_attention": eb.get("projects_requiring_attention") or [],
        "confidence_assessment": eb.get("confidence_assessment") or {},
        "cto_narrative": summary_text,
        "system_health_score": health,
        "portfolio_status": portfolio_status,
        "founder_attention_items": attention_items,
        "executive_briefing": {
            **eb,
            "headline": summary_text[:220] if summary_text else "",
            "bullets": [a.get("title") for a in recommended_actions[:5] if a.get("title")],
            "executive_focus": eb.get("executive_focus") or {},
        },
        "portfolio_snapshot": {"summary": portfolio_metrics.get("summary") or {}},
        "generation_mode": briefing.get("generation_mode") or eb.get("generation_mode"),
        "executive_focus": eb.get("executive_focus") or briefing.get("executive_focus") or {},
    }
