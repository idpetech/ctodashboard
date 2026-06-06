"""
Unified trial + subscription access state for CTO Lens.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.stripe_billing_service import billing_grants_write, billing_summary, get_billing_prefs
from services.trial_service import EXPIRING_DAYS, _iso_date, _parse_dt, DEFAULT_TRIAL_DAYS


def resolve_account_state(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Merge trial and Stripe billing into one access + display state."""
    prefs = user_data.get("preferences") or {}
    role = user_data.get("role", "user")
    billing = get_billing_prefs(prefs)
    billing_status = billing.get("billing_status", "trial")
    b_summary = billing_summary(user_data)

    if role == "admin":
        return {
            **b_summary,
            "trial_start_date": prefs.get("trial_start_date"),
            "trial_end_date": prefs.get("trial_end_date"),
            "trial_status": "paid",
            "days_remaining": None,
            "can_write": True,
            "banner": None,
        }

    if billing_status == "active":
        return {
            **b_summary,
            "trial_status": "paid",
            "days_remaining": None,
            "can_write": True,
            "banner": None,
        }

    if billing_status == "past_due":
        return {
            **b_summary,
            "trial_status": "expired",
            "days_remaining": 0,
            "can_write": False,
            "banner": {
                "level": "error",
                "message": "Your payment is past due. Update billing to restore access.",
            },
        }

    if billing_status == "canceled":
        return {
            **b_summary,
            "trial_status": "expired",
            "days_remaining": 0,
            "can_write": False,
            "banner": {
                "level": "error",
                "message": "Your subscription was canceled. Upgrade to continue.",
            },
        }

    if prefs.get("trial_status") == "paid" or prefs.get("plan") == "paid":
        return {**b_summary, "trial_status": "paid", "days_remaining": None, "can_write": True, "banner": None}

    legacy = prefs.get("trial") or {}
    start = _parse_dt(prefs.get("trial_start_date") or legacy.get("started_at") or user_data.get("created_at"))
    end = _parse_dt(prefs.get("trial_end_date") or legacy.get("expires_at"))
    if not end and start:
        days = int(legacy.get("trial_days") or DEFAULT_TRIAL_DAYS)
        from datetime import datetime, timedelta
        end = start + timedelta(days=days)

    from datetime import datetime
    now = datetime.utcnow()
    days_remaining = max(0, (end.date() - now.date()).days) if end else 0
    if end and end < now:
        trial_status = "expired"
    elif days_remaining <= EXPIRING_DAYS:
        trial_status = "expiring"
    else:
        trial_status = "active"

    banner = None
    if trial_status == "expired":
        banner = {"level": "error", "message": "Your trial has expired. Upgrade to continue."}
    elif trial_status == "expiring":
        day_word = "day" if days_remaining == 1 else "days"
        banner = {"level": "warning", "message": f"Your trial expires in {days_remaining} {day_word}."}

    can_write = trial_status in ("active", "expiring") or billing_grants_write(billing_status)

    return {
        **b_summary,
        "trial_start_date": _iso_date(start) if start else None,
        "trial_end_date": _iso_date(end) if end else None,
        "trial_status": trial_status,
        "days_remaining": days_remaining,
        "can_write": can_write,
        "banner": banner,
    }


def can_write(user_data: Optional[Dict[str, Any]]) -> bool:
    if not user_data:
        return False
    return resolve_account_state(user_data)["can_write"]
