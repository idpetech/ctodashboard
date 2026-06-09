"""Production baseline smoke tests — run on master in CI."""

from __future__ import annotations

import json
from pathlib import Path


def test_flask_app_imports():
    from integrated_dashboard import app

    assert app is not None
    assert app.name == "integrated_dashboard"


def test_starter_only_checkout_plans():
    from services.stripe_billing_service import CHECKOUT_PLANS, PLANS

    assert CHECKOUT_PLANS == ("starter",)
    assert "professional" in PLANS  # legacy subscribers only


def test_homepage_pricing_shows_starter_only():
    path = Path(__file__).resolve().parents[1] / "config" / "homepage_content.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    plans = payload["pricing"]["plans"]
    names = [p["name"] for p in plans]
    assert len(plans) == 2
    assert "Starter" in names
    assert "Scale" not in names
