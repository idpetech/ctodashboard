"""
CTOLens run metadata — schedule, run status, rolling log, staleness, export strip.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from services.signals.models import SignalCategory

logger = get_logger(__name__)

METRICS_STALE_DAYS = 7
MAX_RUN_LOG = 10
DEFAULT_SCHEDULE: Dict[str, Any] = {
    "enabled": False,
    "frequency": "manual_only",
    "time_utc": "06:00",
    "day_of_week": "monday",
    "on_import": False,
}
VALID_FREQUENCIES = frozenset({"manual_only", "daily", "weekly"})
VALID_DAYS = frozenset(
    {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
)

EXPORT_STRIP_KEYS = frozenset(
    {
        "signals",
        "diagnostics",
        "run_id",
        "connector_runs",
        "signals_evaluated_count",
        "signals_shown_count",
    }
)


def is_scheduled_enrichment_enabled() -> bool:
    return os.getenv("ENABLE_CTOLENS_SCHEDULED_ENRICHMENT", "false").lower() == "true"


def cron_secret() -> str:
    return (os.getenv("CTOLENS_CRON_SECRET") or os.getenv("INTERNAL_CRON_SECRET") or "").strip()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def normalize_schedule(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = dict(DEFAULT_SCHEDULE)
    if raw:
        base.update({k: v for k, v in raw.items() if v is not None})
    freq = str(base.get("frequency") or "manual_only").lower()
    if freq not in VALID_FREQUENCIES:
        freq = "manual_only"
    base["frequency"] = freq
    base["enabled"] = bool(base.get("enabled")) and freq != "manual_only"
    day = str(base.get("day_of_week") or "monday").lower()
    base["day_of_week"] = day if day in VALID_DAYS else "monday"
    base["on_import"] = bool(base.get("on_import"))
    return base


def validate_schedule(schedule: Dict[str, Any]) -> None:
    freq = schedule.get("frequency")
    if freq not in VALID_FREQUENCIES:
        raise ValueError(f"Invalid ctolens_schedule.frequency: {freq}")
    if schedule.get("day_of_week") not in VALID_DAYS:
        raise ValueError("Invalid ctolens_schedule.day_of_week")


def get_workspace_schedule(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return normalize_schedule((settings or {}).get("ctolens_schedule"))


def get_run_status(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return dict((settings or {}).get("ctolens_run_status") or {})


def get_run_log(settings: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    log = (settings or {}).get("ctolens_run_log") or []
    return list(log) if isinstance(log, list) else []


def append_run_log(settings: Dict[str, Any], entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    log = get_run_log(settings)
    log.insert(0, entry)
    return log[:MAX_RUN_LOG]


def build_run_log_entry(
    *,
    run_id: str,
    run_type: str,
    source: str,
    status: str,
    duration_seconds: float,
    assignments_evaluated: int,
    connectors_attempted: List[str],
    metrics_fetched: bool,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "run_type": run_type,
        "source": source,
        "status": status,
        "started_at": utc_now_iso(),
        "duration_seconds": round(duration_seconds, 1),
        "assignments_evaluated": assignments_evaluated,
        "connectors_attempted": connectors_attempted,
        "metrics_fetched": metrics_fetched,
        "error": error,
    }


def build_run_status(
    *,
    run_id: str,
    run_type: str,
    source: str,
    status: str,
    duration_seconds: float,
    assignments_evaluated: int,
    connectors_attempted: List[str],
    metrics_fetched: bool,
    connector_runs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    now = utc_now_iso()
    out: Dict[str, Any] = {
        "last_run_id": run_id,
        "last_run_type": run_type,
        "last_run_source": source,
        "last_run_at": now,
        "metrics_fetched": metrics_fetched,
        "assignments_evaluated": assignments_evaluated,
        "connectors_attempted": connectors_attempted,
        "duration_seconds": round(duration_seconds, 1),
        "status": status,
        "connector_runs": connector_runs or [],
    }
    if run_type == "fast":
        out["last_fast_run_at"] = now
    else:
        out["last_enriched_run_at"] = now
        out["last_enriched_run_source"] = source
    return out


def persist_run_metadata(
    secure_db: Any,
    workspace_id: str,
    run_status: Dict[str, Any],
    log_entry: Dict[str, Any],
) -> None:
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return
    settings = dict(ws.get("settings") or {})
    settings["ctolens_run_status"] = run_status
    settings["ctolens_run_log"] = append_run_log(settings, log_entry)
    secure_db.store_workspace(
        workspace_id,
        ws.get("name", workspace_id),
        ws.get("description", ""),
        settings=settings,
    )


def filter_signals_for_run_mode(signals: List[Any], fetch_metrics: bool) -> List[Any]:
    """Drop delivery-category signals when live metrics were not fetched."""
    if fetch_metrics:
        return signals
    kept = []
    for sig in signals:
        category = getattr(sig, "category", None)
        if hasattr(category, "value"):
            category = category.value
        if category == SignalCategory.DELIVERY.value:
            continue
        kept.append(sig)
    return kept


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        raw = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None


def assess_extended_staleness(
    briefing: Optional[Dict[str, Any]],
    assignments: List[Dict[str, Any]],
    run_status: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from services.briefing_pipeline import assess_briefing_staleness

    base = assess_briefing_staleness(briefing, assignments)
    run_status = run_status or {}
    metrics_fetched = bool((briefing or {}).get("metrics_fetched"))
    last_enriched = run_status.get("last_enriched_run_at")
    metrics_stale = False
    metrics_reason = None

    if metrics_fetched and briefing:
        enriched_at = _parse_iso(last_enriched or briefing.get("generated_at"))
        if enriched_at:
            age_days = (datetime.now(timezone.utc) - enriched_at).days
            if age_days >= METRICS_STALE_DAYS:
                metrics_stale = True
                metrics_reason = f"Live metrics are {age_days} days old — refresh recommended."
    elif run_status.get("last_enriched_run_at"):
        enriched_at = _parse_iso(run_status.get("last_enriched_run_at"))
        if enriched_at:
            age_days = (datetime.now(timezone.utc) - enriched_at).days
            if age_days >= METRICS_STALE_DAYS:
                metrics_stale = True
                metrics_reason = f"Last live metrics run was {age_days} days ago."

    assignment_stale = bool(base.get("is_stale"))
    reasons = []
    if assignment_stale and base.get("reason"):
        reasons.append(base["reason"])
    if metrics_stale and metrics_reason:
        reasons.append(metrics_reason)

    return {
        **base,
        "assignment_stale": assignment_stale,
        "metrics_stale": metrics_stale,
        "metrics_fetched": metrics_fetched,
        "last_enriched_run_at": run_status.get("last_enriched_run_at"),
        "is_stale": assignment_stale or metrics_stale,
        "reason": " ".join(reasons) if reasons else base.get("reason"),
    }


def header_summary(
    briefing: Optional[Dict[str, Any]],
    run_status: Optional[Dict[str, Any]] = None,
    schedule: Optional[Dict[str, Any]] = None,
) -> str:
    if not briefing:
        return "No briefing generated yet."
    run_status = run_status or {}
    generated = briefing.get("generated_at")
    when = generated or "unknown time"
    if briefing.get("metrics_fetched"):
        n = run_status.get("assignments_evaluated") or "?"
        connectors = run_status.get("connectors_attempted") or []
        conn_txt = ", ".join(connectors) if connectors else "connectors"
        return f"Last live metrics run: {when} · {n} assignments · {conn_txt} OK"
    return f"Briefing updated · assignment data only · {when}"


def build_diagnostics_payload(
    briefing: Dict[str, Any],
    run_status: Dict[str, Any],
    run_log: List[Dict[str, Any]],
) -> Dict[str, Any]:
    signals = briefing.get("signals") or []
    eb = briefing.get("executive_briefing") or {}
    shown = len(eb.get("top_risks") or []) + len(eb.get("opportunities") or [])
    return {
        "run_id": briefing.get("run_id") or run_status.get("last_run_id"),
        "run_status": run_status,
        "connector_runs": briefing.get("connector_runs") or run_status.get("connector_runs") or [],
        "signals_evaluated_count": len(signals),
        "signals_shown_count": shown,
        "run_log": run_log[:MAX_RUN_LOG],
    }


def strip_briefing_for_export(briefing: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(briefing)
    for key in EXPORT_STRIP_KEYS:
        out.pop(key, None)
    out.pop("feedback_summary", None)
    if "founder_attention_items" in out and out.get("signals") is None:
        out.pop("founder_attention_items", None)
    return out
