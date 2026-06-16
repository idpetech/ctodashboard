"""Runtime configuration for Analysis Layer v1."""

from __future__ import annotations

import os


def is_analysis_enabled() -> bool:
    return os.getenv("ENABLE_ANALYSIS_LAYER", "false").lower() == "true"


def is_analysis_strict_mode() -> bool:
    """When true, use uncalibrated Analysis Layer v1 rules and scoring."""
    return os.getenv("ANALYSIS_STRICT_MODE", "false").lower() == "true"
