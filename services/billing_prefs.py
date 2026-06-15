"""Shared billing preference helpers and plan registry (no Stripe API calls)."""

from __future__ import annotations

from typing import Any, Dict, Optional

PLANS: Dict[str, Dict[str, Any]] = {
    "starter": {
        "name": "Starter",
        "amount": 49,
        "price_env": "STRIPE_PRICE_STARTER",
        "product_env": "STRIPE_PRODUCT_STARTER",
    },
    "professional": {
        "name": "Professional",
        "amount": 149,
        "price_env": "STRIPE_PRICE_PROFESSIONAL",
        "product_env": "STRIPE_PRODUCT_PROFESSIONAL",
    },
}


def get_billing_prefs(preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    prefs = preferences or {}
    billing = dict(prefs.get("billing") or {})
    if not billing.get("billing_status"):
        if prefs.get("trial_status") == "paid" or prefs.get("plan") == "paid":
            billing.setdefault("billing_status", "active")
        else:
            billing.setdefault("billing_status", "trial")
    return billing


def billing_grants_write(billing_status: str) -> bool:
    return billing_status in ("active", "trial")
