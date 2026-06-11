"""
MCP HTTP Routes - Secure External MCP Server Access
Provides authenticated HTTP endpoints for MCP protocol over REST
"""

import asyncio
import json
from functools import wraps

from flask import Blueprint, g, jsonify, request

from config.logging_config import get_logger
from mcp_server import CTODashboardMCPServer
from services.auth.auth_middleware import create_auth_decorators
from services.auth.secure_user_service import SecureUserService
from services.workspace.workspace_service import WorkspaceService

logger = get_logger(__name__)

# Initialize services
user_service = SecureUserService()
workspace_service = WorkspaceService()

# Create auth decorators
(
    require_auth,
    require_workspace_access,
    optional_auth,
    require_web_auth,
    require_web_workspace_access,
    _require_admin,
) = create_auth_decorators(user_service)

# Global MCP server instances per workspace
_mcp_servers = {}


def get_workspace_mcp_server(workspace_id: str, user_context: dict) -> CTODashboardMCPServer:
    """Get or create MCP server instance for workspace with user context"""
    server_key = f"{workspace_id}:{user_context.get('email', 'unknown')}"

    if server_key not in _mcp_servers:
        logger.info(
            "Creating new MCP server instance",
            extra={
                "workspace_id": workspace_id,
                "user_email": user_context.get("email"),
                "operation": "mcp_server_create",
            },
        )

        # Create server with workspace context
        server = CTODashboardMCPServer()
        server.workspace_id = workspace_id
        server.user_context = user_context
        _mcp_servers[server_key] = server

    return _mcp_servers[server_key]


def async_route(f):
    """Decorator to run async functions in Flask routes"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()

    return wrapper


# Create Blueprint
mcp_bp = Blueprint("mcp", __name__, url_prefix="/api/mcp")


@mcp_bp.route("/health", methods=["GET"])
def mcp_health():
    """MCP server health check"""
    return jsonify({"status": "healthy", "service": "mcp-http-gateway", "version": "1.0.0"})


@mcp_bp.route("/<workspace_id>/tools", methods=["GET"])
@require_workspace_access
@async_route
async def list_workspace_tools(workspace_id):
    """List available MCP tools for authenticated workspace"""
    try:
        user_context = {
            "email": g.current_user["email"],
            "user_id": g.current_user.get("id", g.current_user["email"]),
        }

        # Get MCP server for this workspace
        mcp_server = get_workspace_mcp_server(workspace_id, user_context)

        # Get tools list
        tools_result = await mcp_server._register_handlers.__wrapped__(mcp_server).list_tools()

        logger.info(
            "MCP tools listed",
            extra={
                "workspace_id": workspace_id,
                "user_email": user_context["email"],
                "tool_count": len(tools_result.tools),
                "operation": "mcp_list_tools",
            },
        )

        return jsonify(
            {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                    }
                    for tool in tools_result.tools
                ]
            }
        )

    except Exception as e:
        logger.error(
            "Failed to list MCP tools",
            extra={"workspace_id": workspace_id, "error": str(e), "operation": "mcp_list_tools"},
            exc_info=e,
        )

        return jsonify({"error": "Failed to list tools", "message": str(e)}), 500


@mcp_bp.route("/<workspace_id>/tools/<tool_name>", methods=["POST"])
@require_workspace_access
@async_route
async def call_workspace_tool(workspace_id, tool_name):
    """Call MCP tool with workspace authentication and context"""
    try:
        user_context = {
            "email": g.current_user["email"],
            "user_id": g.current_user.get("id", g.current_user["email"]),
        }

        # Get request arguments
        args = request.get_json() or {}

        # Add workspace context to arguments if not present
        if "workspace_id" not in args:
            args["workspace_id"] = workspace_id

        # Get MCP server for this workspace
        mcp_server = get_workspace_mcp_server(workspace_id, user_context)

        # Call the tool
        result = await mcp_server._register_handlers.__wrapped__(mcp_server).call_tool(
            tool_name, args
        )

        logger.info(
            "MCP tool called",
            extra={
                "workspace_id": workspace_id,
                "tool_name": tool_name,
                "user_email": user_context["email"],
                "operation": "mcp_call_tool",
            },
        )

        # Extract text content from MCP result
        if result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, "text"):
                try:
                    # Try to parse as JSON for structured responses
                    response_data = json.loads(content.text)
                    return jsonify({"success": True, "result": response_data})
                except json.JSONDecodeError:
                    # Return as plain text
                    return jsonify({"success": True, "result": content.text})
            else:
                return jsonify({"success": True, "result": str(content)})
        else:
            return jsonify({"success": True, "result": "Tool executed successfully"})

    except Exception as e:
        logger.error(
            "Failed to call MCP tool",
            extra={
                "workspace_id": workspace_id,
                "tool_name": tool_name,
                "error": str(e),
                "operation": "mcp_call_tool",
            },
            exc_info=e,
        )

        return jsonify({"error": "Failed to call tool", "message": str(e)}), 500


@mcp_bp.route("/<workspace_id>/resources", methods=["GET"])
@require_workspace_access
@async_route
async def list_workspace_resources(workspace_id):
    """List available MCP resources for authenticated workspace"""
    try:
        user_context = {
            "email": g.current_user["email"],
            "user_id": g.current_user.get("id", g.current_user["email"]),
        }

        # Get MCP server for this workspace
        mcp_server = get_workspace_mcp_server(workspace_id, user_context)

        # Get resources list
        resources_result = await mcp_server._register_handlers.__wrapped__(
            mcp_server
        ).list_resources()

        return jsonify(
            {
                "resources": [
                    {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mimeType": resource.mimeType,
                    }
                    for resource in resources_result.resources
                ]
            }
        )

    except Exception as e:
        logger.error(
            "Failed to list MCP resources",
            extra={
                "workspace_id": workspace_id,
                "error": str(e),
                "operation": "mcp_list_resources",
            },
            exc_info=e,
        )

        return jsonify({"error": "Failed to list resources", "message": str(e)}), 500


@mcp_bp.route("/<workspace_id>/resources/<path:resource_uri>", methods=["GET"])
@require_workspace_access
@async_route
async def read_workspace_resource(workspace_id, resource_uri):
    """Read MCP resource with workspace authentication"""
    try:
        user_context = {
            "email": g.current_user["email"],
            "user_id": g.current_user.get("id", g.current_user["email"]),
        }

        # Get MCP server for this workspace
        mcp_server = get_workspace_mcp_server(workspace_id, user_context)

        # Read the resource
        result = await mcp_server._register_handlers.__wrapped__(mcp_server).read_resource(
            resource_uri
        )

        # Extract content from MCP result
        if result.contents and len(result.contents) > 0:
            content = result.contents[0]
            if hasattr(content, "text"):
                return jsonify({"success": True, "uri": resource_uri, "content": content.text})
            else:
                return jsonify({"success": True, "uri": resource_uri, "content": str(content)})
        else:
            return jsonify({"success": True, "uri": resource_uri, "content": ""})

    except Exception as e:
        logger.error(
            "Failed to read MCP resource",
            extra={
                "workspace_id": workspace_id,
                "resource_uri": resource_uri,
                "error": str(e),
                "operation": "mcp_read_resource",
            },
            exc_info=e,
        )

        return jsonify({"error": "Failed to read resource", "message": str(e)}), 500


@mcp_bp.route("/<workspace_id>/chatbot", methods=["POST"])
@require_workspace_access
@async_route
async def workspace_chatbot(workspace_id):
    """Workspace-aware chatbot via MCP with full context"""
    try:
        user_context = {
            "email": g.current_user["email"],
            "user_id": g.current_user.get("id", g.current_user["email"]),
        }

        data = request.get_json() or {}
        question = data.get("question", "")
        assignment_id = data.get("assignment_id")
        fetch_metrics = bool(data.get("fetch_metrics", False))
        skip_metrics_fetch = bool(data.get("skip_metrics_fetch", False))

        if not question:
            return jsonify({"error": "Question is required"}), 400

        from services.chatbot_service import process_question_with_workspace

        result = process_question_with_workspace(
            question,
            user_context["user_id"],
            workspace_id,
            assignment_id,
            fetch_metrics=fetch_metrics,
            skip_metrics_fetch=skip_metrics_fetch,
        )
        return jsonify(
            {
                "success": True,
                "response": result,
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
            }
        )

    except Exception as e:
        logger.error(
            "Workspace chatbot failed",
            extra={"workspace_id": workspace_id, "error": str(e), "operation": "workspace_chatbot"},
            exc_info=e,
        )

        return jsonify({"error": "Chatbot request failed", "message": str(e)}), 500


# Register error handlers
@mcp_bp.errorhandler(401)
def unauthorized(error):
    return jsonify(
        {"error": "Unauthorized", "message": "Authentication required for MCP access"}
    ), 401


@mcp_bp.errorhandler(403)
def forbidden(error):
    return jsonify(
        {"error": "Forbidden", "message": "Insufficient permissions for workspace access"}
    ), 403


@mcp_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "message": "MCP endpoint not found"}), 404
