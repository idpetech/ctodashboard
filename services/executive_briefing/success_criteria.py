"""
Deterministic success criteria — answers the five executive questions.

Computed from signals and recommendations only. Never from the LLM.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.executive_briefing.schema import ExecutiveFocus


def build_executive_focus(
    pre_sorted: Dict[str, Any],
    data_completeness: Dict[str, Any],
) -> ExecutiveFocus:
    """
    Answer:
    1. What is the biggest risk?
    2. What is the biggest opportunity?
    3. What should I do first?
    4. Why is that recommendation being made?
    5. How confident is CTOLens in the recommendation?
    """
    risks: List[Dict[str, Any]] = pre_sorted.get("top_risks") or []
    opportunities: List[Dict[str, Any]] = pre_sorted.get("opportunities") or []
    actions: List[Dict[str, Any]] = pre_sorted.get("recommended_actions") or []

    if risks:
        top = risks[0]
        biggest_risk = (
            f"{top.get('project_name', 'Portfolio')}: {top.get('summary', '')} "
            f"({top.get('signal_type', 'signal')}, {top.get('severity', 'warning')})"
        ).strip()
    else:
        biggest_risk = "No critical or warning risks identified in current signals."

    if opportunities:
        top = opportunities[0]
        biggest_opportunity = (
            f"{top.get('project_name', 'Portfolio')}: {top.get('summary', '')} "
            f"({top.get('signal_type', 'signal')})"
        ).strip()
    else:
        biggest_opportunity = "No material opportunities identified in current signals."

    top_action = actions[0] if actions else None
    if top_action:
        do_first = f"{top_action.get('title', 'Action')} — {top_action.get('project_name', 'Portfolio')}"
        why_first = _compose_why(top_action)
        source_rec_id = str(top_action.get("recommendation_id") or "")
        source_signal_ids = list(top_action.get("source_signal_ids") or [])
    else:
        do_first = "Review portfolio health; no ranked recommendations from current signals."
        why_first = "No recommendation rules fired on the supplied signal set."
        source_rec_id = None
        source_signal_ids = []

    confidence_summary = _confidence_for_focus(data_completeness, top_action)

    return ExecutiveFocus(
        biggest_risk=biggest_risk,
        biggest_opportunity=biggest_opportunity,
        do_first=do_first,
        why_first_action=why_first,
        confidence_summary=confidence_summary,
        source_recommendation_id=source_rec_id or None,
        source_signal_ids=source_signal_ids,
    )


def _compose_why(action: Dict[str, Any]) -> str:
    parts: List[str] = []
    why = (action.get("why") or "").strip()
    reason = (action.get("reason") or action.get("description") or "").strip()
    signal_type = (action.get("signal_type") or "").strip()
    signal_ids = action.get("source_signal_ids") or []

    if why:
        parts.append(why)
    if reason and reason not in why:
        parts.append(reason)
    if signal_type:
        parts.append(f"Triggered by signal {signal_type}.")
    if signal_ids:
        parts.append(f"Source: {', '.join(str(s) for s in signal_ids[:3])}.")
    return " ".join(parts) if parts else "Derived from deterministic recommendation rules."


def _confidence_for_focus(
    completeness: Dict[str, Any],
    top_action: Optional[Dict[str, Any]],
) -> str:
    level = completeness.get("overall_level") or "medium"
    readiness = completeness.get("connector_readiness_pct")
    parts = [f"Overall data confidence is {level}."]
    if readiness is not None:
        parts.append(f"Connector readiness {readiness}%.")
    if top_action:
        parts.append(
            f"Top action ranked by impact score {top_action.get('impact_score', 0)} "
            f"and priority {top_action.get('priority', 'medium')}."
        )
    if level == "low":
        parts.append("Treat the ranked action as directional until data coverage improves.")
    return " ".join(parts)
