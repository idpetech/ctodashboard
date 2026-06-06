"""
Founder-friendly language layer for briefing outputs.

Does not change scoring, severity, or detection logic — only rewrites text for executives.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _frame(observation: str, impact: str, action: str) -> Dict[str, str]:
    return {
        "observation": observation.strip(),
        "business_impact": impact.strip(),
        "recommended_action": action.strip(),
        "summary": f"{observation.strip()} {impact.strip()} {action.strip()}".strip(),
    }


def translate_attention_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Rewrite attention_center item message for founders."""
    out = dict(item)
    item_type = item.get("type", "")
    name = item.get("name") or item.get("assignment_id") or "This assignment"
    connector = ""
    raw = item.get("message") or ""

    if item_type == "connector_needs_credentials":
        for part in ("github", "jira", "aws", "railway", "openai"):
            if part in raw.lower():
                connector = part.upper() if part != "github" else "GitHub"
                break
        connector = connector or "A connected system"
        framing = _frame(
            f"{connector} is enabled for {name}, but reporting data is not flowing yet.",
            "Delivery and spend visibility for this project is incomplete, "
            "which increases the chance that issues surface late.",
            f"Complete {connector} credentials for {name} so daily briefings reflect live project health.",
        )
    elif item_type == "budget_overrun":
        framing = _frame(
            f"{name} is running above its approved monthly budget.",
            "Sustained overspend can shorten runway and force reactive budget decisions.",
            f"Review cost drivers and staffing with the {name} lead within the next week.",
        )
    elif item_type == "missing_target":
        framing = _frame(
            f"{name} does not have a monthly budget target configured.",
            "Without a target, overspend may go unnoticed until later in the quarter.",
            f"Set a target monthly burn for {name} to enable proactive budget tracking.",
        )
    else:
        framing = _frame(
            raw or f"{name} needs review.",
            "Unresolved items in this category can slow portfolio-level decision making.",
            "Review this item with your technical lead and agree on a next step.",
        )

    out["executive_framing"] = framing
    out["message"] = framing["summary"]
    return out


def translate_risk_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Rewrite risk signal detail for founders."""
    out = dict(signal)
    sig_type = signal.get("type", "")
    title = signal.get("title") or "Portfolio"
    detail = signal.get("detail") or ""

    if sig_type == "connector_gap":
        framing = _frame(
            "Portfolio reporting accuracy is reduced because several connected systems "
            "are not fully configured.",
            "Leadership may be making decisions on incomplete delivery and cost signals.",
            "Finish connector setup for all enabled integrations to restore full visibility.",
        )
    elif sig_type == "connector_needs_credentials" or "no credentials" in detail.lower():
        framing = _frame(
            "Engineering delivery visibility is limited because source control or delivery "
            "data is not connected.",
            "This increases the risk that delivery issues are discovered late.",
            "Connect GitHub or Jira with read-only credentials to restore early warning signals.",
        )
    elif sig_type == "overloaded_team":
        framing = _frame(
            f"{title} carries a large team relative to its scope.",
            "Large teams without clear workstream splits often hide delivery bottlenecks and excess burn.",
            f"Evaluate whether {title} should be split into smaller, measurable workstreams.",
        )
    elif sig_type == "high_burn_per_head":
        framing = _frame(
            f"{title} has a high monthly cost relative to team size.",
            "Elevated spend per person may indicate staffing inefficiency or scope creep.",
            f"Audit roles and contractors on {title} and align spend to planned outcomes.",
        )
    elif sig_type == "missing_budget_targets":
        framing = _frame(
            "Some active projects are missing monthly budget targets.",
            "Budget risk is harder to spot early when targets are not defined.",
            "Add target monthly burn for each active assignment in portfolio settings.",
        )
    elif sig_type == "budget_overrun" or "over target" in detail.lower():
        framing = _frame(
            f"{title} is spending above its planned monthly budget.",
            "Continued variance can compress runway and create founder-level surprises.",
            f"Schedule a budget review for {title} and reset targets if scope has changed.",
        )
    else:
        framing = _frame(
            detail or f"{title} has an elevated risk signal.",
            "Unaddressed risks in this area can affect delivery predictability and cost control.",
            "Discuss this signal with your fractional CTO or project lead and assign an owner.",
        )

    out["executive_framing"] = framing
    out["detail"] = framing["summary"]
    return out


def translate_opportunity_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Rewrite opportunity signal detail for founders."""
    out = dict(signal)
    sig_type = signal.get("type", "")
    title = signal.get("title") or "Portfolio"
    detail = signal.get("detail") or ""

    if sig_type == "budget_headroom":
        framing = _frame(
            f"{title} is tracking below its monthly budget target.",
            "Unused budget may fund acceleration elsewhere or improve overall portfolio efficiency.",
            f"Decide whether to reinvest the headroom on {title} or reallocate to higher-priority work.",
        )
    elif sig_type == "automation_candidate":
        framing = _frame(
            f"{title} is not yet connected to automated delivery or cost signals.",
            "Manual status updates slow executive visibility and increase reporting overhead.",
            f"Enable GitHub and Jira connectors for {title} to automate health monitoring.",
        )
    elif sig_type == "delivery_visibility":
        framing = _frame(
            f"{title} lacks engineering delivery metrics in the portfolio view.",
            "Without delivery data, schedule slips may only appear near release dates.",
            f"Add GitHub or Jira integration for {title} to surface delivery risk earlier.",
        )
    elif sig_type == "full_connector_coverage":
        framing = _frame(
            "All enabled data connectors are configured and reporting.",
            "This is a strong baseline for reliable executive briefings.",
            "Maintain connector health after credential rotations or team changes.",
        )
    elif sig_type == "portfolio_optimization":
        framing = _frame(
            "The portfolio has enough active projects to benefit from a cross-project review.",
            "Periodic burn and staffing reviews often reveal consolidation or reallocation wins.",
            "Book a 30-minute portfolio review to compare burn, team size, and delivery signals.",
        )
    else:
        framing = _frame(
            detail or f"An improvement opportunity was identified for {title}.",
            "Acting on portfolio opportunities can improve capital efficiency and delivery speed.",
            "Review this recommendation with your CTO advisor and pick one action for this month.",
        )

    out["executive_framing"] = framing
    out["detail"] = framing["summary"]
    return out


def portfolio_status_label(
    health_band: str,
    risk_signals: List[Dict[str, Any]],
) -> str:
    """Top-level status for report landing."""
    crit = any(r.get("severity") == "critical" for r in risk_signals)
    warn = any(r.get("severity") == "warning" for r in risk_signals)
    if crit or health_band == "critical":
        return "Critical"
    if warn or health_band in ("at_risk", "needs_attention"):
        return "Needs Attention"
    return "Healthy"


def translate_health_explanation(components: Dict[str, Any]) -> str:
    parts = []
    if components.get("financial") is not None:
        parts.append(
            f"Financial discipline is rated {components['financial']}/100 based on budget adherence."
        )
    if components.get("connector") is not None:
        parts.append(
            f"Data connectivity is rated {components['connector']}/100 based on configured integrations."
        )
    if components.get("delivery") is not None:
        parts.append(
            f"Delivery visibility is rated {components['delivery']}/100 based on engineering signals."
        )
    return " ".join(parts) if parts else "Score reflects budget, connector, and delivery signals."


def enrich_briefing_for_executives(
    briefing: Dict[str, Any],
    attention: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply founder-friendly language to a briefing dict in place."""
    out = dict(briefing)
    out["risk_signals"] = [
        translate_risk_signal(s) for s in (briefing.get("risk_signals") or [])
    ]
    out["opportunity_signals"] = [
        translate_opportunity_signal(s) for s in (briefing.get("opportunity_signals") or [])
    ]

    attention_items = []
    if attention:
        attention_items = [
            translate_attention_item(i) for i in (attention.get("items") or [])
        ]
        out["founder_attention_items"] = attention_items

    health = out.get("system_health_score") or {}
    comps = health.get("components") or {}
    health = dict(health)
    health["explanation"] = translate_health_explanation(comps)
    out["system_health_score"] = health

    out["portfolio_status"] = portfolio_status_label(
        health.get("band", "healthy"),
        out["risk_signals"],
    )

    eb = dict(out.get("executive_briefing") or {})
    if eb.get("headline") == "Portfolio needs attention":
        eb["headline"] = "Your portfolio needs leadership attention"
    elif eb.get("headline") == "Portfolio has warnings":
        eb["headline"] = "Your portfolio has items to review"
    elif eb.get("headline") == "Portfolio is stable":
        eb["headline"] = "Your portfolio is in a stable position"
    out["executive_briefing"] = eb

    narrative = out.get("cto_narrative") or ""
    if "deterministically" in narrative:
        narrative = narrative.replace(
            "This briefing is computed deterministically from your current data — "
            "refresh after imports or connector updates for the latest picture.",
            "This briefing reflects your latest portfolio data. "
            "Refresh after imports or connector updates for the most current view.",
        )
    out["cto_narrative"] = narrative
    return out
