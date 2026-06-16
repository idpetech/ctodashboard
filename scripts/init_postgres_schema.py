#!/usr/bin/env python3
"""Apply canonical ctodashboard schema via secure_db (requires DATABASE_URL)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()
if not os.getenv("RAILWAY_ENVIRONMENT"):
    load_dotenv(ROOT / ".env.local", override=True)

os.environ.setdefault("ENABLE_DB_AUTO_INIT", "true")

# ruff: noqa: E402
from services.security.db_system import secure_db


def main() -> int:
    health = secure_db.health_check()
    if not health.get("database_connected"):
        print("Schema init failed:", health.get("error", health))
        return 1
    print(
        f"OK schema={health.get('schema')} version={health.get('schema_version')} "
        f"users={health.get('statistics', {}).get('users', 0)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
