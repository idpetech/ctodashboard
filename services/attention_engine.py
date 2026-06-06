"""
Attention Engine — deterministic CTO-level briefing from workspace data.

Rule-based, no external APIs, no randomness. Works with partial data.
Reuses portfolio_service computations where applicable.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from services.portfolio_service import (
    attention_center,
    budget_variance,
    build_portfolio_overview,
    connector_health,
    portfolio_health_score,
    portfolio_summary,
)

logger = get_logger(__name__)


def _input_fingerprint(assignments: List[Dict[str, Any]]) -> str:
    """Stable hash of assignment snapshot for change detection."""
    payload = []
    for a in sorted(assignments, key=lambda x: str(x.get("id") or x.get("assignment_id") or "")):
        payload.append({
            "id": a.get("id") or a.get("assignment_id"),
            "status": a.get("status"),
            "burn": a.get("monthly_burn_rate"),
            "target": a.get("target_monthly_burn"),
            "team": a.get("team_size"),
        })
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _sentence_join(parts: List[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def _risk_signals(
    assignments: List[Dict[str, Any]],
    budget: Dict[str, Any],
    connectors: Dict[str, Any],
    attention: Dict[str, Any],
) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []

    for item in attention.get("items", []):
        if item.get("severity") in ("critical", "warning"):
            signals.append({
                "type": item.get("type", "attention"),
                "severity": item.get("severity"),
                "assignment_id": item.get("assignment_id"),
                "title": item.get("name") or item.get("assignment_id"),
                "detail": item.get("message"),
            })

    # Stalled / overloaded heuristics from assignment fields only.
    active = [a for a in assignments if (a.get("status") or "active") == "active"]
    for a in active:
        team = a.get("team_size")
        burn = a.get("monthly_burn_rate")
        if team and int(team) >= 12:
            signals.append({
                "type": "overloaded_team",
                "severity": "warning",
                "assignment_id": a.get("id"),
                "title": a.get("name"),
                "detail": f"{a.get('name')} has {team} people — consider splitting workstreams",
            })
        if burn and team and int(team) > 0:
            per_head = int(burn) / int(team)
            if per_head > 15000:
                signals.append({
                    "type": "high_burn_per_head",
                    "severity": "warning",
                    "assignment_id": a.get("id"),
                    "title": a.get("name"),
                    "detail": (
                        f"{a.get('name')} burn is ${_fmt(burn)}/mo "
                        f"({_fmt(int(per_head))}/person) — review staffing efficiency"
                    ),
                })

    readiness = connectors.get("readiness_pct")
    if readiness is not None and readiness < 50:
        signals.append({
            "type": "connector_gap",
            "severity": "critical" if readiness < 25 else "warning",
            "assignment_id": None,
            "title": "Connector readiness",
            "detail": f"Only {readiness}% of enabled connectors have credentials configured",
        })

    missing = budget.get("missing_target_count", 0)
    if missing > 0:
        signals.append({
            "type": "missing_budget_targets",
            "severity": "info",
            "assignment_id": None,
            "title": "Budget visibility gap",
            "detail": f"{missing} active assignment(s) lack target monthly burn",
        })

    # Sort: critical first, then warning, then info.
    rank = {"critical": 0, "warning": 1, "info": 2}
    signals.sort(key=lambda s: rank.get(s.get("severity", "info"), 9))
    return signals[:20]


def _opportunity_signals(
    assignments: List[Dict[str, Any]],
    budget: Dict[str, Any],
    connectors: Dict[str, Any],
) -> List[Dict[str, Any]]:
    opportunities: List[Dict[str, Any]] = []
    active = [a for a in assignments if (a.get("status") or "active") == "active"]

    # Under-budget assignments — room to invest or reallocate.
    for row in budget.get("assignments", []):
        if row.get("status") == "under" and row.get("variance_pct", 0) <= -15:
            opportunities.append({
                "type": "budget_headroom",
                "impact": "medium",
                "assignment_id": row.get("assignment_id"),
                "title": row.get("name"),
                "detail": (
                    f"{row['name']} is {abs(row['variance_pct'])}% under target — "
                    "capacity may be available for acceleration or cost reallocation"
                ),
            })

    # Connectors not enabled — automation candidates.
    for a in active:
        cfg = a.get("metrics_config") or {}
        enabled = [k for k, v in cfg.items() if isinstance(v, dict) and v.get("enabled")]
        if not enabled:
            opportunities.append({
                "type": "automation_candidate",
                "impact": "high",
                "assignment_id": a.get("id"),
                "title": a.get("name"),
                "detail": (
                    f"{a.get('name')} has no connectors enabled — "
                    "connect GitHub/Jira for automated health signals"
                ),
            })
        elif "github" not in enabled and "jira" not in enabled:
            opportunities.append({
                "type": "delivery_visibility",
                "impact": "medium",
                "assignment_id": a.get("id"),
                "title": a.get("name"),
                "detail": f"{a.get('name')} lacks GitHub/Jira — add delivery metrics for earlier risk detection",
            })

    total_enabled = connectors.get("total_enabled", 0)
    total_ready = connectors.get("total_ready", 0)
    if total_enabled > 0 and total_ready == total_enabled:
        opportunities.append({
            "type": "full_connector_coverage",
            "impact": "low",
            "assignment_id": None,
            "title": "Connector stack ready",
            "detail": "All enabled connectors are configured — good baseline for daily briefings",
        })

    if len(active) >= 3 and not opportunities:
        opportunities.append({
            "type": "portfolio_optimization",
            "impact": "medium",
            "assignment_id": None,
            "title": "Cross-portfolio review",
            "detail": (
                f"Managing {len(active)} active assignments — "
                "periodic burn and connector review can surface consolidation wins"
            ),
        })

    return opportunities[:15]


def _executive_briefing(
    summary: Dict[str, Any],
    health: Dict[str, Any],
    risks: List[Dict[str, Any]],
    opportunities: List[Dict[str, Any]],
    previous: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    active = summary.get("active_assignments", 0)
    total = summary.get("total_assignments", 0)
    burn = summary.get("total_monthly_burn", 0)
    score = health.get("overall_score", 100)
    band = health.get("band", "healthy")

    bullets: List[str] = []
    bullets.append(f"{active} of {total} assignments are active with {_fmt(burn)}/mo total burn.")
    bullets.append(f"Portfolio health score is {score}/100 ({band.replace('_', ' ')}).")

    crit = sum(1 for r in risks if r.get("severity") == "critical")
    warn = sum(1 for r in risks if r.get("severity") == "warning")
    if crit:
        bullets.append(f"{crit} critical risk signal(s) need immediate attention.")
    elif warn:
        bullets.append(f"{warn} warning(s) flagged for review.")
    else:
        bullets.append("No critical risks detected in the current snapshot.")

    if opportunities:
        bullets.append(f"{len(opportunities)} optimization opportunity(ies) identified.")

    changes: List[str] = []
    if previous:
        prev_score = (previous.get("system_health_score") or {}).get("score")
        if prev_score is not None and prev_score != score:
            delta = score - prev_score
            direction = "improved" if delta > 0 else "declined"
            changes.append(f"Health score {direction} by {abs(delta)} points since last refresh.")
        prev_active = (previous.get("executive_briefing") or {}).get("active_assignments")
        if prev_active is not None and prev_active != active:
            changes.append(f"Active assignment count changed from {prev_active} to {active}.")

    return {
        "headline": (
            "Portfolio needs attention" if crit else
            "Portfolio has warnings" if warn else
            "Portfolio is stable"
        ),
        "active_assignments": active,
        "total_assignments": total,
        "total_monthly_burn": burn,
        "bullets": bullets,
        "changes_since_last_refresh": changes,
    }


def _cto_narrative(
    summary: Dict[str, Any],
    health: Dict[str, Any],
    risks: List[Dict[str, Any]],
    opportunities: List[Dict[str, Any]],
) -> str:
    active = summary.get("active_assignments", 0)
    burn = summary.get("total_monthly_burn", 0)
    score = health.get("overall_score", 100)
    band = health.get("band", "healthy").replace("_", " ")

    parts: List[str] = []
    parts.append(
        f"Across your portfolio, {active} active assignment(s) are running "
        f"with a combined monthly burn of {_fmt(burn)}."
    )
    parts.append(
        f"The system health score is {score} out of 100, placing the portfolio "
        f"in the {band} range based on budget, connector readiness, and delivery signals."
    )

    crit = [r for r in risks if r.get("severity") == "critical"]
    if crit:
        parts.append(
            f"The most urgent item is {crit[0].get('title')}: {crit[0].get('detail')}"
        )
    elif risks:
        parts.append(
            f"Top concern: {risks[0].get('detail')}"
        )
    else:
        parts.append("No critical blockers were detected in this refresh.")

    missing = summary.get("assignments_missing_target", 0)
    if missing:
        parts.append(
            f"{missing} assignment(s) still lack a target monthly burn, "
            "which limits budget variance tracking."
        )

    if opportunities:
        parts.append(
            f"A high-impact opportunity: {opportunities[0].get('detail')}"
        )

    comps = health.get("components") or {}
    weak = []
    if comps.get("financial") is not None and comps["financial"] < 70:
        weak.append("financial discipline")
    if comps.get("connector") is not None and comps["connector"] < 70:
        weak.append("connector configuration")
    if comps.get("delivery") is not None and comps["delivery"] < 70:
        weak.append("delivery coverage")
    if weak:
        parts.append(f"Focus areas for improvement: {', '.join(weak)}.")

    parts.append(
        "This briefing is computed deterministically from your current data — "
        "refresh after imports or connector updates for the latest picture."
    )

    return _sentence_join(parts)


def _fmt(value: Any) -> str:
    try:
        return f"${int(value):,}"
    except (TypeError, ValueError):
        return "$0"


def build_attention_briefing(
    assignments: List[Dict[str, Any]],
    previous_briefing: Optional[Dict[str, Any]] = None,
    import_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a full attention briefing from assignment rows.

    Deterministic for the same input. Gracefully handles empty/partial data.
    """
    if not assignments:
        empty = {
            "generated_at": datetime.utcnow().isoformat(),
            "input_fingerprint": "empty",
            "executive_briefing": {
                "headline": "No data yet",
                "bullets": ["Import assignments or connect services to generate a briefing."],
                "changes_since_last_refresh": [],
            },
            "risk_signals": [],
            "opportunity_signals": [],
            "system_health_score": {
                "score": 0,
                "band": "critical",
                "explanation": "No assignments in workspace",
                "components": {},
            },
            "cto_narrative": (
                "Your workspace has no assignment data yet. "
                "Upload a CSV or Excel file, or create assignments manually, "
                "to receive a CTO-level briefing."
            ),
            "import_context": import_metadata,
        }
        return empty

    overview = build_portfolio_overview(assignments)
    summary = overview.get("summary") or portfolio_summary(assignments)
    budget = overview.get("budget_variance") or budget_variance(assignments)
    connectors = overview.get("connector_health") or connector_health(assignments)
    attention = overview.get("attention_center") or attention_center(assignments, budget)
    health = overview.get("health_score") or portfolio_health_score(
        budget, connectors, attention, summary.get("active_assignments", 0)
    )

    risks = _risk_signals(assignments, budget, connectors, attention)
    opportunities = _opportunity_signals(assignments, budget, connectors)
    executive = _executive_briefing(summary, health, risks, opportunities, previous_briefing)

    score = health.get("overall_score", 100)
    explanation_parts = []
    comps = health.get("components") or {}
    if comps.get("financial") is not None:
        explanation_parts.append(f"Financial component: {comps['financial']}/100")
    if comps.get("connector") is not None:
        explanation_parts.append(f"Connector readiness: {comps['connector']}/100")
    if comps.get("delivery") is not None:
        explanation_parts.append(f"Delivery coverage: {comps['delivery']}/100")

    briefing = {
        "generated_at": datetime.utcnow().isoformat(),
        "input_fingerprint": _input_fingerprint(assignments),
        "executive_briefing": executive,
        "risk_signals": risks,
        "opportunity_signals": opportunities,
        "system_health_score": {
            "score": score,
            "band": health.get("band", "healthy"),
            "explanation": "; ".join(explanation_parts) or "Based on available portfolio signals",
            "components": comps,
        },
        "cto_narrative": _cto_narrative(summary, health, risks, opportunities),
        "import_context": import_metadata,
        "portfolio_snapshot": {
            "summary": summary,
            "attention_item_count": attention.get("total", 0),
        },
    }

    from services.executive_language import enrich_briefing_for_executives

    briefing = enrich_briefing_for_executives(briefing, attention)

    logger.info(
        "Attention briefing built: score=%s risks=%d opportunities=%d",
        score,
        len(risks),
        len(opportunities),
    )
    return briefing


def compute_score_trends(
    history: List[Dict[str, Any]],
    current: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare current scores to the previous history entry."""
    prev = history[-1] if len(history) >= 1 else None
    trends: Dict[str, Any] = {}

    def _delta(key: str) -> Optional[Dict[str, Any]]:
        cur = current.get(key)
        if cur is None:
            return None
        if not prev or prev.get(key) is None:
            return {"current": cur, "previous": None, "change": None}
        change = int(cur) - int(prev[key])
        return {"current": cur, "previous": prev[key], "change": change}

    for metric in ("health", "financial", "connector", "delivery"):
        row = _delta(metric)
        if row:
            trends[metric] = row
    return trends


def append_health_score_history(
    settings: Dict[str, Any],
    briefing: Dict[str, Any],
) -> Dict[str, Any]:
    """Append score snapshot to settings history and attach trends to briefing."""
    health = briefing.get("system_health_score") or {}
    comps = health.get("components") or {}
    entry = {
        "generated_at": briefing.get("generated_at"),
        "health": health.get("score"),
        "financial": comps.get("financial"),
        "connector": comps.get("connector"),
        "delivery": comps.get("delivery"),
    }

    history: List[Dict[str, Any]] = list(settings.get("health_score_history") or [])
    trends = compute_score_trends(history, entry)
    history.append(entry)
    settings["health_score_history"] = history[-52:]
    briefing["score_trends"] = trends
    return settings


def store_briefing_in_workspace(
    secure_db: Any,
    workspace_id: str,
    briefing: Dict[str, Any],
) -> bool:
    """Persist briefing in workspace.settings (no new tables)."""
    try:
        ws = secure_db.get_workspace(workspace_id)
        if not ws:
            return False
        settings = ws.get("settings") or {}
        settings = append_health_score_history(settings, briefing)
        settings["attention_briefing"] = briefing
        settings["attention_briefing_updated_at"] = briefing.get("generated_at")
        return secure_db.store_workspace(
            workspace_id,
            ws.get("name", workspace_id),
            ws.get("description", ""),
            settings=settings,
        )
    except Exception as e:
        logger.error("Failed to store attention briefing: %s", e)
        return False


def get_stored_briefing(secure_db: Any, workspace_id: str) -> Optional[Dict[str, Any]]:
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return None
    return (ws.get("settings") or {}).get("attention_briefing")
