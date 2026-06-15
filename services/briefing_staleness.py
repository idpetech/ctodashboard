"""Briefing fingerprint and staleness checks (shared by pipeline + run metadata)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional


def assignments_fingerprint(assignments: List[Dict[str, Any]]) -> str:
    """Stable hash of active assignment fields that affect briefing output."""
    rows: List[Dict[str, Any]] = []
    for assignment in sorted(
        assignments or [],
        key=lambda item: str(item.get("id") or item.get("assignment_id") or ""),
    ):
        if (assignment.get("status") or "active") != "active":
            continue
        rows.append(
            {
                "id": str(assignment.get("id") or assignment.get("assignment_id") or ""),
                "status": assignment.get("status"),
                "monthly_burn_rate": assignment.get("monthly_burn_rate"),
                "target_monthly_burn": assignment.get("target_monthly_burn"),
                "previous_monthly_burn": assignment.get("previous_monthly_burn"),
                "team_size": assignment.get("team_size"),
                "owner": assignment.get("owner"),
                "metrics_config": assignment.get("metrics_config") or {},
            }
        )
    payload = json.dumps(rows, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def assess_briefing_staleness(
    briefing: Optional[Dict[str, Any]],
    assignments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare stored briefing fingerprint to current assignments."""
    current = assignments_fingerprint(assignments)
    if not briefing:
        return {
            "is_stale": False,
            "reason": None,
            "current_fingerprint": current,
            "stored_fingerprint": None,
        }

    stored = briefing.get("source_fingerprint")
    generated_at = briefing.get("generated_at")
    if not stored:
        return {
            "is_stale": True,
            "reason": "Briefing was generated before change tracking — update recommended.",
            "current_fingerprint": current,
            "stored_fingerprint": None,
            "generated_at": generated_at,
        }
    if stored != current:
        return {
            "is_stale": True,
            "reason": "Portfolio data changed since this briefing was generated.",
            "current_fingerprint": current,
            "stored_fingerprint": stored,
            "generated_at": generated_at,
        }
    return {
        "is_stale": False,
        "reason": None,
        "current_fingerprint": current,
        "stored_fingerprint": stored,
        "generated_at": generated_at,
    }
