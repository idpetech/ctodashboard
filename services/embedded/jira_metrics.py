import os
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EmbeddedJiraMetrics:
    """Jira metrics embedded directly in the Flask app"""
    
    def __init__(self, workspace_id=None, assignment_id=None):
        # Phase 3: Support workspace credentials with environment variable fallback
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id
        
        # Initialize credentials (preserves existing behavior if no workspace context)
        self._init_credentials()
    
    def _init_credentials(self):
        """Initialize Jira credentials with workspace support and env var fallback"""
        if self.workspace_id and self.assignment_id:
            try:
                from services.auth.credential_service import CredentialService
                credential_service = CredentialService()
                credentials = credential_service.get_jira_credentials(self.workspace_id, self.assignment_id)
                self.base_url = credentials.get("url") or os.getenv("JIRA_URL")
                self.email = credentials.get("email") or os.getenv("JIRA_EMAIL") 
                self.token = credentials.get("token") or os.getenv("JIRA_TOKEN")
            except Exception as e:
                logger.warning("Could not load workspace credentials, falling back to env vars: %s", e)
                self.base_url = os.getenv("JIRA_URL")
                self.email = os.getenv("JIRA_EMAIL")
                self.token = os.getenv("JIRA_TOKEN")
        else:
            # Fallback to environment variables (preserves existing behavior)
            self.base_url = os.getenv("JIRA_URL")
            self.email = os.getenv("JIRA_EMAIL")
            self.token = os.getenv("JIRA_TOKEN")
        
    def get_project_metrics(self, project_key: str) -> dict:
        """Get Jira project metrics"""
        if not all([self.base_url, self.email, self.token]):
            return {"error": "Jira credentials not configured"}
        
        try:
            auth = (self.email, self.token)
            headers = {"Accept": "application/json"}
            
            # Get project info
            project_url = f"{self.base_url}/rest/api/3/project/{project_key}"
            project_response = requests.get(project_url, auth=auth, headers=headers, timeout=10)
            project_data = project_response.json() if project_response.status_code == 200 else {}
            
            # Get issues by status using new JQL API endpoint  
            search_url = f"{self.base_url}/rest/api/3/search/jql"
            jql_query = f"project = '{project_key}' AND created >= -30d"
            search_payload = {
                "jql": jql_query,
                "fields": ["status", "priority", "created", "resolutiondate"],
                "maxResults": 100
            }
            
            headers_with_content = {**headers, "Content-Type": "application/json"}
            search_response = requests.post(search_url, auth=auth, headers=headers_with_content, json=search_payload, timeout=10)
            
            if search_response.status_code != 200:
                return {"error": f"Jira API returned {search_response.status_code}: {search_response.text[:200]}"}
            
            search_data = search_response.json()
            issues = search_data.get("issues", [])
            
            # Calculate metrics
            total_issues = len(issues)
            resolved_issues = len([i for i in issues if i["fields"].get("resolutiondate")])
            
            return {
                "project_key": project_key,
                "project_name": project_data.get("name", "Unknown"),
                "total_issues_last_30_days": total_issues,
                "resolved_issues_last_30_days": resolved_issues,
                "resolution_rate": round(resolved_issues / total_issues * 100, 1) if total_issues > 0 else 0
            }
            
        except Exception as e:
            return {"error": f"Jira API error: {str(e)}"}

    def get_metrics(self, config: dict) -> dict:
        """Get Jira metrics with configuration - main method called by routes"""
        project_key = config.get('project_key')
        if not project_key:
            return {"error": "No Jira project_key specified in configuration"}
        
        metrics = self.get_project_metrics(project_key)
        
        # Add configuration context
        metrics['config'] = {
            'project_key': project_key,
            'track_sprints': config.get('track_sprints', False),
            'track_bugs': config.get('track_bugs', False),
            'enabled': config.get('enabled', False)
        }
        
        return metrics

# Note: This is a service class, no Flask routes needed here
# Routes are handled in the main integrated_dashboard.py file
