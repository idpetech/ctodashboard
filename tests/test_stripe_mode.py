"""Stripe test/live key safety checks."""

import os

import pytest

from services.stripe_billing_service import (
    assert_stripe_key_matches_deployment,
    stripe_config_summary,
    stripe_mode,
)


@pytest.fixture(autouse=True)
def _clear_stripe_env(monkeypatch):
    for key in (
        "STRIPE_SECRET_KEY",
        "ENVIRONMENT",
        "APP_ENV",
        "RAILWAY_ENVIRONMENT",
        "STRIPE_ALLOW_LIVE",
        "STRIPE_ALLOW_TEST",
        "ENABLE_STRIPE_BILLING",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ENABLE_STRIPE_BILLING", "true")


def test_stripe_mode_detects_test_key():
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_abc"
    assert stripe_mode() == "test"


def test_live_key_blocked_on_staging(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    with pytest.raises(RuntimeError, match="live key"):
        assert_stripe_key_matches_deployment()


def test_test_key_blocked_on_production(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="test key"):
        assert_stripe_key_matches_deployment()


def test_live_key_allowed_on_production(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert_stripe_key_matches_deployment() is None


def test_config_summary_flags_mismatch(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    summary = stripe_config_summary()
    assert summary["stripe_mode"] == "live"
    assert summary["deployment_tier"] == "non-production"
    assert summary["stripe_key_mismatch"] is True
