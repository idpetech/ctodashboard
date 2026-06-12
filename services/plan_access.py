"""
Subscription plan gates — Chapter 2 (Professional multi-portfolio).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from flask import jsonify

from services.portfolio_scope_service import DEFAULT_PORTFOLIO_ID
from services.stripe_billing_service import PLANS, get_billing_prefs

PROFESSIONAL_PLAN = "professional"
STARTER_PLAN = "starter"
UPGRADE_MESSAGE = (
    "Multi-portfolio features require the Professional plan ($149/mo). "
    "Upgrade in Profile → Billing."
)


def subscription_plan(user_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Active paid plan key (starter|professional) or None for trial/free."""
    if not user_data:
        return None
    if user_data.get("role") == "admin":
        return PROFESSIONAL_PLAN

    billing = get_billing_prefs(user_data.get("preferences") or {})
    if billing.get("billing_status") != "active":
        return None

    plan = (billing.get("plan") or "").strip().lower()
    if plan in PLANS:
        return plan
    return STARTER_PLAN if billing.get("stripe_subscription_id") else None


def can_use_multi_portfolio(user_data: Optional[Dict[str, Any]]) -> bool:
    """Professional (or admin): create portfolios, move assignments, portfolio briefings."""
    return subscription_plan(user_data) == PROFESSIONAL_PLAN


def portfolio_move_requires_upgrade(
    user_data: Optional[Dict[str, Any]], portfolio_id: Optional[str]
) -> bool:
    if not portfolio_id or portfolio_id == DEFAULT_PORTFOLIO_ID:
        return False
    return not can_use_multi_portfolio(user_data)


def multi_portfolio_denied_response() -> Tuple[Any, int]:
    return (
        jsonify(
            {
                "error": "upgrade_required",
                "message": UPGRADE_MESSAGE,
                "required_plan": PROFESSIONAL_PLAN,
                "upgrade_plan": PROFESSIONAL_PLAN,
            }
        ),
        403,
    )


def plan_access_fields(user_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    plan = subscription_plan(user_data)
    return {
        "subscription_plan": plan,
        "can_use_multi_portfolio": can_use_multi_portfolio(user_data),
        "multi_portfolio_upgrade_plan": PROFESSIONAL_PLAN,
    }
