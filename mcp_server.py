#!/usr/bin/env python3
"""
CTO Dashboard MCP Server

This MCP server exposes all internal services to the frontend through
the Model Context Protocol, providing a standardized interface for
AI assistants and tools to interact with the dashboard services.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent / "backend"))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    ReadResourceRequest,
    ReadResourceResult,
    Resource,
    TextContent,
    Tool,
)

# Import our existing services
from assignment_service import AssignmentService
from metrics_service import MetricsAggregator, AWSMetrics, GitHubMetrics, JiraMetrics, RailwayMetrics
from chatbot_service import chatbot_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CTODashboardMCPServer:
    """MCP Server for CTO Dashboard services"""
    
    def __init__(self):
        self.server = Server("cto-dashboard-mcp")
        self.assignment_service = AssignmentService()
        self.metrics_aggregator = MetricsAggregator()
        self.aws_metrics = AWSMetrics()
        self.github_metrics = GitHubMetrics()
        self.jira_metrics = JiraMetrics()
        self.railway_metrics = RailwayMetrics()
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register MCP handlers for tools and resources"""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List all available tools"""
            return ListToolsResult(
                tools=[
                    # Assignment Management Tools
                    Tool(
                        name="get_assignments",
                        description="Get all assignments with optional archived filter",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "include_archived": {
                                    "type": "boolean",
                                    "description": "Include archived assignments",
                                    "default": False
                                )
                            )
                        )
                    ),
                    Tool(
                        name="get_assignment",
                        description="Get a specific assignment by ID",
                        inputSchema={
                            type="object",
                            properties={
                                "assignment_id": {
                                    "type": "string",
                                    "description": "Assignment ID to retrieve"
                                )
                            ),
                            required=["assignment_id"]
                        )
                    ),
                    Tool(
                        name="create_assignment",
                        description="Create a new assignment",
                        inputSchema={
                            type="object",
                            properties={
                                "assignment_data": {
                                    "type": "object",
                                    "description": "Assignment configuration data"
                                )
                            ),
                            required=["assignment_data"]
                        )
                    ),
                    Tool(
                        name="update_assignment",
                        description="Update an existing assignment",
                        inputSchema={
                            type="object",
                            properties={
                                "assignment_id": {
                                    "type": "string",
                                    "description": "Assignment ID to update"
                                ),
                                "assignment_data": {
                                    "type": "object",
                                    "description": "Updated assignment data"
                                )
                            ),
                            required=["assignment_id", "assignment_data"]
                        )
                    ),
                    Tool(
                        name="archive_assignment",
                        description="Archive an assignment",
                        inputSchema={
                            type="object",
                            properties={
                                "assignment_id": {
                                    "type": "string",
                                    "description": "Assignment ID to archive"
                                )
                            ),
                            required=["assignment_id"]
                        )
                    ),
                    
                    # Metrics Tools
                    Tool(
                        name="get_assignment_metrics",
                        description="Get real-time metrics for a specific assignment",
                        inputSchema={
                            type="object",
                            properties={
                                "assignment_id": {
                                    "type": "string",
                                    "description": "Assignment ID to get metrics for"
                                )
                            ),
                            required=["assignment_id"]
                        )
                    ),
                    Tool(
                        name="get_aws_insights",
                        description="Get comprehensive AWS cost and resource insights",
                        inputSchema={
                            type="object",
                            properties={}
                        )
                    ),
                    Tool(
                        name="get_github_metrics",
                        description="Get GitHub repository metrics",
                        inputSchema={
                            type="object",
                            properties={
                                "repo": {
                                    "type": "string",
                                    "description": "Repository name"
                                ),
                                "org": {
                                    "type": "string",
                                    "description": "Organization name (optional)"
                                )
                            ),
                            required=["repo"]
                        )
                    ),
                    Tool(
                        name="get_jira_metrics",
                        description="Get Jira project metrics",
                        inputSchema={
                            type="object",
                            properties={
                                "project_key": {
                                    "type": "string",
                                    "description": "Jira project key (optional)"
                                )
                            )
                        )
                    ),
                    Tool(
                        name="get_railway_metrics",
                        description="Get Railway deployment metrics",
                        inputSchema={
                            type="object",
                            properties={}
                        )
                    ),
                    
                    # CTO Insights Tools
                    Tool(
                        name="get_cto_insights",
                        description="Get detailed CTO-level insights for an assignment",
                        inputSchema={
                            type="object",
                            properties={
                                "assignment_id": {
                                    "type": "string",
                                    "description": "Assignment ID to get insights for"
                                )
                            ),
                            required=["assignment_id"]
                        )
                    ),
                    Tool(
                        name="get_cost_optimization_recommendations",
                        description="Get AWS cost optimization recommendations",
                        inputSchema={
                            type="object",
                            properties={}
                        )
                    ),
                    
                    # Health and Status Tools
                    Tool(
                        name="get_health_status",
                        description="Get health status of all configured services",
                        inputSchema={
                            type="object",
                            properties={}
                        )
                    ),
                    Tool(
                        name="get_service_configuration",
                        description="Get configuration status of all services",
                        inputSchema={
                            type="object",
                            properties={}
                        )
                    ),
                    
                    # Chatbot Tools
                    Tool(
                        name="ask_chatbot",
                        description="Ask the AI chatbot a question about managed services, assignments, costs, or metrics",
                        inputSchema={
                            type="object",
                            properties={
                                "question": {
                                    "type": "string",
                                    "description": "The question to ask the chatbot"
                                ),
                                "user_id": {
                                    "type": "string",
                                    "description": "User identifier for conversation tracking (optional)",
                                    "default": "default"
                                )
                            ),
                            required=["question"]
                        )
                    ),
                    Tool(
                        name="get_chatbot_history",
                        description="Get chatbot conversation history for a user",
                        inputSchema={
                            type="object",
                            properties={
                                "user_id": {
                                    "type": "string",
                                    "description": "User identifier",
                                    "default": "default"
                                ),
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of conversations to retrieve",
                                    "default": 10
                                )
                            )
                        )
                    ),
                    Tool(
                        name="clear_chatbot_history",
                        description="Clear chatbot conversation history for a user",
                        inputSchema={
                            type="object",
                            properties={
                                "user_id": {
                                    "type": "string",
                                    "description": "User identifier",
                                    "default": "default"
                                )
                            )
                        )
                    )
                ]
            )
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls"""
            try:
                if name == "get_assignments":
                    include_archived = arguments.get("include_archived", False)
                    assignments = self.assignment_service.get_all_assignments(include_archived=include_archived)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(assignments, indent=2)
                        )]
                    )
                
                elif name == "get_assignment":
                    assignment_id = arguments["assignment_id"]
                    assignment = self.assignment_service.get_assignment(assignment_id)
                    if not assignment:
                        return CallToolResult(
                            content=[TextContent(
                                type="text",
                                text=f"Assignment {assignment_id} not found"
                            )]
                        )
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(assignment, indent=2)
                        )]
                    )
                
                elif name == "create_assignment":
                    assignment_data = arguments["assignment_data"]
                    success = self.assignment_service.create_assignment(assignment_data)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"Assignment creation {'successful' if success else 'failed'}"
                        )]
                    )
                
                elif name == "update_assignment":
                    assignment_id = arguments["assignment_id"]
                    assignment_data = arguments["assignment_data"]
                    success = self.assignment_service.update_assignment(assignment_id, assignment_data)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"Assignment update {'successful' if success else 'failed'}"
                        )]
                    )
                
                elif name == "archive_assignment":
                    assignment_id = arguments["assignment_id"]
                    success = self.assignment_service.archive_assignment(assignment_id)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"Assignment archiving {'successful' if success else 'failed'}"
                        )]
                    )
                
                elif name == "get_assignment_metrics":
                    assignment_id = arguments["assignment_id"]
                    assignment_config = self.assignment_service.get_assignment(assignment_id)
                    if not assignment_config:
                        return CallToolResult(
                            content=[TextContent(
                                type="text",
                                text=f"Assignment {assignment_id} not found"
                            )]
                        )
                    
                    metrics = await self.metrics_aggregator.get_all_metrics(assignment_config)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(metrics, indent=2)
                        )]
                    )
                
                elif name == "get_aws_insights":
                    insights = self.aws_metrics.get_comprehensive_aws_report()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(insights, indent=2)
                        )]
                    )
                
                elif name == "get_github_metrics":
                    repo = arguments["repo"]
                    org = arguments.get("org")
                    metrics = self.github_metrics.get_repo_metrics(repo, org)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(metrics, indent=2)
                        )]
                    )
                
                elif name == "get_jira_metrics":
                    project_key = arguments.get("project_key")
                    metrics = self.jira_metrics.get_project_metrics(project_key)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(metrics, indent=2)
                        )]
                    )
                
                elif name == "get_railway_metrics":
                    metrics = await self.railway_metrics.get_deployment_metrics()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(metrics, indent=2)
                        )]
                    )
                
                elif name == "get_cto_insights":
                    assignment_id = arguments["assignment_id"]
                    assignment_config = self.assignment_service.get_assignment(assignment_id)
                    if not assignment_config:
                        return CallToolResult(
                            content=[TextContent(
                                type="text",
                                text=f"Assignment {assignment_id} not found"
                            )]
                        )
                    
                    aws_config = assignment_config.get("metrics_config", {}).get("aws", {})
                    if not aws_config.get("enabled", False):
                        return CallToolResult(
                            content=[TextContent(
                                type="text",
                                text="AWS metrics not enabled for this assignment"
                            )]
                        )
                    
                    comprehensive_report = self.aws_metrics.get_comprehensive_aws_report()
                    comprehensive_report["assignment_info"] = {
                        "id": assignment_config.get("id"),
                        "name": assignment_config.get("name"),
                        "monthly_burn_rate": assignment_config.get("monthly_burn_rate"),
                        "team_size": assignment_config.get("team_size")
                    }
                    
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(comprehensive_report, indent=2)
                        )]
                    )
                
                elif name == "get_cost_optimization_recommendations":
                    recommendations = self.aws_metrics._get_cost_optimization_recommendations()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text="\n".join(recommendations)
                        )]
                    )
                
                elif name == "get_health_status":
                    health_status = {
                        "status": "healthy",
                        "timestamp": datetime.utcnow().isoformat(),
                        "services": {
                            "github": "configured" if os.getenv("GITHUB_TOKEN") else "not_configured",
                            "jira": "configured" if os.getenv("JIRA_TOKEN") else "not_configured",
                            "aws": "configured" if os.getenv("AWS_ACCESS_KEY_ID") else "not_configured",
                            "railway": "configured" if os.getenv("RAILWAY_TOKEN") else "not_configured"
                        )
                    }
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(health_status, indent=2)
                        )]
                    )
                
                elif name == "get_service_configuration":
                    config_status = {
                        "github": {
                            "token_configured": bool(os.getenv("GITHUB_TOKEN")),
                            "org": os.getenv("GITHUB_ORG", ""),
                            "api_url": os.getenv("GITHUB_API_URL", "https://api.github.com")
                        ),
                        "jira": {
                            "url": os.getenv("JIRA_URL", ""),
                            "email": os.getenv("JIRA_EMAIL", ""),
                            "token_configured": bool(os.getenv("JIRA_TOKEN")),
                            "project_key": os.getenv("JIRA_PROJECT_KEY", "")
                        ),
                        "aws": {
                            "access_key_configured": bool(os.getenv("AWS_ACCESS_KEY_ID")),
                            "secret_key_configured": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
                            "region": os.getenv("AWS_REGION", "us-east-1")
                        ),
                        "railway": {
                            "token_configured": bool(os.getenv("RAILWAY_TOKEN")),
                            "project_id": os.getenv("RAILWAY_PROJECT_ID", ""),
                            "api_url": os.getenv("RAILWAY_API_URL", "https://backboard.railway.app/graphql")
                        )
                    }
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(config_status, indent=2)
                        )]
                    )
                
                # Chatbot tools
                elif name == "ask_chatbot":
                    question = arguments["question"]
                    user_id = arguments.get("user_id", "default")
                    
                    response = await chatbot_service.process_question(question, user_id)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(response, indent=2)
                        )]
                    )
                
                elif name == "get_chatbot_history":
                    user_id = arguments.get("user_id", "default")
                    limit = arguments.get("limit", 10)
                    
                    history = chatbot_service.get_conversation_history(user_id, limit)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps({"history": history}, indent=2)
                        )]
                    )
                
                elif name == "clear_chatbot_history":
                    user_id = arguments.get("user_id", "default")
                    
                    chatbot_service.clear_conversation_history(user_id)
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps({"message": "Conversation history cleared"}, indent=2)
                        )]
                    )
                
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"Unknown tool: {name}"
                        )]
                    )
                    
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )]
                )
        
        @self.server.list_resources()
        async def list_resources() -> ListResourcesResult:
            """List all available resources"""
            return ListResourcesResult(
                resources=[
                    Resource(
                        uri="assignments://active",
                        name="Active Assignments",
                        description="All active assignment configurations",
                        mimeType="application/json"
                    ),
                    Resource(
                        uri="assignments://archived",
                        name="Archived Assignments",
                        description="All archived assignment configurations",
                        mimeType="application/json"
                    ),
                    Resource(
                        uri="assignments://all",
                        name="All Assignments",
                        description="All assignment configurations (active and archived)",
                        mimeType="application/json"
                    ),
                    Resource(
                        uri="config://service-status",
                        name="Service Configuration Status",
                        description="Configuration status of all external services",
                        mimeType="application/json"
                    ),
                    Resource(
                        uri="docs://api-endpoints",
                        name="API Endpoints Documentation",
                        description="Documentation of all available API endpoints",
                        mimeType="text/plain"
                    )
                ]
            )
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> ReadResourceResult:
            """Read a specific resource"""
            try:
                if uri == "assignments://active":
                    assignments = self.assignment_service.get_all_assignments(include_archived=False)
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(assignments, indent=2)
                        )]
                    )
                
                elif uri == "assignments://archived":
                    assignments = self.assignment_service.get_all_assignments(include_archived=True)
                    archived = [a for a in assignments if a.get("status") == "archived"]
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(archived, indent=2)
                        )]
                    )
                
                elif uri == "assignments://all":
                    assignments = self.assignment_service.get_all_assignments(include_archived=True)
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(assignments, indent=2)
                        )]
                    )
                
                elif uri == "config://service-status":
                    config_status = {
                        "github": {
                            "token_configured": bool(os.getenv("GITHUB_TOKEN")),
                            "org": os.getenv("GITHUB_ORG", ""),
                            "api_url": os.getenv("GITHUB_API_URL", "https://api.github.com")
                        ),
                        "jira": {
                            "url": os.getenv("JIRA_URL", ""),
                            "email": os.getenv("JIRA_EMAIL", ""),
                            "token_configured": bool(os.getenv("JIRA_TOKEN")),
                            "project_key": os.getenv("JIRA_PROJECT_KEY", "")
                        ),
                        "aws": {
                            "access_key_configured": bool(os.getenv("AWS_ACCESS_KEY_ID")),
                            "secret_key_configured": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
                            "region": os.getenv("AWS_REGION", "us-east-1")
                        ),
                        "railway": {
                            "token_configured": bool(os.getenv("RAILWAY_TOKEN")),
                            "project_id": os.getenv("RAILWAY_PROJECT_ID", ""),
                            "api_url": os.getenv("RAILWAY_API_URL", "https://backboard.railway.app/graphql")
                        )
                    }
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(config_status, indent=2)
                        )]
                    )
                
                elif uri == "docs://api-endpoints":
                    api_docs = """
CTO Dashboard API Endpoints

Base URL: /api

GET /api
- Returns API status and message

GET /api/health
- Returns health status of all configured services
- Response includes service configuration status

GET /api/assignments
- Returns all assignments
- Query parameter: include_archived (boolean, default: false)

GET /api/assignments/{assignment_id}
- Returns specific assignment configuration
- Path parameter: assignment_id (string)

GET /api/assignments/{assignment_id}/metrics
- Returns real-time metrics for specific assignment
- Path parameter: assignment_id (string)
- Returns aggregated metrics from all configured services

GET /api/assignments/{assignment_id}/cto-insights
- Returns detailed CTO-level insights for specific assignment
- Path parameter: assignment_id (string)
- Returns comprehensive AWS cost analysis and recommendations

Frontend Integration:
- React frontend consumes these endpoints
- Uses VITE_API_URL environment variable for API base URL
- Handles loading states and error conditions
- Displays metrics in expandable sections

MCP Server Integration:
- All API endpoints are exposed as MCP tools
- Resources provide access to assignment configurations
- Standardized interface for AI assistants and tools
                    """
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=api_docs
                        )]
                    )
                
                else:
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=f"Unknown resource: {uri}"
                        )]
                    )
                    
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                return ReadResourceResult(
                    contents=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )]
                )

async def main():
    """Main entry point for the MCP server"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Create and run the MCP server
    mcp_server = CTODashboardMCPServer()
    
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="cto-dashboard-mcp",
                server_version="1.0.0",
                capabilities=mcp_server.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
