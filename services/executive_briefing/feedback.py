"""
Insight Feedback Loop — record CTO accept/dismiss on recommendations.

Persists to workspace.settings.recommendation_feedback (Postgres JSONB).
Future: personalize RecommendationEngine ranking from acceptance history.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class RecommendationFeedback:
    recommendation_id: str
    title: str
    status: str
    reason: Optional[str] = None
    recorded_at: str = ""

    def __post_init__(self) -> None:
        if not self.recorded_at:
            self.recorded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            if self.recorded_at.endswith("+00:00"):
                self.recorded_at = self.recorded_at.replace("+00:00", "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


VALID_STATUSES = frozenset({"accepted", "dismissed"})


def record_recommendation_feedback(
    secure_db: Any,
    workspace_id: str,
    *,
    recommendation_id: str,
    title: str,
    status: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Store one feedback event. Returns the saved record."""
    status_norm = (status or "").strip().lower()
    if status_norm not in VALID_STATUSES:
        raise ValueError("status must be 'accepted' or 'dismissed'")

    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        raise ValueError("Workspace not found")

    record = RecommendationFeedback(
        recommendation_id=recommendation_id,
        title=title,
        status=status_norm,
        reason=(reason or "").strip() or None,
    )
    settings = ws.get("settings") or {}
    history: List[Dict[str, Any]] = list(settings.get("recommendation_feedback") or [])
    history.append(record.to_dict())
    settings["recommendation_feedback"] = history[-500:]

    secure_db.store_workspace(
        workspace_id,
        ws.get("name", workspace_id),
        ws.get("description", ""),
        settings=settings,
    )
    return record.to_dict()


def list_recommendation_feedback(
    secure_db: Any,
    workspace_id: str,
    *,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return []
    history = (ws.get("settings") or {}).get("recommendation_feedback") or []
    return list(reversed(history[-limit:]))


def feedback_summary(secure_db: Any, workspace_id: str) -> Dict[str, Any]:
    """Aggregate acceptance stats for future ranking personalization."""
    history = list_recommendation_feedback(secure_db, workspace_id, limit=500)
    accepted = sum(1 for h in history if h.get("status") == "accepted")
    dismissed = sum(1 for h in history if h.get("status") == "dismissed")
    return {
        "total": len(history),
        "accepted": accepted,
        "dismissed": dismissed,
        "acceptance_rate": round(accepted / len(history), 3) if history else None,
    }
