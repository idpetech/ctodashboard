"""Tests for subscription plan gates (Chapter 2)."""

from services.plan_access import (
    PROFESSIONAL_PLAN,
    STARTER_PLAN,
    can_use_multi_portfolio,
    portfolio_move_requires_upgrade,
    subscription_plan,
)


def _user(role="user", billing=None, preferences=None):
    prefs = dict(preferences or {})
    if billing is not None:
        prefs["billing"] = billing
    return {"role": role, "preferences": prefs}


def test_admin_gets_professional_plan():
    assert subscription_plan(_user(role="admin")) == PROFESSIONAL_PLAN
    assert can_use_multi_portfolio(_user(role="admin")) is True


def test_trial_user_has_no_paid_plan():
    user = _user(preferences={"trial_status": "active"})
    assert subscription_plan(user) is None
    assert can_use_multi_portfolio(user) is False


def test_starter_active_cannot_use_multi_portfolio():
    user = _user(
        billing={
            "billing_status": "active",
            "plan": STARTER_PLAN,
            "stripe_subscription_id": "sub_123",
        }
    )
    assert subscription_plan(user) == STARTER_PLAN
    assert can_use_multi_portfolio(user) is False


def test_professional_active_can_use_multi_portfolio():
    user = _user(
        billing={
            "billing_status": "active",
            "plan": PROFESSIONAL_PLAN,
            "stripe_subscription_id": "sub_pro",
        }
    )
    assert subscription_plan(user) == PROFESSIONAL_PLAN
    assert can_use_multi_portfolio(user) is True


def test_default_portfolio_move_never_requires_upgrade():
    user = _user(billing={"billing_status": "active", "plan": STARTER_PLAN})
    assert portfolio_move_requires_upgrade(user, None) is False
    assert portfolio_move_requires_upgrade(user, "default") is False


def test_non_default_portfolio_move_requires_upgrade_for_starter():
    user = _user(
        billing={
            "billing_status": "active",
            "plan": STARTER_PLAN,
            "stripe_subscription_id": "sub_123",
        }
    )
    assert portfolio_move_requires_upgrade(user, "acme") is True


def test_non_default_portfolio_move_allowed_for_professional():
    user = _user(
        billing={
            "billing_status": "active",
            "plan": PROFESSIONAL_PLAN,
            "stripe_subscription_id": "sub_pro",
        }
    )
    assert portfolio_move_requires_upgrade(user, "acme") is False
