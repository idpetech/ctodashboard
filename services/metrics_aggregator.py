"""
Metrics Aggregator Service - Phase 2 Workspace-Only
Composes embedded metrics services for MCP consumption using workspace store
"""

import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

from .workspace.workspace_service import WorkspaceService
from .embedded.aws_metrics import EmbeddedAWSMetrics
from .embedded.github_metrics import EmbeddedGitHubMetrics
from .embedded.jira_metrics import EmbeddedJiraMetrics
from .embedded.railway_metrics import RailwayMetrics


class MetricsAggregator:
    """Aggregates metrics from all embedded services - workspace-only"""
    
    def __init__(self):
        self.workspace_service = WorkspaceService()
    
    def _get_workspace_connectors(self, workspace_id: str, assignment_id: str) -> Dict:
        """Create workspace-scoped connector instances with credentials"""
        return {
            'aws': EmbeddedAWSMetrics(workspace_id=workspace_id, assignment_id=assignment_id),
            'github': EmbeddedGitHubMetrics(workspace_id=workspace_id, assignment_id=assignment_id),
            'jira': EmbeddedJiraMetrics(workspace_id=workspace_id, assignment_id=assignment_id)
        }
    
    async def get_all_metrics(self, workspace_id: str, assignment_id: str) -> Dict:
        """
        Get metrics for an assignment from all configured services.
        Phase 2: Uses workspace store and workspace connectors.
        """
        # Load assignment from workspace store
        assignment = self.workspace_service.get_assignment(workspace_id, assignment_id)
        if not assignment:
            return {
                "error": f"Assignment '{assignment_id}' not found in workspace '{workspace_id}'",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create workspace connectors with credentials
        connectors = self._get_workspace_connectors(workspace_id, assignment_id)
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "assignment_id": assignment_id,
            "workspace_id": workspace_id
        }
        
        # Get metrics using correct schema: metrics_config.<connector>
        metrics_config = assignment.get("metrics_config", {})
        
        # Get AWS metrics if configured
        aws_config = metrics_config.get("aws", {})
        if aws_config.get("enabled", False):
            try:
                metrics["aws"] = connectors["aws"].get_metrics()
            except Exception as e:
                metrics["aws"] = {"error": str(e)}
        
        # Get GitHub metrics if configured
        github_config = metrics_config.get("github", {})
        if github_config.get("enabled", False):
            try:
                from services.assignment_metrics_config import (
                    github_metrics_config as build_github_metrics_config,
                )

                gh_cfg = build_github_metrics_config(
                    workspace_id, assignment_id, github_config
                )
                metrics["github"] = connectors["github"].get_metrics(gh_cfg)
            except Exception as e:
                metrics["github"] = {"error": str(e)}

        # Get Jira metrics if configured
        jira_config = metrics_config.get("jira", {})
        if jira_config.get("enabled", False):
            try:
                from services.assignment_metrics_config import (
                    jira_metrics_config as build_jira_metrics_config,
                )

                metrics["jira"] = connectors["jira"].get_metrics(
                    build_jira_metrics_config(
                        workspace_id, assignment_id, jira_config
                    )
                )
            except Exception as e:
                metrics["jira"] = {"error": str(e)}
        
        # Get OpenAI metrics if configured
        openai_config = metrics_config.get("openai", {})
        if openai_config.get("enabled", False):
            try:
                metrics["openai"] = connectors["openai"].get_usage_metrics(openai_config)
            except Exception as e:
                metrics["openai"] = {"error": str(e)}
        
        # Get Railway metrics if configured
        railway_config = metrics_config.get("railway", {})
        if railway_config.get("enabled", False):
            try:
                project_id = railway_config.get("project_id")
                project_name = railway_config.get("project_name")
                railway_metrics = RailwayMetrics()
                metrics["railway"] = await railway_metrics.get_metrics(
                    project_id=project_id, 
                    project_name=project_name
                )
            except Exception as e:
                metrics["railway"] = {"error": str(e)}
        
        return metrics
    
    def find_assignment(self, assignment_id: str, workspace_id: str = None) -> Dict:
        """Find assignment using workspace store"""
        return self.workspace_service.find_assignment(assignment_id, workspace_id)
    
    def get_all_assignments(self) -> list:
        """Get all assignments from workspace store"""
        all_assignments = []
        try:
            for workspace_path in self.workspace_service.workspace_dir.glob("*"):
                if workspace_path.is_dir():
                    workspace_id = workspace_path.name
                    result = self.workspace_service.get_workspace_assignments(workspace_id)
                    if "assignments" in result:
                        all_assignments.extend(result["assignments"])
        except Exception as e:
            logger.error("Error aggregating assignments: %s", e, exc_info=True)
        
        return all_assignments