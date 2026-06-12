"""
Portfolio entity layer (Act 1) — workspace.settings.portfolios + assignment.portfolio_id.

Feature-flagged via ENABLE_PORTFOLIOS (default off). When off, assignments still
carry portfolio_id='default' in Postgres; portfolio APIs return 403.
"""

from __future__ import annotations

import os
import re
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PORTFOLIO_ID = "default"
DEFAULT_PORTFOLIO_NAME = "Main"
PORTFOLIO_BRIEFINGS_KEY = "portfolio_briefings"
ASSIGNMENT_BRIEFINGS_KEY = "assignment_briefings"
PORTFOLIO_CTOLENS_BRIEFINGS_KEY = "portfolio_ctolens_briefings"
ASSIGNMENT_CTOLENS_BRIEFINGS_KEY = "assignment_ctolens_briefings"

_PORTFOLIO_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def is_portfolios_enabled() -> bool:
    return os.getenv("ENABLE_PORTFOLIOS", "false").lower() == "true"


def default_portfolio_entry() -> Dict[str, Any]:
    return {
        "id": DEFAULT_PORTFOLIO_ID,
        "name": DEFAULT_PORTFOLIO_NAME,
        "description": "Default portfolio for all assignments",
        "sort_order": 0,
        "created_at": datetime.utcnow().isoformat(),
    }


def ensure_default_portfolio(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Ensure settings.portfolios contains the implicit default bucket."""
    settings = dict(settings or {})
    portfolios = list(settings.get("portfolios") or [])
    if not any(p.get("id") == DEFAULT_PORTFOLIO_ID for p in portfolios):
        portfolios.insert(0, default_portfolio_entry())
        settings["portfolios"] = portfolios
    return settings


def list_portfolios(settings: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    settings = ensure_default_portfolio(settings)
    return sorted(
        settings.get("portfolios") or [],
        key=lambda p: (p.get("sort_order", 0), str(p.get("name") or "")),
    )


def get_portfolio(settings: Optional[Dict[str, Any]], portfolio_id: str) -> Optional[Dict[str, Any]]:
    for portfolio in list_portfolios(settings):
        if portfolio.get("id") == portfolio_id:
            return portfolio
    return None


def validate_portfolio_id(portfolio_id: str) -> Optional[str]:
    if not portfolio_id or not isinstance(portfolio_id, str):
        return "portfolio_id is required"
    pid = portfolio_id.strip()
    if not pid:
        return "portfolio_id cannot be empty"
    if pid == DEFAULT_PORTFOLIO_ID:
        return None
    if not _PORTFOLIO_ID_RE.match(pid):
        return "portfolio_id must be alphanumeric (hyphens/underscores allowed)"
    return None


def validate_portfolio_name(name: str) -> Optional[str]:
    if not name or not str(name).strip():
        return "Portfolio name is required"
    if len(str(name).strip()) > 120:
        return "Portfolio name is too long"
    return None


def normalize_assignment_portfolio_id(assignment: Dict[str, Any]) -> str:
    return str(assignment.get("portfolio_id") or DEFAULT_PORTFOLIO_ID)


def filter_assignments_by_portfolio(
    assignments: List[Dict[str, Any]], portfolio_id: str
) -> List[Dict[str, Any]]:
    return [
        a for a in (assignments or []) if normalize_assignment_portfolio_id(a) == portfolio_id
    ]


def filter_assignments_by_id(
    assignments: List[Dict[str, Any]], assignment_id: str
) -> List[Dict[str, Any]]:
    aid = str(assignment_id)
    return [
        a
        for a in (assignments or [])
        if str(a.get("id") or a.get("assignment_id") or "") == aid
    ]


def create_portfolio(
    settings: Dict[str, Any],
    name: str,
    description: str = "",
    sort_order: Optional[int] = None,
    portfolio_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[str]]:
    name_err = validate_portfolio_name(name)
    if name_err:
        return settings, {}, name_err

    settings = ensure_default_portfolio(deepcopy(settings))
    portfolios = list(settings.get("portfolios") or [])

    pid = (portfolio_id or f"pf_{uuid.uuid4().hex[:12]}").strip()
    id_err = validate_portfolio_id(pid)
    if id_err:
        return settings, {}, id_err
    if pid == DEFAULT_PORTFOLIO_ID:
        return settings, {}, "Cannot create a portfolio with reserved id 'default'"
    if any(p.get("id") == pid for p in portfolios):
        return settings, {}, f"Portfolio '{pid}' already exists"
    if any(str(p.get("name") or "").strip().lower() == name.strip().lower() for p in portfolios):
        return settings, {}, "A portfolio with this name already exists"

    entry = {
        "id": pid,
        "name": name.strip(),
        "description": (description or "").strip(),
        "sort_order": sort_order if sort_order is not None else len(portfolios),
        "created_at": datetime.utcnow().isoformat(),
    }
    portfolios.append(entry)
    settings["portfolios"] = portfolios
    return settings, entry, None


def update_portfolio(
    settings: Dict[str, Any],
    portfolio_id: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[str]]:
    settings = ensure_default_portfolio(deepcopy(settings))
    portfolios = list(settings.get("portfolios") or [])
    idx = next((i for i, p in enumerate(portfolios) if p.get("id") == portfolio_id), None)
    if idx is None:
        return settings, None, f"Portfolio '{portfolio_id}' not found"

    entry = dict(portfolios[idx])
    if name is not None:
        name_err = validate_portfolio_name(name)
        if name_err:
            return settings, None, name_err
        entry["name"] = name.strip()
    if description is not None:
        entry["description"] = description.strip()
    if sort_order is not None:
        entry["sort_order"] = sort_order
    entry["updated_at"] = datetime.utcnow().isoformat()
    portfolios[idx] = entry
    settings["portfolios"] = portfolios
    return settings, entry, None


def delete_portfolio(
    settings: Dict[str, Any], portfolio_id: str
) -> Tuple[Dict[str, Any], Optional[str]]:
    if portfolio_id == DEFAULT_PORTFOLIO_ID:
        return settings, "The default portfolio cannot be deleted"

    settings = ensure_default_portfolio(deepcopy(settings))
    portfolios = list(settings.get("portfolios") or [])
    if not any(p.get("id") == portfolio_id for p in portfolios):
        return settings, f"Portfolio '{portfolio_id}' not found"

    settings["portfolios"] = [p for p in portfolios if p.get("id") != portfolio_id]

    for key in (PORTFOLIO_BRIEFINGS_KEY, PORTFOLIO_CTOLENS_BRIEFINGS_KEY):
        briefings = dict(settings.get(key) or {})
        briefings.pop(portfolio_id, None)
        settings[key] = briefings

    return settings, None


def merge_imported_portfolios(
    settings: Dict[str, Any], imported: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Merge portfolios from import without removing the default bucket."""
    settings = ensure_default_portfolio(deepcopy(settings))
    if not imported:
        return settings

    by_id = {p.get("id"): p for p in list_portfolios(settings) if p.get("id")}
    for row in imported:
        if not isinstance(row, dict):
            continue
        pid = row.get("id")
        if not pid or pid == DEFAULT_PORTFOLIO_ID:
            if pid == DEFAULT_PORTFOLIO_ID:
                by_id[DEFAULT_PORTFOLIO_ID] = {
                    **by_id.get(DEFAULT_PORTFOLIO_ID, default_portfolio_entry()),
                    **{k: v for k, v in row.items() if v is not None and k != "id"},
                }
            continue
        if validate_portfolio_id(str(pid)):
            continue
        by_id[str(pid)] = {
            "id": str(pid),
            "name": row.get("name") or str(pid),
            "description": row.get("description") or "",
            "sort_order": row.get("sort_order", 0),
            "created_at": row.get("created_at") or datetime.utcnow().isoformat(),
        }

    settings["portfolios"] = sorted(by_id.values(), key=lambda p: (p.get("sort_order", 0), p.get("name", "")))
    return settings


def _briefing_bucket(settings: Dict[str, Any], key: str) -> Dict[str, Any]:
    bucket = settings.get(key)
    return dict(bucket) if isinstance(bucket, dict) else {}


def get_scoped_briefing(
    settings: Optional[Dict[str, Any]],
    *,
    scope: str,
    scope_id: str,
    engine: str = "attention",
) -> Optional[Dict[str, Any]]:
    settings = settings or {}
    if scope == "portfolio":
        key = PORTFOLIO_BRIEFINGS_KEY if engine == "attention" else PORTFOLIO_CTOLENS_BRIEFINGS_KEY
    elif scope == "assignment":
        key = (
            ASSIGNMENT_BRIEFINGS_KEY if engine == "attention" else ASSIGNMENT_CTOLENS_BRIEFINGS_KEY
        )
    else:
        return None
    return _briefing_bucket(settings, key).get(scope_id)


def store_scoped_briefing_settings(
    settings: Dict[str, Any],
    *,
    scope: str,
    scope_id: str,
    briefing: Dict[str, Any],
    engine: str = "attention",
) -> Dict[str, Any]:
    settings = dict(settings or {})
    if scope == "portfolio":
        key = PORTFOLIO_BRIEFINGS_KEY if engine == "attention" else PORTFOLIO_CTOLENS_BRIEFINGS_KEY
    elif scope == "assignment":
        key = (
            ASSIGNMENT_BRIEFINGS_KEY if engine == "attention" else ASSIGNMENT_CTOLENS_BRIEFINGS_KEY
        )
    else:
        return settings

    bucket = _briefing_bucket(settings, key)
    bucket[scope_id] = briefing
    settings[key] = bucket
    updated_key = f"{key}_updated_at"
    timestamps = dict(settings.get(updated_key) or {})
    timestamps[scope_id] = briefing.get("generated_at") or datetime.utcnow().isoformat()
    settings[updated_key] = timestamps
    return settings


def persist_scoped_briefing(
    secure_db: Any,
    workspace_id: str,
    *,
    scope: str,
    scope_id: str,
    briefing: Dict[str, Any],
    engine: str = "attention",
) -> bool:
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return False
    settings = store_scoped_briefing_settings(
        ws.get("settings") or {},
        scope=scope,
        scope_id=scope_id,
        briefing=briefing,
        engine=engine,
    )
    return secure_db.store_workspace(
        workspace_id,
        ws.get("name", workspace_id),
        ws.get("description") or "",
        settings=settings,
    )


def load_scoped_briefing(
    secure_db: Any,
    workspace_id: str,
    *,
    scope: str,
    scope_id: str,
    engine: str = "attention",
) -> Optional[Dict[str, Any]]:
    ws = secure_db.get_workspace(workspace_id)
    if not ws:
        return None
    return get_scoped_briefing(
        ws.get("settings") or {},
        scope=scope,
        scope_id=scope_id,
        engine=engine,
    )
