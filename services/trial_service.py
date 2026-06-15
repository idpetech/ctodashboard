"""
MVP trial management — pilot users and free trials before commercial launch.

Trial fields live in users.preferences JSON (no schema migration).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from services.trial_common import (
    DEFAULT_TRIAL_DAYS,
    EXPIRING_DAYS,
    iso_date,
    parse_dt,
)

# Backward-compatible aliases for existing imports.
_parse_dt = parse_dt
_iso_date = iso_date


def normalize_trial_fields(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve trial_start_date, trial_end_date, trial_status from preferences.
    Does not mutate user_data.
    """
    prefs = user_data.get("preferences") or {}
    role = user_data.get("role", "user")

    if role == "admin" or prefs.get("trial_status") == "paid" or prefs.get("plan") == "paid":
        return {
            "trial_start_date": prefs.get("trial_start_date"),
            "trial_end_date": prefs.get("trial_end_date"),
            "trial_status": "paid",
            "days_remaining": None,
            "can_write": True,
            "banner": None,
        }

    legacy = prefs.get("trial") or {}
    start = parse_dt(
        prefs.get("trial_start_date") or legacy.get("started_at") or user_data.get("created_at")
    )
    end = parse_dt(prefs.get("trial_end_date") or legacy.get("expires_at"))

    if not end and start:
        days = int(legacy.get("trial_days") or DEFAULT_TRIAL_DAYS)
        end = start + timedelta(days=days)
    if not start:
        start = datetime.utcnow()
    if not end:
        end = start + timedelta(days=DEFAULT_TRIAL_DAYS)

    now = datetime.utcnow()
    days_remaining = max(0, (end.date() - now.date()).days)
    if end < now:
        status = "expired"
    elif days_remaining <= EXPIRING_DAYS:
        status = "expiring"
    else:
        status = "active"

    banner = None
    if status == "expired":
        banner = {
            "level": "error",
            "message": "Your trial has expired. Upgrade to continue.",
        }
    elif status == "expiring":
        day_word = "day" if days_remaining == 1 else "days"
        banner = {
            "level": "warning",
            "message": f"Your trial expires in {days_remaining} {day_word}.",
        }

    return {
        "trial_start_date": iso_date(start),
        "trial_end_date": iso_date(end),
        "trial_status": status,
        "days_remaining": days_remaining if status != "paid" else None,
        "can_write": status in ("active", "expiring"),
        "banner": banner,
    }


def trial_prefs_for_new_user(
    start: Optional[datetime] = None, days: Optional[int] = None
) -> Dict[str, Any]:
    """Preferences fragment for a newly registered trial user."""
    _start = start or datetime.utcnow()
    _days = days if days is not None else DEFAULT_TRIAL_DAYS
    _end = _start + timedelta(days=_days)
    return {
        "plan": "free",
        "trial_start_date": iso_date(_start),
        "trial_end_date": iso_date(_end),
        "trial_status": "active",
        "trial": {
            "plan": "free",
            "trial_days": _days,
            "started_at": iso_date(_start),
            "expires_at": iso_date(_end),
        },
    }


def trial_write_denied_response():
    from flask import jsonify

    return jsonify(
        {
            "error": "trial_expired",
            "message": "Your trial has expired. Upgrade to continue.",
            "trial_status": "expired",
        }
    ), 403


def admin_trial_summary(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Trial + billing fields for admin user list."""
    from services.user_access import resolve_account_state

    info = resolve_account_state(user_data)
    return {
        "email": user_data.get("email"),
        "display_name": user_data.get("display_name"),
        "role": user_data.get("role"),
        "trial_start_date": info.get("trial_start_date"),
        "trial_end_date": info.get("trial_end_date"),
        "trial_status": info.get("trial_status"),
        "days_remaining": info.get("days_remaining"),
        "plan": info.get("plan_name"),
        "billing_status": info.get("billing_status"),
    }
