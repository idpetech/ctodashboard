# Railway Metrics Service
# Extracted from backend/metrics_service.py::RailwayMetrics
import asyncio
import os
import ssl
from typing import Any, Dict, Optional

import aiohttp

from config.logging_config import get_logger

logger = get_logger(__name__)

RAILWAY_GRAPHQL_V2 = os.getenv("RAILWAY_API_URL", "https://backboard.railway.com/graphql/v2")


def validate_railway_connection(token: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Validate Railway account, workspace, or project token against the public GraphQL API."""
    import requests

    token = (token or "").strip()
    project_id = (project_id or "").strip() or None
    if not token:
        return {"valid": False, "error": "Railway token is required"}

    def _post(query: str, variables: Optional[dict] = None, project_token: bool = False):
        headers = {"Content-Type": "application/json"}
        if project_token:
            headers["Project-Access-Token"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        return requests.post(RAILWAY_GRAPHQL_V2, json=payload, headers=headers, timeout=15)

    last_status = None

    # Account / personal token
    try:
        response = _post("query { me { id email name } }")
        last_status = response.status_code
        if response.status_code == 200:
            data = response.json()
            me = (data.get("data") or {}).get("me") or {}
            if me.get("id") and not data.get("errors"):
                return {
                    "valid": True,
                    "user_id": me.get("id"),
                    "email": me.get("email"),
                    "name": me.get("name"),
                    "token_type": "account",
                }
    except requests.RequestException as exc:
        return {"valid": False, "error": f"Railway connection failed: {exc}"}

    # Project access token (uses Project-Access-Token header, not Bearer)
    try:
        response = _post("query { projectToken { projectId environmentId } }", project_token=True)
        last_status = response.status_code
        if response.status_code == 200:
            data = response.json()
            project_token_data = (data.get("data") or {}).get("projectToken") or {}
            token_project_id = project_token_data.get("projectId")
            if token_project_id and not data.get("errors"):
                if project_id and token_project_id != project_id:
                    return {
                        "valid": False,
                        "error": "Project token does not match the project ID you entered",
                    }
                return {
                    "valid": True,
                    "project_id": token_project_id,
                    "environment_id": project_token_data.get("environmentId"),
                    "token_type": "project",
                }
    except requests.RequestException as exc:
        return {"valid": False, "error": f"Railway connection failed: {exc}"}

    # Workspace/account token scoped to a specific project
    if project_id:
        try:
            response = _post(
                "query($id: String!) { project(id: $id) { id name } }",
                variables={"id": project_id},
            )
            last_status = response.status_code
            if response.status_code == 200:
                data = response.json()
                project = (data.get("data") or {}).get("project")
                if project and project.get("id"):
                    return {
                        "valid": True,
                        "project_id": project.get("id"),
                        "project_name": project.get("name"),
                        "token_type": "workspace",
                    }
                errors = data.get("errors") or []
                if errors:
                    return {
                        "valid": False,
                        "error": errors[0].get("message", "Railway project not accessible"),
                    }
        except requests.RequestException as exc:
            return {"valid": False, "error": f"Railway connection failed: {exc}"}

    if last_status == 401:
        return {"valid": False, "error": "Invalid Railway token"}
    if last_status == 404:
        return {
            "valid": False,
            "error": "Railway API endpoint not found — verify Railway API status or token type",
        }
    return {
        "valid": False,
        "error": (
            "Railway token could not be verified. Use a personal account token, "
            "or a project token scoped to this project."
        ),
    }


class RailwayMetrics:
    """Railway API integration for deployment metrics

    NOTE: As of August 2024, Railway appears to have deprecated their public API.
    All known GraphQL and REST endpoints return 404. This service provides
    placeholder metrics until Railway's API becomes available again.

    Usage:
    ------
    railway = RailwayMetrics()
    metrics = await railway.get_metrics(project_id="my-project")

    Expected responses:
    - {"status": "success", ...} when API is working
    - {"status": "api_unavailable", ...} when Railway API returns 404/errors
    """

    def __init__(self, workspace_id: str = None, assignment_id: str = None):
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id
        self.base_url = os.getenv("RAILWAY_API_URL", RAILWAY_GRAPHQL_V2)
        self.rest_api_url = os.getenv("RAILWAY_REST_API", "https://api.railway.app/v2")
        self._init_credentials()

    def _init_credentials(self) -> None:
        from services.auth.credential_service import allow_connector_env_fallback

        self.api_token = None
        if self.workspace_id and self.assignment_id:
            try:
                from services.auth.credential_service import CredentialService

                creds = CredentialService().get_railway_credentials(
                    self.workspace_id, self.assignment_id
                )
                self.api_token = creds.get("token")
                if self.api_token:
                    return
            except Exception as exc:
                logger.warning("Could not load Railway credentials: %s", exc)
            if allow_connector_env_fallback():
                self.api_token = os.getenv("RAILWAY_TOKEN")
        else:
            self.api_token = os.getenv("RAILWAY_TOKEN")

    async def get_metrics(self, project_id: str = None, project_name: str = None) -> Dict:
        """Get Railway deployment metrics

        Args:
            project_id: Railway project ID (preferred)
            project_name: Railway project name (fallback)

        Returns:
            Dict with deployment metrics or error status
        """
        if not self.api_token:
            return {
                "status": "api_unavailable",
                "error": "Railway token not configured",
                "message": "Set RAILWAY_TOKEN environment variable to enable Railway metrics",
            }

        if not project_id and not project_name:
            return {
                "status": "api_unavailable",
                "error": "No project specified",
                "message": "Either project_id or project_name must be provided",
            }

        # Try multiple API approaches since Railway's API availability is inconsistent
        methods = [
            ("GraphQL API", self._get_metrics_graphql),
            ("REST API v2", self._get_metrics_rest_v2),
            ("Legacy REST API", self._get_metrics_rest_legacy),
        ]

        for method_name, method in methods:
            try:
                result = await method(project_id, project_name)
                if result.get("status") == "success":
                    return result
                # If method returns api_unavailable, try next method
            except Exception:
                # Continue to next method
                pass

        # All methods failed - return graceful fallback
        return {
            "status": "api_unavailable",
            "message": "Railway API currently unavailable",
            "fallback_data": {
                "project_id": project_id or "unknown",
                "project_name": project_name or "unknown",
                "total_deployments": "N/A",
                "successful_deployments": "N/A",
                "failed_deployments": "N/A",
                "success_rate": "N/A",
                "last_deployment": "N/A",
                "average_deployment_time": "N/A",
            },
        }

    async def _get_metrics_graphql(self, project_id: str, project_name: str) -> Dict:
        """Try Railway's GraphQL API (current schema: project → services → latestDeployment)."""
        query = """
        query GetProjectMetrics($id: String!) {
            project(id: $id) {
                id
                name
                services {
                    edges {
                        node {
                            name
                            serviceInstances {
                                edges {
                                    node {
                                        latestDeployment {
                                            id
                                            status
                                            createdAt
                                            finishedAt
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        payload = {"query": query, "variables": {"id": project_id}}

        auth_modes = [
            {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"},
            {"Project-Access-Token": self.api_token, "Content-Type": "application/json"},
        ]

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for headers in auth_modes:
                async with session.post(self.base_url, json=payload, headers=headers) as response:
                    if response.status == 404:
                        continue

                    if response.status != 200:
                        continue

                    data = await response.json()

                    if data.get("errors"):
                        continue

                    project = data.get("data", {}).get("project")
                    if not project:
                        continue

                    deployments = []
                    for service_edge in project.get("services", {}).get("edges", []):
                        service = service_edge.get("node") or {}
                        for inst_edge in service.get("serviceInstances", {}).get("edges", []):
                            deployment = (inst_edge.get("node") or {}).get("latestDeployment")
                            if deployment:
                                deployments.append(deployment)

                    return self._process_deployment_data(
                        deployments, project_id, project.get("name") or project_name
                    )

        return {
            "status": "api_unavailable",
            "method": "graphql",
            "error": "GraphQL endpoint not found or project not accessible",
        }

    async def _get_metrics_rest_v2(self, project_id: str, project_name: str) -> Dict:
        """Try Railway's REST API v2"""
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}

        url = f"{self.rest_api_url}/projects/{project_id}/deployments"

        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 404:
                    return {
                        "status": "api_unavailable",
                        "method": "rest_v2",
                        "error": "REST v2 endpoint not found",
                    }

                if response.status != 200:
                    return {
                        "status": "api_unavailable",
                        "method": "rest_v2",
                        "error": f"HTTP {response.status}",
                    }

                data = await response.json()
                return self._process_deployment_data(data, project_id, project_name)

    async def _get_metrics_rest_legacy(self, project_id: str, project_name: str) -> Dict:
        """Try Railway's legacy REST API endpoints"""
        legacy_endpoints = [
            f"https://railway.app/api/projects/{project_id}/deployments",
            f"https://api.railway.com/v1/projects/{project_id}/deployments",
        ]

        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}

        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for url in legacy_endpoints:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._process_deployment_data(data, project_id, project_name)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                    logger.warning("Railway API endpoint %s failed: %s", url, e)
                    continue

        return {
            "status": "api_unavailable",
            "method": "legacy",
            "error": "All legacy endpoints failed",
        }

    def _process_deployment_data(
        self, deployments_data, project_id: str, project_name: str
    ) -> Dict:
        """Process deployment data into metrics"""
        try:
            # Handle different data structures
            if isinstance(deployments_data, list):
                deployments = deployments_data
            elif isinstance(deployments_data, dict) and "edges" in deployments_data:
                deployments = [edge["node"] for edge in deployments_data["edges"]]
            elif isinstance(deployments_data, dict) and "data" in deployments_data:
                deployments = deployments_data["data"]
            else:
                deployments = []

            total_deployments = len(deployments)

            if total_deployments == 0:
                return {
                    "status": "success",
                    "project_id": project_id,
                    "project_name": project_name or "Unknown",
                    "total_deployments": 0,
                    "successful_deployments": 0,
                    "failed_deployments": 0,
                    "success_rate": 0,
                    "last_deployment": "Never",
                    "average_deployment_time": "N/A",
                }

            successful_deployments = 0
            failed_deployments = 0
            deployment_times = []
            last_deployment = None

            for deployment in deployments:
                status = deployment.get("status", "").lower()

                if status in ["success", "completed", "deployed", "active"]:
                    successful_deployments += 1
                elif status in ["failed", "error", "cancelled"]:
                    failed_deployments += 1

                # Track deployment time if available
                created_at = deployment.get("createdAt") or deployment.get("created_at")
                finished_at = deployment.get("finishedAt") or deployment.get("finished_at")

                if created_at and finished_at:
                    try:
                        from datetime import datetime

                        start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        end = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
                        duration = (end - start).total_seconds()
                        deployment_times.append(duration)
                    except (ValueError, TypeError) as e:
                        logger.warning("Failed to parse deployment timestamp: %s", e)
                        pass

                # Track most recent deployment
                if created_at:
                    if not last_deployment or created_at > last_deployment:
                        last_deployment = created_at

            success_rate = (
                round((successful_deployments / total_deployments) * 100, 1)
                if total_deployments > 0
                else 0
            )
            avg_deployment_time = (
                round(sum(deployment_times) / len(deployment_times), 1)
                if deployment_times
                else "N/A"
            )

            return {
                "status": "success",
                "project_id": project_id,
                "project_name": project_name or "Unknown",
                "total_deployments": total_deployments,
                "successful_deployments": successful_deployments,
                "failed_deployments": failed_deployments,
                "success_rate": success_rate,
                "last_deployment": last_deployment or "Unknown",
                "average_deployment_time": f"{avg_deployment_time}s"
                if isinstance(avg_deployment_time, float)
                else avg_deployment_time,
            }

        except Exception as e:
            return {
                "status": "api_unavailable",
                "error": f"Data processing error: {str(e)}",
                "project_id": project_id,
                "project_name": project_name,
            }
