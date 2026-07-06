"""
Persist Load All Metrics snapshots per assignment (workspace.settings JSONB).

Mirrors the CTOLens briefing pattern: GET returns stored data; live connector
fetches happen only when refresh is explicitly requested.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from config.logging_config import get_logger
from services.briefing_staleness import assignments_fingerprint
from services.ctolens_run_metadata import METRICS_STALE_DAYS
from services.workspace.db_access import resolve_workspace_db

logger = get_logger(__name__)

SETTINGS_KEY = "assignment_metrics_cache"
CONNECTOR_KEYS = frozenset({"aws", "github", "jira", "openai", "railway", "vercel", "azure"})
METADATA_KEYS = frozenset(
    {
        "source",
        "fetched_at",
        "metrics_fetched",
        "source_fingerprint",
        "duration_seconds",
        "connectors_ok",
        "connectors_failed",
        "is_stale",
        "stale_reason",
        "workspace_id",
        "assignment_id",
        "cache_enabled",
    }
)


def is_metrics_cache_enabled() -> bool:
    return os.getenv("ENABLE_ASSIGNMENT_METRICS_CACHE", "false").lower() == "true"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _assignment_fingerprint(assignment: Dict[str, Any]) -> str:
    aid = str(assignment.get("id") or assignment.get("assignment_id") or "")
    return assignments_fingerprint([{**assignment, "id": aid}])


def _connector_status(payload: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    ok: List[str] = []
    failed: List[str] = []
    for name in sorted(CONNECTOR_KEYS):
        block = payload.get(name)
        if block is None:
            continue
        if isinstance(block, dict) and block.get("error"):
            failed.append(name)
        elif (
            isinstance(block, list)
            and block
            and isinstance(block[0], dict)
            and block[0].get("error")
        ):
            failed.append(name)
        else:
            ok.append(name)
    return ok, failed


def _metrics_payload_only(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    payload = snapshot.get("payload")
    if isinstance(payload, dict):
        return dict(payload)
    return {
        key: value
        for key, value in snapshot.items()
        if key not in METADATA_KEYS and key in CONNECTOR_KEYS
    }


def get_cache_bucket(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    bucket = (settings or {}).get(SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def get_stored_snapshot(
    secure_db: Any,
    workspace_id: str,
    assignment_id: str,
) -> Optional[Dict[str, Any]]:
    secure_db = resolve_workspace_db(secure_db)
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return None
    entry = get_cache_bucket(ws.get("settings")).get(assignment_id)
    return dict(entry) if isinstance(entry, dict) else None


def assess_snapshot_staleness(
    snapshot: Optional[Dict[str, Any]],
    assignment: Dict[str, Any],
) -> Dict[str, Any]:
    current_fp = _assignment_fingerprint(assignment)
    if not snapshot:
        return {
            "is_stale": False,
            "stale_reason": None,
            "current_fingerprint": current_fp,
            "stored_fingerprint": None,
            "fetched_at": None,
            "metrics_age_days": None,
        }

    stored_fp = snapshot.get("source_fingerprint")
    fetched_at = snapshot.get("fetched_at")
    reasons: List[str] = []

    if stored_fp and stored_fp != current_fp:
        reasons.append("Assignment connectors or budget changed since last metrics refresh.")
    elif not stored_fp:
        reasons.append("Metrics were captured before change tracking — refresh recommended.")

    parsed = _parse_iso(fetched_at)
    age_days = None
    if parsed:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - parsed).days
        if age_days >= METRICS_STALE_DAYS:
            reasons.append(f"Live metrics are {age_days} days old — refresh recommended.")

    return {
        "is_stale": bool(reasons),
        "stale_reason": " ".join(reasons) if reasons else None,
        "current_fingerprint": current_fp,
        "stored_fingerprint": stored_fp,
        "fetched_at": fetched_at,
        "metrics_age_days": age_days,
    }


def store_metrics_snapshot(
    secure_db: Any,
    workspace_id: str,
    assignment_id: str,
    assignment: Dict[str, Any],
    payload: Dict[str, Any],
    *,
    duration_seconds: float,
) -> bool:
    secure_db = resolve_workspace_db(secure_db)
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return False

    connectors_ok, connectors_failed = _connector_status(payload)
    settings = dict(ws.get("settings") or {})
    bucket = get_cache_bucket(settings)
    bucket[assignment_id] = {
        "fetched_at": _utc_now(),
        "metrics_fetched": True,
        "source_fingerprint": _assignment_fingerprint(assignment),
        "duration_seconds": round(duration_seconds, 2),
        "connectors_ok": connectors_ok,
        "connectors_failed": connectors_failed,
        "workspace_id": workspace_id,
        "assignment_id": assignment_id,
        "payload": payload,
    }
    settings[SETTINGS_KEY] = bucket
    return bool(
        secure_db.store_workspace(
            workspace_id,
            ws.get("name", workspace_id),
            ws.get("description", ""),
            settings=settings,
        )
    )


def build_metrics_response(
    *,
    source: str,
    workspace_id: str,
    assignment_id: str,
    snapshot: Dict[str, Any],
    staleness: Dict[str, Any],
) -> Dict[str, Any]:
    payload = _metrics_payload_only(snapshot)
    return {
        **payload,
        "source": source,
        "fetched_at": snapshot.get("fetched_at"),
        "metrics_fetched": bool(snapshot.get("metrics_fetched")),
        "duration_seconds": snapshot.get("duration_seconds"),
        "connectors_ok": snapshot.get("connectors_ok") or [],
        "connectors_failed": snapshot.get("connectors_failed") or [],
        "is_stale": bool(staleness.get("is_stale")),
        "stale_reason": staleness.get("stale_reason"),
        "source_fingerprint": snapshot.get("source_fingerprint"),
        "workspace_id": workspace_id,
        "assignment_id": assignment_id,
        "cache_enabled": is_metrics_cache_enabled(),
    }


def refresh_assignment_metrics(
    workspace_id: str,
    assignment_id: str,
    assignment: Dict[str, Any],
    collect_fn: Callable[[str, str, Dict[str, Any]], Dict[str, Any]],
    *,
    secure_db: Any = None,
) -> Dict[str, Any]:
    """Live connector fetch, persist snapshot, return API envelope."""
    started = time.monotonic()
    payload = collect_fn(workspace_id, assignment_id, assignment)
    duration = time.monotonic() - started

    if is_metrics_cache_enabled():
        store_metrics_snapshot(
            secure_db,
            workspace_id,
            assignment_id,
            assignment,
            payload,
            duration_seconds=duration,
        )

    snapshot = {
        "fetched_at": _utc_now(),
        "metrics_fetched": True,
        "source_fingerprint": _assignment_fingerprint(assignment),
        "duration_seconds": round(duration, 2),
        "connectors_ok": _connector_status(payload)[0],
        "connectors_failed": _connector_status(payload)[1],
        "payload": payload,
    }
    staleness = assess_snapshot_staleness(snapshot, assignment)
    return build_metrics_response(
        source="live",
        workspace_id=workspace_id,
        assignment_id=assignment_id,
        snapshot=snapshot,
        staleness=staleness,
    )


def resolve_assignment_metrics(
    workspace_id: str,
    assignment_id: str,
    assignment: Dict[str, Any],
    collect_fn: Callable[[str, str, Dict[str, Any]], Dict[str, Any]],
    *,
    refresh: bool = False,
    source: Optional[str] = None,
    secure_db: Any = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Return (body, http_status).

    Flag off: always live fetch (legacy).
    Flag on:
      - refresh=true -> live fetch + store
      - source=stored -> stored only (404 if missing)
      - default -> stored if present, else 404 with hint
    """
    if not is_metrics_cache_enabled():
        payload = collect_fn(workspace_id, assignment_id, assignment)
        return payload, 200

    source_norm = (source or "").strip().lower()
    if refresh or source_norm in ("live", "fetch"):
        return refresh_assignment_metrics(
            workspace_id,
            assignment_id,
            assignment,
            collect_fn,
            secure_db=secure_db,
        ), 200

    snapshot = get_stored_snapshot(secure_db, workspace_id, assignment_id)
    if source_norm == "stored":
        if not snapshot:
            return (
                {
                    "error": "no_stored_metrics",
                    "message": (
                        "No stored metrics for this assignment yet. "
                        "Use Refresh live metrics to fetch from connectors."
                    ),
                    "cache_enabled": True,
                    "workspace_id": workspace_id,
                    "assignment_id": assignment_id,
                },
                404,
            )
        staleness = assess_snapshot_staleness(snapshot, assignment)
        return (
            build_metrics_response(
                source="stored",
                workspace_id=workspace_id,
                assignment_id=assignment_id,
                snapshot=snapshot,
                staleness=staleness,
            ),
            200,
        )

    if snapshot:
        staleness = assess_snapshot_staleness(snapshot, assignment)
        return (
            build_metrics_response(
                source="stored",
                workspace_id=workspace_id,
                assignment_id=assignment_id,
                snapshot=snapshot,
                staleness=staleness,
            ),
            200,
        )

    return (
        {
            "error": "no_stored_metrics",
            "message": (
                "No stored metrics yet. Click Refresh live metrics to fetch from connectors "
                "(often 30–90 seconds)."
            ),
            "cache_enabled": True,
            "workspace_id": workspace_id,
            "assignment_id": assignment_id,
        },
        404,
    )
