"""
Workspace Credential Service — reads from Postgres credentials table only.

See docs/POSTGRES-SINGLE-SOURCE-PLAN.md
"""

import os
from typing import Any, Dict, Optional

from services.security.secure_database import secure_db


def allow_connector_env_fallback() -> bool:
    """Platform env vars (AWS_*, GITHUB_*) may only substitute assignment creds when explicitly allowed."""
    return os.getenv("ALLOW_CONNECTOR_ENV_FALLBACK", "false").lower() == "true"


class CredentialService:
    """Load decrypted assignment credentials from secure_db."""

    def get_workspace_credentials(
        self, workspace_id: str, assignment_id: str, connector_type: str
    ) -> Dict[str, Any]:
        creds = secure_db.get_assignment_credentials(workspace_id, assignment_id, connector_type)
        return creds or {}

    def get_credential_with_fallback(
        self,
        workspace_id: str,
        assignment_id: str,
        connector_type: str,
        credential_name: str,
        env_var_name: str,
    ) -> Optional[str]:
        """
        Get a specific credential with environment variable fallback for secrets only.

        Args:
            workspace_id: ID of the workspace (required for workspace-only)
            assignment_id: ID of the assignment (required for workspace-only)
            connector_type: Type of connector (github, jira, aws)
            credential_name: Name of the credential in the assignment JSON
            env_var_name: Name of the environment variable to fallback to (for secrets only)

        Returns:
            The credential value or None if not found
        """
        # First try workspace credentials
        credentials = self.get_workspace_credentials(workspace_id, assignment_id, connector_type)
        if credential_name in credentials and credentials[credential_name]:
            return credentials[credential_name]

        if not allow_connector_env_fallback():
            return None

        # Local/dev only: optional env fallback for secrets management
        return os.getenv(env_var_name)

    def get_github_credentials(
        self, workspace_id: str, assignment_id: str
    ) -> Dict[str, Optional[str]]:
        """Get GitHub credentials from workspace store with env var fallback for secrets"""
        return {
            "token": self.get_credential_with_fallback(
                workspace_id, assignment_id, "github", "github_token", "GITHUB_TOKEN"
            ),
            "org": self.get_credential_with_fallback(
                workspace_id, assignment_id, "github", "github_org", "GITHUB_ORG"
            ),
        }

    def get_jira_credentials(
        self, workspace_id: str, assignment_id: str
    ) -> Dict[str, Optional[str]]:
        """Get Jira credentials from workspace store with env var fallback for secrets"""
        return {
            "token": self.get_credential_with_fallback(
                workspace_id, assignment_id, "jira", "jira_token", "JIRA_TOKEN"
            ),
            "email": self.get_credential_with_fallback(
                workspace_id, assignment_id, "jira", "jira_email", "JIRA_EMAIL"
            ),
            "url": self.get_credential_with_fallback(
                workspace_id, assignment_id, "jira", "jira_url", "JIRA_URL"
            ),
        }

    def get_aws_credentials(
        self, workspace_id: str, assignment_id: str
    ) -> Dict[str, Optional[str]]:
        """Get AWS credentials from workspace store with env var fallback for secrets"""
        return {
            "access_key": self.get_credential_with_fallback(
                workspace_id, assignment_id, "aws", "aws_access_key", "AWS_ACCESS_KEY_ID"
            ),
            "secret_key": self.get_credential_with_fallback(
                workspace_id, assignment_id, "aws", "aws_secret_key", "AWS_SECRET_ACCESS_KEY"
            ),
            "region": self.get_credential_with_fallback(
                workspace_id, assignment_id, "aws", "aws_region", "AWS_REGION"
            ),
        }

    def get_openai_credentials(
        self, workspace_id: str, assignment_id: str
    ) -> Dict[str, Optional[str]]:
        """Get OpenAI credentials from workspace store with env var fallback for secrets"""
        return {
            "api_key": self.get_credential_with_fallback(
                workspace_id, assignment_id, "openai", "openai_api_key", "OPENAI_API_KEY"
            )
        }

    def get_railway_credentials(
        self, workspace_id: str, assignment_id: str
    ) -> Dict[str, Optional[str]]:
        """Get Railway credentials from workspace store with optional env fallback."""
        credentials = self.get_workspace_credentials(workspace_id, assignment_id, "railway")
        token = self.get_credential_with_fallback(
            workspace_id, assignment_id, "railway", "railway_token", "RAILWAY_TOKEN"
        )
        project_id = credentials.get("railway_project_id") or credentials.get("project_id")
        project_name = credentials.get("railway_project_name") or credentials.get("project_name")
        if not project_id and allow_connector_env_fallback():
            project_id = os.getenv("RAILWAY_PROJECT_ID")
        if not project_name and allow_connector_env_fallback():
            project_name = os.getenv("RAILWAY_PROJECT_NAME")
        return {
            "token": token,
            "project_id": project_id,
            "project_name": project_name,
        }

    def get_vercel_credentials(
        self, workspace_id: str, assignment_id: str
    ) -> Dict[str, Optional[str]]:
        """Get Vercel credentials from workspace store with optional env fallback."""
        credentials = self.get_workspace_credentials(workspace_id, assignment_id, "vercel")
        token = self.get_credential_with_fallback(
            workspace_id, assignment_id, "vercel", "vercel_token", "VERCEL_TOKEN"
        )
        project_id = credentials.get("vercel_project_id") or credentials.get("project_id")
        team_id = credentials.get("vercel_team_id") or credentials.get("team_id")
        if not project_id and allow_connector_env_fallback():
            project_id = os.getenv("VERCEL_PROJECT_ID")
        if not team_id and allow_connector_env_fallback():
            team_id = os.getenv("VERCEL_TEAM_ID")
        return {
            "token": token,
            "project_id": project_id,
            "team_id": team_id,
        }

    def get_azure_credentials(
        self, workspace_id: str, assignment_id: str
    ) -> Dict[str, Optional[str]]:
        """Get Azure service principal credentials from workspace store."""
        credentials = self.get_workspace_credentials(workspace_id, assignment_id, "azure")
        tenant_id = credentials.get("azure_tenant_id") or credentials.get("tenant_id")
        client_id = credentials.get("azure_client_id") or credentials.get("client_id")
        subscription_id = credentials.get("azure_subscription_id") or credentials.get(
            "subscription_id"
        )
        resource_group = credentials.get("azure_resource_group") or credentials.get(
            "resource_group"
        )
        client_secret = self.get_credential_with_fallback(
            workspace_id,
            assignment_id,
            "azure",
            "azure_client_secret",
            "AZURE_CLIENT_SECRET",
        )
        if allow_connector_env_fallback():
            tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
            client_id = client_id or os.getenv("AZURE_CLIENT_ID")
            subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
            resource_group = resource_group or os.getenv("AZURE_RESOURCE_GROUP")
        return {
            "tenant_id": tenant_id,
            "client_id": client_id,
            "client_secret": client_secret,
            "subscription_id": subscription_id,
            "resource_group": resource_group,
        }
