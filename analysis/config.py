"""Runtime configuration for Analysis Layer v1."""

from __future__ import annotations

import os


def is_analysis_enabled() -> bool:
    return os.getenv("ENABLE_ANALYSIS_LAYER", "false").lower() == "true"
