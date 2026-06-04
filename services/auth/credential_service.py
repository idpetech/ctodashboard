"""
Workspace Credential Service — reads from Postgres credentials table only.

See docs/POSTGRES-SINGLE-SOURCE-PLAN.md
"""

import os
from typing import Dict, Any, Optional

from services.security.secure_database import secure_db


class CredentialService:
    """Load decrypted assignment credentials from secure_db."""

    def get_workspace_credentials(
        self, workspace_id: str, assignment_id: str, connector_type: str
    ) -> Dict[str, Any]:
        creds = secure_db.get_assignment_credentials(
            workspace_id, assignment_id, connector_type
        )
        return creds or {}
    
    def get_credential_with_fallback(self, 
                                   workspace_id: str, 
                                   assignment_id: str, 
                                   connector_type: str, 
                                   credential_name: str, 
                                   env_var_name: str) -> Optional[str]:
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
        
        # Fallback to environment variable for secret values only (documented behavior)
        # This preserves deployment compatibility for secrets management
        return os.getenv(env_var_name)
    
    def get_github_credentials(self, workspace_id: str, assignment_id: str) -> Dict[str, Optional[str]]:
        """Get GitHub credentials from workspace store with env var fallback for secrets"""
        return {
            "token": self.get_credential_with_fallback(workspace_id, assignment_id, "github", "github_token", "GITHUB_TOKEN"),
            "org": self.get_credential_with_fallback(workspace_id, assignment_id, "github", "github_org", "GITHUB_ORG")
        }
    
    def get_jira_credentials(self, workspace_id: str, assignment_id: str) -> Dict[str, Optional[str]]:
        """Get Jira credentials from workspace store with env var fallback for secrets"""
        return {
            "token": self.get_credential_with_fallback(workspace_id, assignment_id, "jira", "jira_token", "JIRA_TOKEN"),
            "email": self.get_credential_with_fallback(workspace_id, assignment_id, "jira", "jira_email", "JIRA_EMAIL"),
            "url": self.get_credential_with_fallback(workspace_id, assignment_id, "jira", "jira_url", "JIRA_URL")
        }
    
    def get_aws_credentials(self, workspace_id: str, assignment_id: str) -> Dict[str, Optional[str]]:
        """Get AWS credentials from workspace store with env var fallback for secrets"""
        return {
            "access_key": self.get_credential_with_fallback(workspace_id, assignment_id, "aws", "aws_access_key", "AWS_ACCESS_KEY_ID"),
            "secret_key": self.get_credential_with_fallback(workspace_id, assignment_id, "aws", "aws_secret_key", "AWS_SECRET_ACCESS_KEY"),
            "region": self.get_credential_with_fallback(workspace_id, assignment_id, "aws", "aws_region", "AWS_REGION")
        }
    
    def get_openai_credentials(self, workspace_id: str, assignment_id: str) -> Dict[str, Optional[str]]:
        """Get OpenAI credentials from workspace store with env var fallback for secrets"""
        return {
            "api_key": self.get_credential_with_fallback(workspace_id, assignment_id, "openai", "openai_api_key", "OPENAI_API_KEY")
        }