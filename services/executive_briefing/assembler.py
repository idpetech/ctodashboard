"""
Assemble BriefingInput and pre-sorted fact slices for the generator.
"""

from __future__ import annotations

from typing import Any, Dict, List

from services.executive_briefing.schema import (
    ActionItem,
    BriefingInput,
    OpportunityItem,
    ProjectAttentionItem,
    RiskItem,
)
from services.executive_briefing.success_criteria import build_executive_focus
from services.portfolio_service import build_portfolio_overview

OPPORTUNITY_SIGNAL_TYPES = frozenset(
    {
        "UNDER_BUDGET",
        "UNUSED_CAPACITY",
        "HIGH_PERFORMING_PROJECT",
        "SLOW_DELIVERY_TREND",
        "BLOCKED_WORK_INCREASE",
        "PR_REVIEW_BOTTLENECK",
        "HIGH_REOPEN_RATE",
        "BUILD_FAILURE_TREND",
        "RELEASE_INSTABILITY",
        "DEPENDENCY_CONCENTRATION",
        "HIGH_SERVICE_COUPLING",
        "TECH_DEBT_ACCUMULATION",
        "LOW_THROUGHPUT_PROJECT",
        "STALLED_PROJECT",
        "MOMENTUM_ACCELERATION",
    }
)

RISK_SIGNAL_TYPES = frozenset(
    {
        "OVER_BUDGET",
        "COST_SPIKE",
        "NO_COMMITS_7_DAYS",
        "NO_COMMITS_14_DAYS",
        "VELOCITY_DROP",
        "NO_JIRA_ACTIVITY",
        "CONNECTOR_FAILURE",
        "STALE_DATA",
        "MISSING_OWNER",
        "RESOURCE_IMBALANCE",
    }
)

ATTENTION_SEVERITIES = frozenset({"critical", "warning"})


def build_portfolio_metrics(assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
    overview = build_portfolio_overview(assignments or [])
    summary = overview.get("summary") or {}
    health = overview.get("health_score") or {}
    connectors = overview.get("connector_health") or {}
    budget = overview.get("budget_variance") or {}
    return {
        "summary": summary,
        "health_score": health,
        "connector_health": connectors,
        "budget_variance": {
            "portfolio_actual_burn": budget.get("portfolio_actual_burn"),
            "portfolio_target_burn": budget.get("portfolio_target_burn"),
            "portfolio_variance_pct": budget.get("portfolio_variance_pct"),
            "tracked_assignments": budget.get("tracked_assignments"),
        },
    }


def assess_data_completeness(
    portfolio_metrics: Dict[str, Any],
    signals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    connectors = portfolio_metrics.get("connector_health") or {}
    readiness = connectors.get("readiness_pct")
    low_conf = sum(1 for s in signals if float(s.get("confidence") or 0) < 0.75)
    missing_targets = (portfolio_metrics.get("summary") or {}).get("assignments_missing_target", 0)

    if readiness is None:
        level = "low"
    elif readiness >= 80 and low_conf == 0:
        level = "high"
    elif readiness >= 50:
        level = "medium"
    else:
        level = "low"

    return {
        "overall_level": level,
        "connector_readiness_pct": readiness,
        "low_confidence_signal_count": low_conf,
        "assignments_missing_target": missing_targets,
        "signal_count": len(signals),
    }


def build_briefing_input(
    assignments: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
) -> BriefingInput:
    portfolio_metrics = build_portfolio_metrics(assignments)
    completeness = assess_data_completeness(portfolio_metrics, signals)
    return BriefingInput(
        portfolio_metrics=portfolio_metrics,
        signals=signals,
        recommendations=recommendations,
        data_completeness=completeness,
    )


def pre_sort_facts(
    briefing_input: BriefingInput,
) -> Dict[str, Any]:
    """Deterministic section builders — source of truth before optional LLM polish."""

    signals = briefing_input.signals
    recommendations = briefing_input.recommendations

    top_risks: List[RiskItem] = []
    for sig in signals:
        stype = sig.get("signal_type") or ""
        sev = sig.get("severity") or "info"
        if stype not in RISK_SIGNAL_TYPES or sev not in ATTENTION_SEVERITIES:
            continue
        top_risks.append(
            RiskItem(
                project_name=str(sig.get("project_name") or ""),
                signal_type=str(stype),
                severity=str(sev),
                summary=str(sig.get("description") or sig.get("title") or ""),
                confidence=float(sig.get("confidence") or 0),
            )
        )
    top_risks.sort(key=lambda r: (-_severity_rank(r.severity), -r.confidence, r.project_name))

    opportunities: List[OpportunityItem] = []
    for sig in signals:
        stype = sig.get("signal_type") or ""
        if stype not in OPPORTUNITY_SIGNAL_TYPES:
            continue
        opportunities.append(
            OpportunityItem(
                project_name=str(sig.get("project_name") or ""),
                signal_type=str(stype),
                summary=str(sig.get("description") or sig.get("title") or ""),
                confidence=float(sig.get("confidence") or 0),
            )
        )
    opportunities.sort(key=lambda o: (-o.confidence, o.project_name))

    recommended_actions: List[ActionItem] = []
    for rec in sorted(
        recommendations,
        key=lambda r: (-int(r.get("impact_score") or 0), -float(r.get("priority_score") or 0)),
    ):
        rationale = rec.get("rationale") or {}
        metrics = rationale.get("supporting_metrics") or {}
        signal_ids = list(rec.get("source_signal_ids") or rationale.get("triggering_signals") or [])
        recommended_actions.append(
            ActionItem(
                recommendation_id=str(rec.get("recommendation_id") or ""),
                title=str(rec.get("title") or ""),
                description=str(rec.get("description") or ""),
                priority=str(rec.get("priority") or "medium"),
                impact_score=int(rec.get("impact_score") or 0),
                project_name=str(rec.get("project_name") or ""),
                why=str(rationale.get("business_rationale") or ""),
                reason=str(rec.get("description") or ""),
                signal_type=str(metrics.get("signal_type") or ""),
                source_signal_ids=signal_ids,
            )
        )

    projects_map: Dict[str, Dict[str, Any]] = {}
    for sig in signals:
        sev = sig.get("severity") or "info"
        if sev not in ATTENTION_SEVERITIES:
            continue
        name = str(sig.get("project_name") or sig.get("project_id") or "")
        bucket = projects_map.setdefault(
            name,
            {"summaries": [], "severities": [], "count": 0},
        )
        bucket["summaries"].append(str(sig.get("description") or sig.get("title") or ""))
        bucket["severities"].append(sev)
        bucket["count"] += 1

    projects_requiring_attention: List[ProjectAttentionItem] = []
    for name, bucket in sorted(projects_map.items()):
        severities = bucket["severities"]
        highest = min(severities, key=_severity_rank)
        projects_requiring_attention.append(
            ProjectAttentionItem(
                project_name=name,
                highest_severity=highest,
                signal_count=int(bucket["count"]),
                summaries=list(bucket["summaries"][:5]),
            )
        )

    result = {
        "top_risks": [r.model_dump() for r in top_risks[:8]],
        "opportunities": [o.model_dump() for o in opportunities[:8]],
        "recommended_actions": [a.model_dump() for a in recommended_actions[:10]],
        "projects_requiring_attention": [p.model_dump() for p in projects_requiring_attention],
    }
    result["executive_focus"] = build_executive_focus(
        result,
        briefing_input.data_completeness,
    ).model_dump()
    return result


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "warning": 1, "info": 2}.get(severity, 9)
