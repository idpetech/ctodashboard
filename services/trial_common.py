"""Shared trial date helpers and constants (no access-policy logic)."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

EXPIRING_DAYS = int(os.getenv("TRIAL_EXPIRING_DAYS", "3"))
DEFAULT_TRIAL_DAYS = int(os.getenv("FREE_TRIAL_DAYS", "7"))


def parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except (TypeError, ValueError):
        return None


def iso_date(dt: datetime) -> str:
    return dt.isoformat()
