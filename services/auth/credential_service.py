"""
Workspace Credential Service - Phase 1 Rewrite
Reads credentials from workspace store exclusively (no legacy fallback)

Schema: config/workspaces/<ws>/assignments/<id>.json
  -> metrics_config.<connector>.auth_instance.credentials
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class CredentialService:
    """
    Service to read credentials from workspace assignment configurations.
    Phase 1: Workspace-only, no legacy reads.
    """
    
    def __init__(self):
        self.workspaces_dir = Path("config/workspaces")
    
    def get_workspace_credentials(self, workspace_id: str, assignment_id: str, connector_type: str) -> Dict[str, Any]:
        """
        Get credentials for a specific connector in a workspace assignment.
        
        Reads from: config/workspaces/<ws>/assignments/<id>.json
        Path: metrics_config.<connector>.auth_instance.credentials
        
        Args:
            workspace_id: ID of the workspace
            assignment_id: ID of the assignment within the workspace
            connector_type: Type of connector (github, jira, aws, openai)
            
        Returns:
            Dictionary containing credentials for the connector
            
        Example return for GitHub:
        {
            "github_token": "ghp_xxxxxxxxxxxx",
            "github_org": "ideptech"
        }
        """
        try:
            # Read workspace assignment file
            assignment_file = self.workspaces_dir / workspace_id / "assignments" / f"{assignment_id}.json"
            if not assignment_file.exists():
                return {}
                
            with open(assignment_file, 'r') as f:
                assignment_data = json.load(f)
            
            # Navigate to credentials path: metrics_config.<connector>.auth_instance.credentials
            metrics_config = assignment_data.get("metrics_config", {})
            connector_config = metrics_config.get(connector_type, {})
            auth_instance = connector_config.get("auth_instance", {})
            credentials = auth_instance.get("credentials", {})
            
            return credentials
            
        except Exception as e:
            print(f"Warning: Could not load workspace credentials for {workspace_id}/{assignment_id}/{connector_type}: {e}")
            return {}
    
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