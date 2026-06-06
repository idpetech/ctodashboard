#!/usr/bin/env python3
"""
Test MCP Client - Demonstrates external Python connection to MCP server
Run this to see the MCP tools in action
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_tools_reference import CTODashboardMCPClient

def test_public_endpoints():
    """Test endpoints that don't require authentication"""
    print("🔍 Testing Public Endpoints (No Auth Required)")
    print("=" * 50)
    
    client = CTODashboardMCPClient()
    
    try:
        # Test health check
        health = client.health_check()
        print(f"✅ Health Check: {health}")
        return True
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        return False

def test_authenticated_endpoints():
    """Test endpoints that require authentication"""
    print("\n🔐 Testing Authenticated Endpoints")
    print("=" * 50)
    
    # For demo purposes, we'll test without a real token to show the auth requirement
    client = CTODashboardMCPClient(auth_token="demo_token_for_testing")
    workspace_id = "test_workspace"
    
    endpoints_to_test = [
        ("List Tools", lambda: client.list_tools(workspace_id)),
        ("List Resources", lambda: client.list_resources(workspace_id)),
        ("Workspace Chatbot", lambda: client.workspace_chatbot(workspace_id, "What is my workspace status?")),
        ("Get Health Status", lambda: client.call_tool(workspace_id, "get_health_status")),
        ("Get AWS Insights", lambda: client.call_tool(workspace_id, "get_aws_insights")),
    ]
    
    for name, test_func in endpoints_to_test:
        try:
            result = test_func()
            print(f"✅ {name}: Success")
            if isinstance(result, dict) and 'error' not in result:
                print(f"   Response preview: {str(result)[:100]}...")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                print(f"🔒 {name}: Requires valid authentication (expected)")
            else:
                print(f"❌ {name}: Unexpected error - {e}")

def demonstrate_tool_usage():
    """Show how to use specific tools"""
    print("\n📋 Tool Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "name": "Workspace Chatbot",
            "tool": "ask_workspace_chatbot",
            "description": "AI assistant with workspace context",
            "example_call": "client.workspace_chatbot('my_workspace', 'How is my infrastructure performing?')"
        },
        {
            "name": "AWS Cost Analysis", 
            "tool": "get_aws_insights",
            "description": "Comprehensive AWS cost and resource analysis",
            "example_call": "client.call_tool('my_workspace', 'get_aws_insights')"
        },
        {
            "name": "GitHub Repository Metrics",
            "tool": "get_github_metrics", 
            "description": "Repository activity and team productivity",
            "example_call": "client.call_tool('my_workspace', 'get_github_metrics', {'repo': 'my-project', 'org': 'my-company'})"
        },
        {
            "name": "Service Health Check",
            "tool": "get_health_status",
            "description": "Overall health of all configured services", 
            "example_call": "client.call_tool('my_workspace', 'get_health_status')"
        },
        {
            "name": "Workspace Assignments",
            "tool": "get_workspace_assignments",
            "description": "All assignments in the current workspace",
            "example_call": "client.call_tool('my_workspace', 'get_workspace_assignments')"
        }
    ]
    
    for example in examples:
        print(f"\n📌 {example['name']}")
        print(f"   Tool: {example['tool']}")
        print(f"   Description: {example['description']}")
        print(f"   Usage: {example['example_call']}")

def show_integration_patterns():
    """Show common integration patterns"""
    print("\n🔧 Common Integration Patterns")
    print("=" * 50)
    
    patterns = [
        {
            "pattern": "CI/CD Health Check",
            "description": "Check if it's safe to deploy",
            "code": """
# In your CI/CD pipeline
client = CTODashboardMCPClient(auth_token=os.getenv('CTO_TOKEN'))
health = client.call_tool('production', 'get_health_status')
if health['result']['status'] != 'healthy':
    print("❌ Deployment blocked - unhealthy services")
    sys.exit(1)
"""
        },
        {
            "pattern": "Daily Executive Report",
            "description": "Generate daily summary for leadership",
            "code": """
# Daily report script
def generate_daily_report():
    client = CTODashboardMCPClient(auth_token=TOKEN)
    
    report = client.workspace_chatbot(
        'production',
        'Generate an executive summary of today\\'s key metrics and any issues requiring attention'
    )
    
    send_slack_message(report['response'])
"""
        },
        {
            "pattern": "Cost Alert System", 
            "description": "Monitor and alert on cost changes",
            "code": """
# Cost monitoring
def check_costs():
    client = CTODashboardMCPClient(auth_token=TOKEN)
    
    insights = client.call_tool('production', 'get_aws_insights')
    recommendations = client.call_tool('production', 'get_cost_optimization_recommendations')
    
    if insights['result']['monthly_cost_change'] > 20:
        send_alert(f"Cost increased by {insights['result']['monthly_cost_change']}%")
"""
        },
        {
            "pattern": "Slack Bot Integration",
            "description": "Answer questions via Slack",
            "code": """
# Slack bot handler
@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json
    if data['event']['type'] == 'app_mention':
        question = data['event']['text']
        
        client = CTODashboardMCPClient(auth_token=SLACK_BOT_TOKEN)
        response = client.workspace_chatbot('production', question)
        
        slack_client.chat_postMessage(
            channel=data['event']['channel'],
            text=response['response']['answer']
        )
"""
        }
    ]
    
    for pattern in patterns:
        print(f"\n🎯 {pattern['pattern']}")
        print(f"   {pattern['description']}")
        print(f"   Code:{pattern['code']}")

def main():
    """Run all tests and demonstrations"""
    print("🚀 CTO Dashboard MCP Client Test & Demo")
    print("=" * 60)
    
    # Test public endpoints
    public_ok = test_public_endpoints()
    
    if not public_ok:
        print("\n❌ MCP server not responding. Make sure it's running:")
        print("   python integrated_dashboard.py")
        return False
    
    # Test authenticated endpoints (will show auth requirement)
    test_authenticated_endpoints()
    
    # Show tool usage examples
    demonstrate_tool_usage()
    
    # Show integration patterns
    show_integration_patterns()
    
    print("\n" + "=" * 60)
    print("🎯 Next Steps:")
    print("1. Get a valid auth token (see Authentication Guide)")
    print("2. Replace 'demo_token_for_testing' with real token")
    print("3. Start integrating MCP tools into your workflows!")
    print("\n📖 Full documentation in: mcp_tools_reference.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)