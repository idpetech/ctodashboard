#!/usr/bin/env python3
"""Apply canonical ctodashboard schema via secure_db (requires DATABASE_URL)."""
import os
import sys

os.environ.setdefault("ENABLE_DB_AUTO_INIT", "true")

from services.security.secure_database import secure_db


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
