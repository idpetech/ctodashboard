"""Cloud Access Framework interface (AWS first; Azure/GCP later)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from services.cloud_access.session import CloudAccessSession


class CloudAccessBroker(ABC):
    """Broker that returns ephemeral sessions for a tenant-scoped cloud connection."""

    provider: str

    @abstractmethod
    def get_session(
        self,
        *,
        workspace_id: str,
        assignment_id: str,
        stored: Dict[str, Any],
        region: Optional[str] = None,
    ) -> CloudAccessSession:
        """Obtain or refresh a short-lived session. Must not persist tokens."""
