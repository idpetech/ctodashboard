"""
Metrics Aggregator Service
Composes embedded metrics services for MCP consumption
"""

import asyncio
from datetime import datetime
from typing import Dict

from .assignment_service import AssignmentService
from .embedded.aws_metrics import EmbeddedAWSMetrics
from .embedded.github_metrics import EmbeddedGitHubMetrics
from .embedded.jira_metrics import EmbeddedJiraMetrics
from .embedded.openai_metrics import OpenAIMetrics
from .embedded.railway_metrics import RailwayMetrics


class MetricsAggregator:
    """Aggregates metrics from all embedded services"""
    
    def __init__(self):
        self.assignment_service = AssignmentService()
        self.aws_metrics = EmbeddedAWSMetrics()
        self.github_metrics = EmbeddedGitHubMetrics()
        self.jira_metrics = EmbeddedJiraMetrics()
        self.openai_metrics = OpenAIMetrics()
        self.railway_metrics = RailwayMetrics()
    
    async def get_all_metrics(self, assignment_config: Dict) -> Dict:
        """Get metrics for an assignment from all configured services"""
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "assignment_id": assignment_config.get("id", "unknown")
        }
        
        # Get AWS metrics if configured
        aws_config = assignment_config.get("aws", {})
        if aws_config.get("enabled", False):
            try:
                metrics["aws"] = self.aws_metrics.get_metrics()
            except Exception as e:
                metrics["aws"] = {"error": str(e)}
        
        # Get GitHub metrics if configured
        github_config = assignment_config.get("github", {})
        if github_config.get("enabled", False):
            try:
                metrics["github"] = self.github_metrics.get_metrics(github_config)
            except Exception as e:
                metrics["github"] = {"error": str(e)}
        
        # Get Jira metrics if configured
        jira_config = assignment_config.get("jira", {})
        if jira_config.get("enabled", False):
            try:
                metrics["jira"] = self.jira_metrics.get_metrics(jira_config)
            except Exception as e:
                metrics["jira"] = {"error": str(e)}
        
        # Get OpenAI metrics if configured
        openai_config = assignment_config.get("openai", {})
        if openai_config.get("enabled", False):
            try:
                metrics["openai"] = self.openai_metrics.get_usage_metrics(openai_config)
            except Exception as e:
                metrics["openai"] = {"error": str(e)}
        
        # Get Railway metrics if configured
        railway_config = assignment_config.get("metrics_config", {}).get("railway", {})
        if railway_config.get("enabled", False):
            try:
                project_id = railway_config.get("project_id")
                project_name = railway_config.get("project_name")
                metrics["railway"] = await self.railway_metrics.get_metrics(
                    project_id=project_id, 
                    project_name=project_name
                )
            except Exception as e:
                metrics["railway"] = {"error": str(e)}
        
        return metrics
    
    def get_assignment(self, assignment_id: str) -> Dict:
        """Get assignment configuration"""
        return self.assignment_service.get_assignment(assignment_id)
    
    def get_all_assignments(self) -> list:
        """Get all assignments"""
        return self.assignment_service.get_all_assignments()