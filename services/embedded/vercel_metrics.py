"""Vercel deployment metrics — Act 4 connector."""

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class EmbeddedVercelMetrics:
    """Fetch recent deployment signals from the Vercel REST API."""

    def __init__(self, workspace_id: Optional[str] = None, assignment_id: Optional[str] = None):
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id
        self._init_credentials()

    def _init_credentials(self) -> None:
        from services.auth.credential_service import allow_connector_env_fallback

        self.token = None
        self.team_id = None
        if self.workspace_id and self.assignment_id:
            try:
                from services.auth.credential_service import CredentialService

                creds = CredentialService().get_vercel_credentials(
                    self.workspace_id, self.assignment_id
                )
                self.token = creds.get("token")
                self.team_id = creds.get("team_id")
                if self.token:
                    return
            except Exception as exc:
                logger.warning("Could not load Vercel credentials: %s", exc)
            if allow_connector_env_fallback():
                import os

                self.token = os.getenv("VERCEL_TOKEN")
                self.team_id = os.getenv("VERCEL_TEAM_ID")
        else:
            import os

            self.token = os.getenv("VERCEL_TOKEN")
            self.team_id = os.getenv("VERCEL_TEAM_ID")

    def get_metrics(self, config: dict) -> Dict[str, Any]:
        project_id = (config.get("project_id") or "").strip()
        team_id = (config.get("team_id") or self.team_id or "").strip() or None

        if not self.token:
            return {"error": "Vercel API token not configured"}
        if not project_id:
            return {"error": "Vercel project ID not configured"}

        headers = {"Authorization": f"Bearer {self.token}"}
        params: Dict[str, Any] = {"projectId": project_id, "limit": 20}
        if team_id:
            params["teamId"] = team_id

        try:
            response = requests.get(
                "https://api.vercel.com/v6/deployments",
                headers=headers,
                params=params,
                timeout=15,
            )
            if response.status_code == 401:
                return {"error": "Vercel API returned 401 — check token"}
            if response.status_code == 404:
                return {"error": f"Vercel project '{project_id}' not found"}
            if response.status_code != 200:
                return {"error": f"Vercel API error {response.status_code}: {response.text[:120]}"}

            deployments = response.json().get("deployments") or []
            states: Dict[str, int] = {}
            for dep in deployments:
                state = (dep.get("state") or dep.get("readyState") or "unknown").lower()
                states[state] = states.get(state, 0) + 1

            ready = states.get("ready", 0) + states.get("success", 0)
            failed = states.get("error", 0) + states.get("failed", 0) + states.get("canceled", 0)
            total = len(deployments)
            last = deployments[0] if deployments else {}

            return {
                "project_id": project_id,
                "total_deployments": total,
                "ready_deployments": ready,
                "failed_deployments": failed,
                "success_rate": round((ready / total) * 100, 1) if total else None,
                "last_deployment_state": last.get("state") or last.get("readyState"),
                "last_deployment_url": last.get("url"),
                "last_deployment_at": last.get("createdAt") or last.get("created"),
            }
        except requests.RequestException as exc:
            logger.warning("Vercel metrics request failed: %s", exc)
            return {"error": f"Vercel connection failed: {exc}"}
