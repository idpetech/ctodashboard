"""
Load recommendation catalog and ranking weights from JSON.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

_DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "recommendation_catalog.json"
)

DEFAULT_SEVERITY_WEIGHTS = {
    "critical": 3.0,
    "warning": 2.0,
    "info": 1.0,
}

DEFAULT_PRIORITY_BANDS = {
    "high": 15.0,
    "medium": 8.0,
}


def load_recommendation_catalog(
    catalog_path: str | Path | None = None,
) -> Dict[str, Any]:
    path = Path(catalog_path or os.getenv("RECOMMENDATION_CATALOG_PATH", _DEFAULT_CATALOG_PATH))
    if not path.is_file():
        raise FileNotFoundError(f"Recommendation catalog not found: {path}")

    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)

    ranking = payload.get("ranking") or {}
    return {
        "recommendations": payload.get("recommendations") or {},
        "severity_weights": {
            **DEFAULT_SEVERITY_WEIGHTS,
            **(ranking.get("severity_weights") or {}),
        },
        "priority_bands": {
            **DEFAULT_PRIORITY_BANDS,
            **(ranking.get("priority_bands") or {}),
        },
    }


def get_catalog_entry(catalog: Dict[str, Any], signal_type: str) -> Dict[str, Any] | None:
    entry = catalog.get("recommendations", {}).get(signal_type)
    return dict(entry) if isinstance(entry, dict) else None
