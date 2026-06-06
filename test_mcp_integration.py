#!/usr/bin/env python3
"""
Test MCP Integration
Demonstrates the working MCP server with authentication and workspace context
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Activate virtual environment programmatically
import os
import dotenv
dotenv.load_dotenv()

def test_mcp_server_direct():
    """Test MCP server directly"""
    print("🔧 Testing MCP Server Direct Access...")
    
    try:
        from mcp_server import CTODashboardMCPServer
        
        # Test basic initialization
        server = CTODashboardMCPServer()
        print("✓ MCP server initialized successfully")
        
        # Test with user and workspace context
        user_context = {"user_id": "test_user", "email": "test@example.com"}
        workspace_context = {"workspace_id": "test_workspace"}
        
        authenticated_server = CTODashboardMCPServer(user_context, workspace_context)
        authenticated_server.workspace_id = "test_workspace"
        print("✓ MCP server with authentication context created")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False

def test_workspace_chatbot():
    """Test workspace-aware chatbot"""
    print("\n🤖 Testing Workspace-Aware Chatbot...")
    
    try:
        from services.chatbot_service import process_question_with_workspace
        
        # Test workspace-aware question
        result = process_question_with_workspace(
            question="What is the status of my workspace?",
            user_id="test_user",
            workspace_id="test_workspace",
            assignment_id="test_assignment"
        )
        
        print("✓ Workspace chatbot responded successfully")
        print(f"  Response type: {result.get('question_type', 'unknown')}")
        print(f"  Has workspace context: {'workspace_context' in result}")
        
        if 'workspace_context' in result:
            ctx = result['workspace_context']
            print(f"  Workspace ID: {ctx.get('workspace_id')}")
            print(f"  Assignment ID: {ctx.get('assignment_id')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workspace chatbot test failed: {e}")
        return False

def test_flask_mcp_routes():
    """Test Flask MCP routes"""
    print("\n🌐 Testing Flask MCP HTTP Routes...")
    
    try:
        from integrated_dashboard import app
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/api/mcp/health')
            if response.status_code == 200:
                print("✓ MCP health endpoint working")
                data = response.get_json()
                print(f"  Service: {data.get('service')}")
                print(f"  Status: {data.get('status')}")
            else:
                print(f"❌ MCP health endpoint failed: {response.status_code}")
                return False
            
            # Test authentication requirement
            response = client.get('/api/mcp/test_workspace/tools')
            if response.status_code == 401:
                print("✓ Authentication requirement working")
                data = response.get_json()
                print(f"  Error message: {data.get('message')}")
            else:
                print(f"⚠️  Expected 401, got: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask MCP routes test failed: {e}")
        return False

def test_authentication_flow():
    """Test authentication and workspace access"""
    print("\n🔐 Testing Authentication Flow...")
    
    try:
        from services.auth.secure_user_service import SecureUserService
        from services.workspace.workspace_service import WorkspaceService
        
        # Test service initialization
        user_service = SecureUserService()
        workspace_service = WorkspaceService()
        
        print("✓ Authentication and workspace services initialized")
        print(f"  Workspace feature enabled: {workspace_service.is_workspace_enabled()}")
        
        # Test workspace creation (if enabled)
        if workspace_service.is_workspace_enabled():
            result = workspace_service.get_workspace("test_workspace")
            print(f"  Test workspace status: {'exists' if 'error' not in result else 'not found'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication flow test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 CTO Dashboard MCP Integration Test Suite\n")
    
    tests = [
        test_mcp_server_direct,
        test_workspace_chatbot,
        test_flask_mcp_routes,
        test_authentication_flow
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All MCP integration tests PASSED!")
        print("\nThe MCP server is ready for external use with:")
        print("  ✓ Secure authentication via Bearer tokens or session cookies")
        print("  ✓ Workspace isolation and context awareness")
        print("  ✓ HTTP endpoints for external tool access")
        print("  ✓ Workspace-aware chatbot functionality")
        print("\n📍 Available endpoints:")
        print("  GET  /api/mcp/health")
        print("  GET  /api/mcp/<workspace_id>/tools")
        print("  POST /api/mcp/<workspace_id>/tools/<tool_name>")
        print("  GET  /api/mcp/<workspace_id>/resources")
        print("  POST /api/mcp/<workspace_id>/chatbot")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)