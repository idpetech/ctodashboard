#!/usr/bin/env python3
"""
CTO Dashboard MCP Tools Reference and Python Client
Complete guide to available tools and external Python integration
"""

import requests
import json
from typing import Dict, Any, Optional

# MCP Server Configuration
MCP_BASE_URL = "http://localhost:8520/api/mcp"
AUTH_TOKEN = None  # Set this with your actual token

class CTODashboardMCPClient:
    """Python client for external MCP server access"""
    
    def __init__(self, base_url: str = MCP_BASE_URL, auth_token: Optional[str] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.session = requests.Session()
        
        if auth_token:
            self.session.headers.update({
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            })
    
    def health_check(self) -> Dict[str, Any]:
        """Check MCP server health (no auth required)"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def list_tools(self, workspace_id: str) -> Dict[str, Any]:
        """List all available MCP tools for workspace"""
        response = self.session.get(f"{self.base_url}/{workspace_id}/tools")
        response.raise_for_status()
        return response.json()
    
    def call_tool(self, workspace_id: str, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a specific MCP tool"""
        if arguments is None:
            arguments = {}
            
        response = self.session.post(
            f"{self.base_url}/{workspace_id}/tools/{tool_name}",
            json=arguments
        )
        response.raise_for_status()
        return response.json()
    
    def list_resources(self, workspace_id: str) -> Dict[str, Any]:
        """List available MCP resources"""
        response = self.session.get(f"{self.base_url}/{workspace_id}/resources")
        response.raise_for_status()
        return response.json()
    
    def workspace_chatbot(self, workspace_id: str, question: str, assignment_id: Optional[str] = None) -> Dict[str, Any]:
        """Ask the workspace-aware chatbot"""
        data = {"question": question}
        if assignment_id:
            data["assignment_id"] = assignment_id
            
        response = self.session.post(
            f"{self.base_url}/{workspace_id}/chatbot",
            json=data
        )
        response.raise_for_status()
        return response.json()

def print_available_tools():
    """Display all available MCP tools with descriptions"""
    tools = {
        "🏢 Workspace Management": {
            "get_workspace_assignments": {
                "description": "Get all assignments in the current workspace",
                "parameters": {
                    "workspace_id": "string (optional, uses context if not provided)"
                },
                "example": {
                    "workspace_id": "my_workspace"
                }
            }
        },
        
        "🤖 AI Chatbot": {
            "ask_chatbot": {
                "description": "Ask the AI chatbot general questions",
                "parameters": {
                    "question": "string (required)",
                    "user_id": "string (optional, default: 'default')"
                },
                "example": {
                    "question": "What is the status of my services?",
                    "user_id": "john_doe"
                }
            },
            "ask_workspace_chatbot": {
                "description": "Ask AI chatbot with full workspace and assignment context",
                "parameters": {
                    "question": "string (required)",
                    "workspace_id": "string (optional, uses context)",
                    "assignment_id": "string (optional, for additional context)"
                },
                "example": {
                    "question": "How are my GitHub repositories performing?",
                    "assignment_id": "project_alpha"
                }
            },
            "get_chatbot_history": {
                "description": "Get chatbot conversation history for a user",
                "parameters": {
                    "user_id": "string (optional, default: 'default')",
                    "limit": "integer (optional, default: 10)"
                },
                "example": {
                    "user_id": "john_doe",
                    "limit": 20
                }
            },
            "clear_chatbot_history": {
                "description": "Clear chatbot conversation history for a user",
                "parameters": {
                    "user_id": "string (optional, default: 'default')"
                },
                "example": {
                    "user_id": "john_doe"
                }
            }
        },
        
        "☁️ Cloud Services": {
            "get_aws_insights": {
                "description": "Get comprehensive AWS cost and resource insights",
                "parameters": {},
                "example": {}
            },
            "get_cost_optimization_recommendations": {
                "description": "Get AWS cost optimization recommendations",
                "parameters": {},
                "example": {}
            },
            "get_cto_insights": {
                "description": "Get detailed CTO-level insights for an assignment",
                "parameters": {
                    "assignment_id": "string (required)"
                },
                "example": {
                    "assignment_id": "project_alpha"
                }
            }
        },
        
        "🐙 Development Tools": {
            "get_github_metrics": {
                "description": "Get GitHub repository metrics",
                "parameters": {
                    "repo": "string (required)",
                    "org": "string (optional)"
                },
                "example": {
                    "repo": "my-awesome-project",
                    "org": "my-company"
                }
            },
            "get_jira_metrics": {
                "description": "Get Jira project metrics",
                "parameters": {
                    "project_key": "string (optional)"
                },
                "example": {
                    "project_key": "PROJ"
                }
            },
            "get_railway_metrics": {
                "description": "Get Railway deployment metrics",
                "parameters": {},
                "example": {}
            }
        },
        
        "🔧 System Status": {
            "get_health_status": {
                "description": "Get health status of all configured services",
                "parameters": {},
                "example": {}
            },
            "get_service_configuration": {
                "description": "Get configuration status of all services",
                "parameters": {},
                "example": {}
            }
        },
        
        "📊 Assignment Metrics": {
            "get_assignment_metrics": {
                "description": "Get real-time metrics for a specific assignment",
                "parameters": {
                    "assignment_id": "string (required)"
                },
                "example": {
                    "assignment_id": "project_alpha"
                },
                "note": "Currently returns placeholder in workspace mode"
            }
        }
    }
    
    print("🚀 CTO Dashboard MCP Tools Reference")
    print("=" * 50)
    
    for category, category_tools in tools.items():
        print(f"\n{category}")
        print("-" * (len(category) - 2))  # Subtract emoji length
        
        for tool_name, tool_info in category_tools.items():
            print(f"\n📋 {tool_name}")
            print(f"   Description: {tool_info['description']}")
            
            if tool_info['parameters']:
                print(f"   Parameters:")
                for param, param_type in tool_info['parameters'].items():
                    print(f"     • {param}: {param_type}")
            else:
                print(f"   Parameters: None required")
            
            if tool_info['example']:
                print(f"   Example: {json.dumps(tool_info['example'], indent=6)[6:-6]}")
            
            if 'note' in tool_info:
                print(f"   Note: {tool_info['note']}")

def example_usage():
    """Demonstrate how to use the MCP client"""
    print("\n🔧 Python Client Usage Examples")
    print("=" * 50)
    
    client_code = '''
# 1. Initialize the client
from mcp_tools_reference import CTODashboardMCPClient

# Without authentication (health check only)
client = CTODashboardMCPClient()

# With authentication
client = CTODashboardMCPClient(auth_token="your_bearer_token_here")

# 2. Health check (no auth required)
health = client.health_check()
print(f"MCP Server Status: {health['status']}")

# 3. List available tools (requires auth)
workspace_id = "my_workspace"
tools = client.list_tools(workspace_id)
print(f"Available tools: {len(tools['tools'])}")

# 4. Ask workspace chatbot (requires auth)
response = client.workspace_chatbot(
    workspace_id="my_workspace",
    question="What's the current status of my AWS infrastructure?",
    assignment_id="production_env"
)
print(f"Chatbot response: {response['response']}")

# 5. Get AWS insights (requires auth)
aws_insights = client.call_tool(
    workspace_id="my_workspace",
    tool_name="get_aws_insights"
)
print(f"AWS insights: {aws_insights['result']}")

# 6. Get GitHub metrics (requires auth)
github_metrics = client.call_tool(
    workspace_id="my_workspace",
    tool_name="get_github_metrics",
    arguments={
        "repo": "my-project",
        "org": "my-company"
    }
)
print(f"GitHub metrics: {github_metrics['result']}")

# 7. Get workspace assignments (requires auth)
assignments = client.call_tool(
    workspace_id="my_workspace",
    tool_name="get_workspace_assignments"
)
print(f"Assignments: {assignments['result']}")

# 8. Get service health status (requires auth)
health_status = client.call_tool(
    workspace_id="my_workspace",
    tool_name="get_health_status"
)
print(f"Service health: {health_status['result']}")
'''
    
    print(client_code)

def authentication_guide():
    """Guide for getting authentication tokens"""
    print("\n🔐 Authentication Guide")
    print("=" * 50)
    
    auth_guide = '''
To use the MCP server externally, you need a Bearer token. Here are the methods:

METHOD 1: Session Token (from logged-in browser)
1. Log into the CTO Dashboard at http://localhost:8520
2. Open browser developer tools (F12)
3. Go to Application/Storage tab
4. Find session cookie or look for auth token in localStorage
5. Use that token as Bearer token

METHOD 2: API Login (if available)
POST /api/auth/login
Content-Type: application/json
{
  "email": "your@email.com",
  "password": "your_password"
}

Response will contain token:
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {...}
}

METHOD 3: Direct Token Creation (for testing)
If you have database access, you can create a test token directly.

USAGE:
All protected endpoints require:
Authorization: Bearer YOUR_TOKEN_HERE

EXAMPLE CURL:
curl -H "Authorization: Bearer YOUR_TOKEN" \\
     http://localhost:8520/api/mcp/my_workspace/tools
'''
    
    print(auth_guide)

def integration_examples():
    """Real-world integration examples"""
    print("\n🌐 Real-World Integration Examples")
    print("=" * 50)
    
    examples = '''
# Example 1: CI/CD Pipeline Integration
import os
from mcp_tools_reference import CTODashboardMCPClient

def check_deployment_health():
    client = CTODashboardMCPClient(auth_token=os.getenv('CTO_DASHBOARD_TOKEN'))
    
    # Get service health
    health = client.call_tool('production', 'get_health_status')
    
    # Get AWS insights
    aws = client.call_tool('production', 'get_aws_insights')
    
    # Ask AI for analysis
    analysis = client.workspace_chatbot(
        'production',
        'Based on current metrics, is it safe to deploy?'
    )
    
    return {
        'safe_to_deploy': health['result']['status'] == 'healthy',
        'aws_status': aws['result'],
        'ai_recommendation': analysis['response']
    }

# Example 2: Monitoring Dashboard
def get_executive_summary():
    client = CTODashboardMCPClient(auth_token=os.getenv('CTO_DASHBOARD_TOKEN'))
    
    workspaces = ['production', 'staging', 'development']
    summary = {}
    
    for workspace in workspaces:
        summary[workspace] = {
            'assignments': client.call_tool(workspace, 'get_workspace_assignments'),
            'health': client.call_tool(workspace, 'get_health_status'),
            'ai_summary': client.workspace_chatbot(
                workspace, 
                'Give me a brief executive summary of this workspace'
            )
        }
    
    return summary

# Example 3: Slack Bot Integration
def slack_bot_handler(workspace_id, question):
    client = CTODashboardMCPClient(auth_token=os.getenv('CTO_DASHBOARD_TOKEN'))
    
    # Ask the workspace-aware chatbot
    response = client.workspace_chatbot(workspace_id, question)
    
    # Format for Slack
    return {
        'text': response['response']['answer'],
        'attachments': [{
            'color': 'good' if 'error' not in response else 'danger',
            'fields': [
                {'title': 'Workspace', 'value': workspace_id, 'short': True},
                {'title': 'Confidence', 'value': f"{response.get('confidence', 0)}%", 'short': True}
            ]
        }]
    }

# Example 4: Cost Monitoring Alert
def check_cost_alerts():
    client = CTODashboardMCPClient(auth_token=os.getenv('CTO_DASHBOARD_TOKEN'))
    
    # Get AWS cost insights
    aws_insights = client.call_tool('production', 'get_aws_insights')
    
    # Get cost recommendations
    recommendations = client.call_tool('production', 'get_cost_optimization_recommendations')
    
    # Ask AI to analyze
    analysis = client.workspace_chatbot(
        'production',
        'Are there any urgent cost optimization opportunities I should know about?'
    )
    
    return {
        'current_costs': aws_insights['result'],
        'recommendations': recommendations['result'],
        'ai_analysis': analysis['response']
    }
'''
    
    print(examples)

def main():
    """Main function to display all information"""
    print_available_tools()
    example_usage()
    authentication_guide()
    integration_examples()
    
    print("\n🚀 Quick Start")
    print("=" * 50)
    print("1. Copy this file to your project")
    print("2. Install requests: pip install requests")
    print("3. Get your auth token (see Authentication Guide above)")
    print("4. Initialize client: client = CTODashboardMCPClient(auth_token='your_token')")
    print("5. Start calling tools!")
    print("\n📍 MCP Server URL: http://localhost:8520/api/mcp")
    print("📋 Health Check: curl http://localhost:8520/api/mcp/health")

if __name__ == "__main__":
    main()