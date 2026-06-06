"""
Shareable read-only executive reports — reuses stored briefing snapshots.

Lightweight persistence: workspace.settings.shared_reports + local token index.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from config.logging_config import get_logger
from services.portfolio_service import build_portfolio_overview

logger = get_logger(__name__)

_INDEX_ENV = "REPORT_SHARE_INDEX_PATH"
_DEFAULT_INDEX = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "report_share_index.json")
_MAX_VIEWS_LOG = 50


def _index_path() -> str:
    return os.getenv(_INDEX_ENV, _DEFAULT_INDEX)


def _load_index() -> Dict[str, Any]:
    path = _index_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Share index read failed: %s", e)
        return {}


def _save_index(index: Dict[str, Any]) -> None:
    path = _index_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def _parse_expires(expires_in_days: Optional[int]) -> Optional[str]:
    if not expires_in_days or expires_in_days <= 0:
        return None
    return (datetime.utcnow() + timedelta(days=int(expires_in_days))).isoformat()


def create_share_link(
    secure_db: Any,
    workspace_id: str,
    *,
    expires_in_days: Optional[int] = 30,
    request_base_url: str = "",
) -> Dict[str, Any]:
    """Snapshot current briefing + portfolio and return a public share URL."""
    from services.attention_engine import get_stored_briefing

    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        raise ValueError("Workspace not found")

    briefing = get_stored_briefing(secure_db, workspace_id)
    if not briefing:
        raise ValueError("No briefing available — refresh briefing first")

    assignments = secure_db.get_workspace_assignments(workspace_id) or []
    portfolio = build_portfolio_overview(assignments)
    portfolio_name = ws.get("name") or workspace_id
    settings = ws.get("settings") or {}
    score_trends = briefing.get("score_trends") or settings.get("health_score_history_trends")

    token = secrets.token_urlsafe(24)
    created_at = datetime.utcnow().isoformat()
    expires_at = _parse_expires(expires_in_days)

    share_record = {
        "token": token,
        "workspace_id": workspace_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "view_count": 0,
        "views": [],
        "snapshot": {
            "portfolio_name": portfolio_name,
            "briefing": briefing,
            "portfolio": portfolio,
            "score_trends": score_trends,
        },
    }

    shared = settings.get("shared_reports") or {}
    shared[token] = share_record
    settings["shared_reports"] = shared

    if not secure_db.store_workspace(
        workspace_id,
        ws.get("name", workspace_id),
        ws.get("description", ""),
        settings=settings,
    ):
        raise RuntimeError("Failed to persist share link")

    index = _load_index()
    index[token] = {
        "workspace_id": workspace_id,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    _save_index(index)

    path = f"/r/{token}"
    share_url = f"{request_base_url.rstrip('/')}{path}" if request_base_url else path

    return {
        "token": token,
        "share_url": share_url,
        "path": path,
        "expires_at": expires_at,
        "created_at": created_at,
    }


def get_share_report(
    secure_db: Any,
    token: str,
    *,
    user_agent: str = "",
    record_view: bool = True,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Load a shared report snapshot. Returns (report_dict, error_message).
    Increments view_count when record_view=True.
    """
    index = _load_index()
    entry = index.get(token)
    if not entry:
        return None, "Report not found or link has been revoked"

    workspace_id = entry.get("workspace_id")
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return None, "Report not found"

    shared = (ws.get("settings") or {}).get("shared_reports") or {}
    record = shared.get(token)
    if not record:
        return None, "Report not found or link has been revoked"

    expires_at = record.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.utcnow() > exp.replace(tzinfo=None):
                return None, "This report link has expired"
        except (TypeError, ValueError):
            pass

    if record_view:
        record["view_count"] = int(record.get("view_count") or 0) + 1
        views: List[Dict[str, str]] = list(record.get("views") or [])
        views.append({
            "viewed_at": datetime.utcnow().isoformat(),
            "user_agent": (user_agent or "")[:200],
        })
        record["views"] = views[-_MAX_VIEWS_LOG:]
        shared[token] = record
        settings = ws.get("settings") or {}
        settings["shared_reports"] = shared
        secure_db.store_workspace(
            workspace_id,
            ws.get("name", workspace_id),
            ws.get("description", ""),
            settings=settings,
        )

    snapshot = record.get("snapshot") or {}
    return {
        "token": token,
        "workspace_id": workspace_id,
        "created_at": record.get("created_at"),
        "expires_at": record.get("expires_at"),
        "view_count": record.get("view_count", 0),
        **snapshot,
    }, None


def build_report_template_context(report: Dict[str, Any]) -> Dict[str, Any]:
    """Shape a share snapshot for report_share.html."""
    briefing = report.get("briefing") or {}
    portfolio = report.get("portfolio") or {}
    summary = portfolio.get("summary") or briefing.get("portfolio_snapshot", {}).get("summary") or {}
    health = briefing.get("system_health_score") or portfolio.get("health_score") or {}
    eb = briefing.get("executive_briefing") or {}
    risks = briefing.get("risk_signals") or []
    opps = briefing.get("opportunity_signals") or []

    attention_items = briefing.get("founder_attention_items")
    if not attention_items:
        from services.executive_language import translate_attention_item

        ac = portfolio.get("attention_center") or {}
        attention_items = [translate_attention_item(i) for i in (ac.get("items") or [])]
        if not attention_items:
            attention_items = [
                {"severity": r.get("severity", "warning"), "message": r.get("detail", "")}
                for r in risks[:8]
            ]

    generated = briefing.get("generated_at") or report.get("created_at")
    generated_display = generated
    if generated:
        try:
            generated_display = datetime.fromisoformat(
                generated.replace("Z", "+00:00")
            ).strftime("%B %d, %Y")
        except (TypeError, ValueError):
            pass

    return {
        "portfolio_name": report.get("portfolio_name") or "Portfolio",
        "portfolio_status": briefing.get("portfolio_status") or "Healthy",
        "health_score": health.get("score") or health.get("overall_score") or "—",
        "headline": eb.get("headline"),
        "bullets": eb.get("bullets") or [],
        "narrative": briefing.get("cto_narrative"),
        "top_risks": risks[:3],
        "top_recommendations": opps[:3],
        "all_risks": risks,
        "all_opportunities": opps,
        "attention_items": attention_items,
        "summary": summary,
        "score_trends": report.get("score_trends") or briefing.get("score_trends"),
        "generated_display": generated_display,
        "view_count": report.get("view_count", 0),
    }


def list_share_links(secure_db: Any, workspace_id: str) -> List[Dict[str, Any]]:
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return []
    shared = (ws.get("settings") or {}).get("shared_reports") or {}
    out = []
    for token, rec in shared.items():
        out.append({
            "token": token,
            "created_at": rec.get("created_at"),
            "expires_at": rec.get("expires_at"),
            "view_count": rec.get("view_count", 0),
            "path": f"/r/{token}",
        })
    out.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return out
