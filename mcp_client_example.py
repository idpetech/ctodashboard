#!/usr/bin/env python3
"""
CTO Dashboard MCP Client Example

This example demonstrates how to connect to and use the CTO Dashboard MCP server
from external applications or AI assistants.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

from mcp.client import Client
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CTODashboardMCPClient:
    """Client for interacting with the CTO Dashboard MCP server"""
    
    def __init__(self):
        self.client = None
        self.connected = False
    
    async def connect(self, server_command: List[str]):
        """Connect to the MCP server"""
        try:
            self.client = await stdio_client(server_command)
            await self.client.initialize()
            self.connected = True
            logger.info("Connected to CTO Dashboard MCP server")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.client:
            await self.client.close()
            self.connected = False
            logger.info("Disconnected from MCP server")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")
        
        result = await self.client.list_tools()
        return [tool.dict() for tool in result.tools]
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources"""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")
        
        result = await self.client.list_resources()
        return [resource.dict() for resource in result.resources]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> str:
        """Call a tool on the MCP server"""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")
        
        if arguments is None:
            arguments = {}
        
        result = await self.client.call_tool(name, arguments)
        
        # Extract text content from result
        if result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    return content.text
                elif hasattr(content, 'type') and content.type == 'text':
                    return content.text
        
        return "No content returned"
    
    async def read_resource(self, uri: str) -> str:
        """Read a resource from the MCP server"""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")
        
        result = await self.client.read_resource(uri)
        
        # Extract text content from result
        if result.contents:
            for content in result.contents:
                if hasattr(content, 'text'):
                    return content.text
                elif hasattr(content, 'type') and content.type == 'text':
                    return content.text
        
        return "No content returned"

async def example_usage():
    """Example of how to use the MCP client"""
    
    # Create client
    client = CTODashboardMCPClient()
    
    try:
        # Connect to the MCP server (assuming it's running)
        server_command = ["python", "mcp_server.py"]
        await client.connect(server_command)
        
        # List available tools
        print("=== Available Tools ===")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")
        
        # List available resources
        print("\n=== Available Resources ===")
        resources = await client.list_resources()
        for resource in resources:
            print(f"- {resource['name']}: {resource['description']}")
        
        # Get health status
        print("\n=== Health Status ===")
        health = await client.call_tool("get_health_status")
        print(health)
        
        # Get all assignments
        print("\n=== All Assignments ===")
        assignments = await client.call_tool("get_assignments", {"include_archived": True})
        print(assignments)
        
        # Get AWS insights
        print("\n=== AWS Insights ===")
        aws_insights = await client.call_tool("get_aws_insights")
        print(aws_insights)
        
        # Read a resource
        print("\n=== API Documentation ===")
        api_docs = await client.read_resource("docs://api-endpoints")
        print(api_docs)
        
    except Exception as e:
        logger.error(f"Error in example usage: {e}")
    
    finally:
        # Disconnect
        await client.disconnect()

async def interactive_mode():
    """Interactive mode for testing MCP client"""
    
    client = CTODashboardMCPClient()
    
    try:
        # Connect to the MCP server
        server_command = ["python", "mcp_server.py"]
        await client.connect(server_command)
        
        print("CTO Dashboard MCP Client - Interactive Mode")
        print("Type 'help' for available commands, 'quit' to exit")
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if command == "quit":
                    break
                elif command == "help":
                    print("Available commands:")
                    print("  tools - List all available tools")
                    print("  resources - List all available resources")
                    print("  health - Get health status")
                    print("  assignments - Get all assignments")
                    print("  aws - Get AWS insights")
                    print("  call <tool_name> [args] - Call a tool")
                    print("  read <resource_uri> - Read a resource")
                    print("  quit - Exit")
                
                elif command == "tools":
                    tools = await client.list_tools()
                    for tool in tools:
                        print(f"- {tool['name']}: {tool['description']}")
                
                elif command == "resources":
                    resources = await client.list_resources()
                    for resource in resources:
                        print(f"- {resource['name']}: {resource['description']}")
                
                elif command == "health":
                    result = await client.call_tool("get_health_status")
                    print(result)
                
                elif command == "assignments":
                    result = await client.call_tool("get_assignments", {"include_archived": True})
                    print(result)
                
                elif command == "aws":
                    result = await client.call_tool("get_aws_insights")
                    print(result)
                
                elif command.startswith("call "):
                    parts = command.split(" ", 2)
                    if len(parts) >= 2:
                        tool_name = parts[1]
                        args = {}
                        if len(parts) == 3:
                            try:
                                args = json.loads(parts[2])
                            except json.JSONDecodeError:
                                print("Invalid JSON arguments")
                                continue
                        
                        result = await client.call_tool(tool_name, args)
                        print(result)
                    else:
                        print("Usage: call <tool_name> [json_arguments]")
                
                elif command.startswith("read "):
                    parts = command.split(" ", 1)
                    if len(parts) == 2:
                        resource_uri = parts[1]
                        result = await client.read_resource(resource_uri)
                        print(result)
                    else:
                        print("Usage: read <resource_uri>")
                
                else:
                    print("Unknown command. Type 'help' for available commands.")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    finally:
        await client.disconnect()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(example_usage())

