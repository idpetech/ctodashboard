"""Azure resource metrics — Act 4 connector (service principal)."""

import logging
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

AZURE_MGMT_SCOPE = "https://management.azure.com/.default"
AZURE_MGMT_BASE = "https://management.azure.com"


def fetch_azure_access_token(
    tenant_id: str, client_id: str, client_secret: str
) -> Tuple[Optional[str], Optional[str]]:
    """Exchange service principal credentials for an Azure management token."""
    if not all([tenant_id, client_id, client_secret]):
        return None, "Azure tenant, client ID, and client secret are required"

    try:
        response = requests.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": AZURE_MGMT_SCOPE,
            },
            timeout=15,
        )
        if response.status_code != 200:
            detail = response.text[:160]
            return None, f"Azure auth failed ({response.status_code}): {detail}"
        token = response.json().get("access_token")
        if not token:
            return None, "Azure auth response did not include an access token"
        return token, None
    except requests.RequestException as exc:
        logger.warning("Azure token request failed: %s", exc)
        return None, f"Azure auth connection failed: {exc}"


class EmbeddedAzureMetrics:
    """Fetch lightweight Azure signals via the Resource Manager REST API."""

    def __init__(self, workspace_id: Optional[str] = None, assignment_id: Optional[str] = None):
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id
        self._init_credentials()

    def _init_credentials(self) -> None:
        from services.auth.credential_service import allow_connector_env_fallback

        self.tenant_id = None
        self.client_id = None
        self.client_secret = None
        self.subscription_id = None
        self.resource_group = None

        if self.workspace_id and self.assignment_id:
            try:
                from services.auth.credential_service import CredentialService

                creds = CredentialService().get_azure_credentials(
                    self.workspace_id, self.assignment_id
                )
                self.tenant_id = creds.get("tenant_id")
                self.client_id = creds.get("client_id")
                self.client_secret = creds.get("client_secret")
                self.subscription_id = creds.get("subscription_id")
                self.resource_group = creds.get("resource_group")
                if self.client_secret:
                    return
            except Exception as exc:
                logger.warning("Could not load Azure credentials: %s", exc)
            if allow_connector_env_fallback():
                import os

                self.tenant_id = os.getenv("AZURE_TENANT_ID")
                self.client_id = os.getenv("AZURE_CLIENT_ID")
                self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
                self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
                self.resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        else:
            import os

            self.tenant_id = os.getenv("AZURE_TENANT_ID")
            self.client_id = os.getenv("AZURE_CLIENT_ID")
            self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
            self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
            self.resource_group = os.getenv("AZURE_RESOURCE_GROUP")

    def get_metrics(self, config: dict) -> Dict[str, Any]:
        subscription_id = (config.get("subscription_id") or self.subscription_id or "").strip()
        resource_group = (config.get("resource_group") or self.resource_group or "").strip() or None

        if not self.client_secret:
            return {"error": "Azure client secret not configured"}
        if not subscription_id:
            return {"error": "Azure subscription ID not configured"}

        token, auth_error = fetch_azure_access_token(
            self.tenant_id or "", self.client_id or "", self.client_secret
        )
        if auth_error:
            return {"error": auth_error}

        headers = {"Authorization": f"Bearer {token}"}

        try:
            if resource_group:
                url = (
                    f"{AZURE_MGMT_BASE}/subscriptions/{subscription_id}"
                    f"/resourceGroups/{resource_group}/resources?api-version=2021-04-01"
                )
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code == 404:
                    return {"error": f"Azure resource group '{resource_group}' not found"}
                if response.status_code != 200:
                    return {
                        "error": f"Azure API error {response.status_code}: {response.text[:120]}"
                    }
                resources = response.json().get("value") or []
                types: Dict[str, int] = {}
                for item in resources:
                    rtype = item.get("type") or "unknown"
                    types[rtype] = types.get(rtype, 0) + 1
                return {
                    "subscription_id": subscription_id,
                    "resource_group": resource_group,
                    "resource_count": len(resources),
                    "resource_types": types,
                }

            rg_response = requests.get(
                f"{AZURE_MGMT_BASE}/subscriptions/{subscription_id}/resourcegroups?api-version=2021-04-01",
                headers=headers,
                timeout=20,
            )
            if rg_response.status_code == 404:
                return {"error": f"Azure subscription '{subscription_id}' not found"}
            if rg_response.status_code != 200:
                return {
                    "error": f"Azure API error {rg_response.status_code}: {rg_response.text[:120]}"
                }

            resource_groups = rg_response.json().get("value") or []
            sites_response = requests.get(
                f"{AZURE_MGMT_BASE}/subscriptions/{subscription_id}"
                "/providers/Microsoft.Web/sites?api-version=2022-03-01",
                headers=headers,
                timeout=20,
            )
            web_apps = []
            if sites_response.status_code == 200:
                web_apps = sites_response.json().get("value") or []

            states: Dict[str, int] = {}
            for app in web_apps:
                state = (app.get("properties") or {}).get("state") or "Unknown"
                states[state] = states.get(state, 0) + 1

            running = states.get("Running", 0)
            total_apps = len(web_apps)

            return {
                "subscription_id": subscription_id,
                "resource_group_count": len(resource_groups),
                "web_app_count": total_apps,
                "web_apps_running": running,
                "web_app_states": states,
                "web_app_availability_rate": round((running / total_apps) * 100, 1)
                if total_apps
                else None,
            }
        except requests.RequestException as exc:
            logger.warning("Azure metrics request failed: %s", exc)
            return {"error": f"Azure connection failed: {exc}"}
