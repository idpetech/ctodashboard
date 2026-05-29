"""
Workspace Credential Service - Phase 3
Reads credentials from workspace assignment JSON files instead of environment variables
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class CredentialService:
    """
    Service to read credentials from workspace assignment configurations.
    Phase 3: Enable workspace-scoped authentication instead of global env vars.
    """
    
    def __init__(self):
        self.workspaces_dir = Path("config/workspaces")
        self.assignments_dir = Path("config/assignments")
    
    def get_workspace_credentials(self, workspace_id: str, assignment_id: str, connector_type: str) -> Dict[str, Any]:
        """
        Get credentials for a specific connector in a workspace assignment.
        
        Args:
            workspace_id: ID of the workspace
            assignment_id: ID of the assignment within the workspace
            connector_type: Type of connector (github, jira, aws, etc.)
            
        Returns:
            Dictionary containing credentials for the connector
            
        Example return for GitHub:
        {
            "github_token": "ghp_xxxxxxxxxxxx",
            "github_org": "ideptech"
        }
        """
        try:
            # First try to load from workspace file
            workspace_file = self.workspaces_dir / f"{workspace_id}.json"
            if workspace_file.exists():
                with open(workspace_file, 'r') as f:
                    workspace_data = json.load(f)
                
                # Look for assignment in workspace
                if assignment_id in workspace_data.get("assignments", []):
                    # Try to find assignment with auth instances
                    assignment_path = self.assignments_dir / f"{assignment_id}.json"
                    if assignment_path.exists():
                        with open(assignment_path, 'r') as f:
                            assignment_data = json.load(f)
                        
                        # Extract credentials from auth_instances
                        auth_instances = assignment_data.get("auth_instances", {})
                        if connector_type in auth_instances:
                            return auth_instances[connector_type].get("credentials", {})
            
            # Fallback: try direct assignment file
            assignment_file = self.assignments_dir / f"{assignment_id}.json"
            if assignment_file.exists():
                with open(assignment_file, 'r') as f:
                    assignment_data = json.load(f)
                
                # Extract credentials from auth_instances
                auth_instances = assignment_data.get("auth_instances", {})
                if connector_type in auth_instances:
                    return auth_instances[connector_type].get("credentials", {})
            
            return {}
            
        except Exception as e:
            print(f"Warning: Could not load workspace credentials for {workspace_id}/{assignment_id}/{connector_type}: {e}")
            return {}
    
    def get_credential_with_fallback(self, 
                                   workspace_id: Optional[str], 
                                   assignment_id: Optional[str], 
                                   connector_type: str, 
                                   credential_name: str, 
                                   env_var_name: str) -> Optional[str]:
        """
        Get a specific credential with fallback to environment variable.
        This preserves existing behavior while enabling workspace credentials.
        
        Args:
            workspace_id: ID of the workspace (None for env var only)
            assignment_id: ID of the assignment (None for env var only)
            connector_type: Type of connector (github, jira, aws)
            credential_name: Name of the credential in the assignment JSON
            env_var_name: Name of the environment variable to fallback to
            
        Returns:
            The credential value or None if not found
        """
        # First try workspace credentials if workspace context is available
        if workspace_id and assignment_id:
            credentials = self.get_workspace_credentials(workspace_id, assignment_id, connector_type)
            if credential_name in credentials:
                return credentials[credential_name]
        
        # Fallback to environment variable (preserves existing behavior)
        return os.getenv(env_var_name)
    
    def get_github_credentials(self, workspace_id: Optional[str] = None, assignment_id: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Get GitHub credentials with environment variable fallback"""
        return {
            "token": self.get_credential_with_fallback(workspace_id, assignment_id, "github", "github_token", "GITHUB_TOKEN"),
            "org": self.get_credential_with_fallback(workspace_id, assignment_id, "github", "github_org", "GITHUB_ORG")
        }
    
    def get_jira_credentials(self, workspace_id: Optional[str] = None, assignment_id: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Get Jira credentials with environment variable fallback"""
        return {
            "token": self.get_credential_with_fallback(workspace_id, assignment_id, "jira", "jira_token", "JIRA_TOKEN"),
            "email": self.get_credential_with_fallback(workspace_id, assignment_id, "jira", "jira_email", "JIRA_EMAIL"),
            "url": self.get_credential_with_fallback(workspace_id, assignment_id, "jira", "jira_url", "JIRA_URL")
        }
    
    def get_aws_credentials(self, workspace_id: Optional[str] = None, assignment_id: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Get AWS credentials with environment variable fallback"""
        return {
            "access_key": self.get_credential_with_fallback(workspace_id, assignment_id, "aws", "aws_access_key", "AWS_ACCESS_KEY_ID"),
            "secret_key": self.get_credential_with_fallback(workspace_id, assignment_id, "aws", "aws_secret_key", "AWS_SECRET_ACCESS_KEY"),
            "region": self.get_credential_with_fallback(workspace_id, assignment_id, "aws", "aws_region", "AWS_REGION")
        }
    
    def get_openai_credentials(self, workspace_id: Optional[str] = None, assignment_id: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Get OpenAI credentials with environment variable fallback"""
        return {
            "api_key": self.get_credential_with_fallback(workspace_id, assignment_id, "openai", "openai_api_key", "OPENAI_API_KEY")
        }