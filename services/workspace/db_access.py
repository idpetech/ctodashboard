"""Single entry point for workspace Postgres handle (avoids route-layer imports)."""

from __future__ import annotations

from typing import Any, Optional


def get_workspace_db() -> Any:
    """Return the shared secure_db proxy (lazy import)."""
    from services.security.db_workspaces import secure_db

    return secure_db


def resolve_workspace_db(secure_db: Optional[Any] = None) -> Any:
    """Use explicit db when provided; otherwise resolve via workspace backend."""
    if secure_db is not None:
        return secure_db
    from services.workspace.workspace_service import get_workspace_backend

    return get_workspace_backend().db
