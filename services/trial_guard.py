"""Server-side trial write guards for API routes."""

from __future__ import annotations

from typing import Any, Optional, Tuple

from services.auth.auth_middleware import get_current_user
from services.trial_service import trial_write_denied_response
from services.user_access import can_write


def require_trial_write_access() -> Optional[Tuple[Any, int]]:
    """Return a Flask error response if the user cannot perform write operations."""
    user = get_current_user()
    if not can_write(user):
        return trial_write_denied_response()
    return None
