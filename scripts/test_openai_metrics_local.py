#!/usr/bin/env python3
"""Local OpenAI metrics diagnostic — run before deploying connector changes."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_dotenv_local() -> None:
    env_path = ROOT / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_dotenv_local()

    api_key = os.getenv("OPENAI_API_KEY", "")
    admin_key = os.getenv("OPENAI_ADMIN_API_KEY", "")
    org_id = os.getenv("OPENAI_ORG_ID") or os.getenv("OPENAI_ORGANIZATION") or ""

    print("=== OpenAI local metrics diagnostic ===")
    print(f"OPENAI_API_KEY set: {bool(api_key)}")
    print(f"OPENAI_ADMIN_API_KEY set: {bool(admin_key)}")
    print(f"OPENAI_ORG_ID set: {bool(org_id)}")
    if org_id:
        print(f"Organization ID: {org_id[:12]}...")
    print()

    if not api_key and not admin_key:
        print("ERROR: Set OPENAI_API_KEY and/or OPENAI_ADMIN_API_KEY in .env.local or env.")
        return 1

    from connectors.openai.connector import OpenAIConnector
    from connectors.openai.validator import OpenAIValidator

    creds = {
        "openai_api_key": api_key,
        "openai_admin_api_key": admin_key,
        "openai_org_id": org_id,
    }

    print("--- Credential validation (models endpoint) ---")
    validation = OpenAIValidator.validate_credentials(creds)
    print(json.dumps({k: v for k, v in validation.items() if k != "sample_models"}, indent=2))
    print()

    connector = OpenAIConnector()
    connector.credentials = creds

    print("--- Raw usage API probe ---")
    usage_data = connector._get_usage_data()
    if usage_data.get("usage_access_limited"):
        print("usage_access_limited: true")
        print("message:", usage_data.get("message"))
        print("recommendation:", usage_data.get("recommendation"))
        if usage_data.get("api_errors"):
            print("api_errors:", json.dumps(usage_data.get("api_errors"), indent=2))
    else:
        buckets = len((usage_data.get("data") or []))
        rows = connector._flatten_org_buckets(usage_data)
        print(f"Connected: {buckets} day-buckets, {len(rows)} usage rows parsed")
        if rows[:1]:
            print("sample row:", json.dumps(rows[0], indent=2))
    print()

    print("--- Full get_metrics() output (summary) ---")
    metrics = connector.get_metrics({})
    summary = {
        "status": metrics.get("status"),
        "account_type": metrics.get("account_type"),
        "usage_notice": metrics.get("usage_notice"),
        "recommendation": metrics.get("recommendation"),
        "usage_this_month": metrics.get("usage_this_month"),
        "models_used": metrics.get("models_used"),
        "raw_data_points": metrics.get("raw_data_points"),
        "cto_insights": metrics.get("cto_insights"),
    }
    print(json.dumps(summary, indent=2))
    print()

    usage = metrics.get("usage_this_month") or {}
    if metrics.get("status") == "usage_unavailable":
        print("RESULT: Usage API not available with current keys — see message above.")
        print("Fix: add Admin API key with Usage read + org ID, then re-run this script.")
        return 2
    if (usage.get("total_tokens") or 0) == 0 and (usage.get("estimated_cost") or 0) == 0:
        print("RESULT: Connected but zero usage for current month (may be normal if no API calls).")
        return 0
    print("RESULT: Metrics look good — safe to test in dashboard Load All Metrics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
