"""Runtime configuration for CTO Report Generator v1."""

from __future__ import annotations

import os


def is_reporting_enabled() -> bool:
    return os.getenv("ENABLE_REPORTING_LAYER", "false").lower() == "true"
