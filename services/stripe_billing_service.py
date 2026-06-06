"""
Stripe Subscription Billing MVP — Checkout, portal, webhooks.

Stores stripe_customer_id and stripe_subscription_id in users.preferences.billing.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)

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

_STRIPE_STATUS_MAP = {
    "active": "active",
    "trialing": "trial",
    "past_due": "past_due",
    "canceled": "canceled",
    "unpaid": "past_due",
    "incomplete": "trial",
    "incomplete_expired": "canceled",
    "paused": "canceled",
}


def is_billing_enabled() -> bool:
    return (
        os.getenv("ENABLE_STRIPE_BILLING", os.getenv("ENABLE_BILLING", "false")).lower()
        == "true"
    )


def _stripe():
    import stripe

    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = key
    return stripe


def _plan_env_value(plan: str) -> str:
    """Price ID (price_...) or product ID (prod_...) from env."""
    if plan not in PLANS:
        raise ValueError(f"Unknown plan: {plan}")
    meta = PLANS[plan]
    return (
        os.getenv(meta["price_env"], "").strip()
        or os.getenv(meta["product_env"], "").strip()
    )


def _stripe_field(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from a Stripe object or plain dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        val = obj[key]
    except (KeyError, TypeError):
        val = getattr(obj, key, default)
    return default if val is None and default is not None else val


def _price_id_from_product(product_id: str) -> str:
    """Resolve the default active recurring price for a Stripe product."""
    stripe = _stripe()
    prices = stripe.Price.list(product=product_id, active=True, limit=10)
    recurring = [p for p in prices.data if getattr(p, "recurring", None)]
    if not recurring:
        raise RuntimeError(f"No active recurring price found for product {product_id}")
    return recurring[0].id


def _price_id(plan: str) -> str:
    raw = _plan_env_value(plan)
    if not raw:
        meta = PLANS[plan]
        raise RuntimeError(
            f"Set {meta['price_env']} (price_...) or {meta['product_env']} (prod_...)"
        )
    if raw.startswith("price_"):
        return raw
    if raw.startswith("prod_"):
        return _price_id_from_product(raw)
    raise RuntimeError(f"Invalid Stripe ID for {plan}: expected price_... or prod_..., got {raw}")


def _plan_from_price_id(price_id: Optional[str]) -> Optional[str]:
    if not price_id:
        return None
    for key in PLANS:
        env_val = _plan_env_value(key)
        if not env_val:
            continue
        if env_val == price_id:
            return key
        if env_val.startswith("prod_"):
            try:
                if _price_id_from_product(env_val) == price_id:
                    return key
            except RuntimeError:
                continue
    return None


def get_billing_prefs(preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    prefs = preferences or {}
    billing = dict(prefs.get("billing") or {})
    if not billing.get("billing_status"):
        if prefs.get("trial_status") == "paid" or prefs.get("plan") == "paid":
            billing.setdefault("billing_status", "active")
        else:
            billing.setdefault("billing_status", "trial")
    return billing


def billing_summary(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Public billing info for dashboard."""
    prefs = user_data.get("preferences") or {}
    billing = get_billing_prefs(prefs)
    plan_key = billing.get("plan")
    plan_meta = PLANS.get(plan_key) if plan_key else None
    return {
        "enabled": is_billing_enabled(),
        "plan": plan_key,
        "plan_name": plan_meta["name"] if plan_meta else (plan_key or "Trial"),
        "plan_amount": plan_meta["amount"] if plan_meta else None,
        "billing_status": billing.get("billing_status", "trial"),
        "renewal_date": billing.get("renewal_date"),
        "stripe_customer_id": billing.get("stripe_customer_id"),
        "has_subscription": bool(billing.get("stripe_subscription_id")),
        "can_manage_billing": bool(billing.get("stripe_customer_id")),
        "available_plans": [
            {"id": k, "name": v["name"], "amount": v["amount"]}
            for k, v in PLANS.items()
        ],
    }


def billing_grants_write(billing_status: str) -> bool:
    return billing_status in ("active", "trial")


def create_checkout_session(
    user_email: str,
    plan: str,
    *,
    success_url: str,
    cancel_url: str,
    existing_customer_id: Optional[str] = None,
) -> Dict[str, str]:
    stripe = _stripe()
    price_id = _price_id(plan)

    params: Dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": user_email,
        "metadata": {"user_email": user_email, "plan": plan},
        "subscription_data": {"metadata": {"user_email": user_email, "plan": plan}},
    }
    if existing_customer_id:
        params["customer"] = existing_customer_id
    else:
        params["customer_email"] = user_email

    session = stripe.checkout.Session.create(**params)
    return {"checkout_url": session.url, "session_id": session.id}


def confirm_checkout_session(session_id: str, user_email: str) -> Dict[str, Any]:
    """
    Sync billing after Checkout redirect — local-dev fallback when webhooks
    are unavailable (no Stripe CLI / public tunnel).
    """
    stripe = _stripe()
    session = stripe.checkout.Session.retrieve(session_id)
    payment_status = _stripe_field(session, "payment_status")
    session_status = _stripe_field(session, "status")
    if payment_status != "paid" and session_status != "complete":
        raise ValueError("Checkout is not complete yet")

    metadata = _stripe_field(session, "metadata") or {}
    email = _stripe_field(session, "client_reference_id") or _stripe_field(metadata, "user_email")
    if email != user_email:
        raise ValueError("Checkout session does not belong to this user")

    _handle_checkout_completed(session)
    return {"confirmed": True, "session_id": session_id}


def create_portal_session(customer_id: str, *, return_url: str) -> Dict[str, str]:
    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return {"portal_url": session.url}


def handle_webhook(payload: bytes, sig_header: str) -> Dict[str, Any]:
    stripe = _stripe()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")

    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    etype = event["type"]
    data = event["data"]["object"]

    if etype == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif etype in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        _sync_subscription(data)
    elif etype == "customer.subscription.deleted":
        _sync_subscription(data, deleted=True)
    else:
        logger.debug("Unhandled Stripe event: %s", etype)

    return {"received": True, "type": etype}


def _handle_checkout_completed(session: Dict[str, Any]) -> None:
    metadata = _stripe_field(session, "metadata") or {}
    email = _stripe_field(session, "client_reference_id") or _stripe_field(metadata, "user_email")
    customer_id = _stripe_field(session, "customer")
    subscription_id = _stripe_field(session, "subscription")
    if not email:
        logger.warning("checkout.session.completed without user email")
        return

    billing: Dict[str, Any] = {
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "billing_status": "active",
        "updated_at": datetime.utcnow().isoformat(),
    }
    plan = _stripe_field(metadata, "plan")
    if plan:
        billing["plan"] = plan

    _persist_billing(email, billing)

    if subscription_id:
        stripe = _stripe()
        sub = stripe.Subscription.retrieve(subscription_id)
        _sync_subscription(sub)


def _sync_subscription(subscription: Dict[str, Any], *, deleted: bool = False) -> None:
    metadata = _stripe_field(subscription, "metadata") or {}
    email = _stripe_field(metadata, "user_email")
    customer_id = _stripe_field(subscription, "customer")
    sub_id = _stripe_field(subscription, "id")

    if not email and customer_id:
        email = _email_for_customer(customer_id)

    if not email:
        logger.warning("subscription sync missing user email for %s", sub_id)
        return

    stripe_status = _stripe_field(subscription, "status", "canceled")
    billing_status = "canceled" if deleted else _STRIPE_STATUS_MAP.get(stripe_status, "canceled")

    items_container = _stripe_field(subscription, "items") or {}
    items = _stripe_field(items_container, "data") or []
    price_id = None
    if items:
        price_obj = _stripe_field(items[0], "price") or {}
        price_id = _stripe_field(price_obj, "id")

    plan = _stripe_field(metadata, "plan") or _plan_from_price_id(price_id)
    renewal = _stripe_field(subscription, "current_period_end")
    renewal_date = (
        datetime.utcfromtimestamp(renewal).isoformat() if renewal else None
    )

    billing: Dict[str, Any] = {
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": sub_id,
        "billing_status": billing_status,
        "renewal_date": renewal_date,
        "stripe_price_id": price_id,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if plan:
        billing["plan"] = plan

    _persist_billing(email, billing)


def _email_for_customer(customer_id: str) -> Optional[str]:
    from services.security.secure_database import secure_db

    users = secure_db.list_all_users() or []
    for row in users:
        full = secure_db.get_user_credentials(row.get("email"))
        if not full:
            continue
        billing = get_billing_prefs(full.get("preferences"))
        if billing.get("stripe_customer_id") == customer_id:
            return full.get("email")
    return None


def _persist_billing(email: str, billing_update: Dict[str, Any]) -> None:
    from services.security.secure_database import secure_db

    user = secure_db.get_user_credentials(email)
    if not user:
        logger.error("Cannot persist billing — user not found: %s", email)
        return

    prefs = user.get("preferences") or {}
    billing = dict(prefs.get("billing") or {})
    billing.update({k: v for k, v in billing_update.items() if v is not None})
    prefs["billing"] = billing

    if billing.get("billing_status") == "active":
        prefs["trial_status"] = "paid"
        prefs["plan"] = billing.get("plan") or prefs.get("plan")

    user["preferences"] = prefs
    audit = {"user_email": email, "ip_address": "stripe_webhook", "user_agent": "stripe"}
    secure_db.store_user_credentials(email, user, audit)
    logger.info("Billing updated for %s: status=%s plan=%s", email, billing.get("billing_status"), billing.get("plan"))
