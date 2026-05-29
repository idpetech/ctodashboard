"""
API Routes for CTO Dashboard
Extracted from integrated_dashboard.py for clean separation
"""

from flask import jsonify, render_template, request, send_from_directory
import os
import json
from datetime import datetime, timedelta
from services.service_manager import ServiceManager
from services.embedded.aws_metrics import EmbeddedAWSMetrics
from services.embedded.github_metrics import EmbeddedGitHubMetrics
from services.embedded.jira_metrics import EmbeddedJiraMetrics
from services.embedded.openai_metrics import OpenAIMetrics
from services.embedded.railway_metrics import RailwayMetrics
from services.chatbot_service import process_question, process_question_stream, get_conversation_history, clear_conversation_history
from services.assignment_service import AssignmentService
from services.workspace.workspace_service import WorkspaceService
from services.auth.user_service import UserService
from services.auth.auth_middleware import create_auth_decorators, get_current_user

# Initialize services
service_manager = ServiceManager()
assignment_service = AssignmentService()
workspace_service = WorkspaceService()
user_service = UserService()

# Create authentication decorators with dependency injection
auth_decorators = create_auth_decorators(user_service)
require_auth, require_workspace_access, optional_auth = auth_decorators[:3]
require_web_auth, require_web_workspace_access = auth_decorators[3:5] if len(auth_decorators) >= 5 else (None, None)

# Global connector instances (for backward compatibility)
aws_metrics = EmbeddedAWSMetrics()
github_metrics = EmbeddedGitHubMetrics()
jira_metrics = EmbeddedJiraMetrics()
openai_metrics = OpenAIMetrics()
railway_metrics = RailwayMetrics()

def get_workspace_connectors(workspace_id, assignment_id):
    """
    Create workspace-scoped connector instances with credentials from assignment JSON.
    Phase 3: Enable workspace-specific authentication instead of global env vars.
    """
    return {
        'github': EmbeddedGitHubMetrics(workspace_id=workspace_id, assignment_id=assignment_id),
        'jira': EmbeddedJiraMetrics(workspace_id=workspace_id, assignment_id=assignment_id),
        'aws': EmbeddedAWSMetrics(workspace_id=workspace_id, assignment_id=assignment_id)
    }

def register_routes(app):
    """Register all routes with the Flask app"""
    
    @app.route("/")
    def index():
        """Main dashboard page"""
        return render_template("dashboard.html")
    
    @app.route("/workspace/<workspace_id>/settings")
    def workspace_settings_page(workspace_id):
        """Workspace settings page - temporarily unprotected for debugging"""
        return render_template("workspace_settings.html")
    
    @app.route("/settings")
    @app.route("/workspace/settings") 
    def workspace_settings_redirect():
        """Redirect to default workspace settings for Railway deployment"""
        return redirect("/workspace/default_workspace/settings")
    
    @app.route("/auth-test")
    def auth_test():
        """Authentication system test page"""
        from flask import send_from_directory
        return send_from_directory('static', 'auth_test.html')

    @app.route("/health")
    def health_check():
        """Health check endpoint showing service configuration status"""
        return jsonify({
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "services": {
                "github": "configured" if os.getenv("GITHUB_TOKEN") else "not_configured",
                "jira": "configured" if os.getenv("JIRA_TOKEN") else "not_configured", 
                "aws": "configured" if os.getenv("AWS_ACCESS_KEY_ID") else "not_configured",
                "railway": "configured" if os.getenv("RAILWAY_TOKEN") else "not_configured",
                "openai": "configured" if os.getenv("OPENAI_API_KEY") else "not_configured"
            }
        })

    @app.route("/api/feature-flags")
    def get_feature_flags():
        """Get current feature flag status"""
        return jsonify({
            "multi_tenancy": os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true",
            "workstream_management": os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true",
            "service_config_ui": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true",
            "advanced_billing": os.getenv("ENABLE_BILLING", "false").lower() == "true",
            "database_storage": os.getenv("ENABLE_DATABASE", "false").lower() == "true"
        })

    @app.route("/api/services/status")
    def get_services_status():
        """Get status of all services"""
        return jsonify({
            "service_manager": "available",
            "workstream_service": "available",
            "service_config_service": "available",
            "tenant_service": "available"
        })

    @app.route("/api/workstreams", methods=["GET", "POST"])
    def workstreams():
        """Workstream management endpoint"""
        if not os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true":
            return jsonify({"error": "Workstream management is disabled"}), 403
        
        if request.method == "GET":
            return jsonify({"workstreams": []})
        elif request.method == "POST":
            return jsonify({"error": "Workstream creation not implemented"}), 501

    @app.route("/api/service-configs", methods=["GET", "POST"])
    def service_configs():
        """Service configuration management endpoint"""
        if not os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true":
            return jsonify({"error": "Service configuration UI is disabled"}), 403
        
        if request.method == "GET":
            return jsonify({"service_configs": []})
        elif request.method == "POST":
            return jsonify({"error": "Service configuration creation not implemented"}), 501

    @app.route("/api/assignments")
    def get_assignments():
        """Get all assignments"""
        assignments = assignment_service.get_all_assignments()
        return jsonify(assignments)

    @app.route("/api/assignments/<assignment_id>")
    def get_assignment(assignment_id):
        """Get a specific assignment configuration"""
        assignment = assignment_service.get_assignment(assignment_id)
        if not assignment:
            return jsonify({"error": f"Assignment {assignment_id} not found"}), 404
        return jsonify(assignment)

    @app.route("/api/aws-metrics")
    def get_aws_metrics():
        """Get AWS metrics"""
        try:
            metrics = aws_metrics.get_metrics()
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/github-metrics/<assignment_id>")
    def get_github_metrics(assignment_id):
        """Get GitHub metrics for specific assignment"""
        try:
            # Load assignment configuration
            assignment = assignment_service.get_assignment(assignment_id)
            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404
            
            github_config = assignment.get('metrics_config', {}).get('github', {})
            if not github_config.get('enabled', False):
                return jsonify({"error": "GitHub not enabled for this assignment"}), 400
            
            metrics = github_metrics.get_metrics(github_config)
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/github-token-status")
    def check_github_token_status():
        """Check GitHub token validation status"""
        try:
            status = github_metrics.validate_token()
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": str(e), "valid": False}), 500

    @app.route("/api/jira-metrics/<assignment_id>")
    def get_jira_metrics(assignment_id):
        """Get Jira metrics for specific assignment"""
        try:
            # Load assignment configuration
            assignment = assignment_service.get_assignment(assignment_id)
            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404
            
            jira_config = assignment.get('metrics_config', {}).get('jira', {})
            if not jira_config.get('enabled', False):
                return jsonify({"error": "Jira not enabled for this assignment"}), 400
            
            metrics = jira_metrics.get_metrics(jira_config)
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/all-metrics/<assignment_id>")
    def get_all_metrics(assignment_id):
        """Get all metrics for specific assignment"""
        try:
            # Load assignment configuration
            assignment = assignment_service.get_assignment(assignment_id)
            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404
            
            metrics = {}
            
            # AWS metrics
            aws_config = assignment.get('metrics_config', {}).get('aws', {})
            if aws_config.get('enabled', False):
                try:
                    metrics['aws'] = aws_metrics.get_metrics()
                except Exception as e:
                    metrics['aws'] = {"error": str(e)}
            
            # GitHub metrics
            github_config = assignment.get('metrics_config', {}).get('github', {})
            if github_config.get('enabled', False):
                try:
                    metrics['github'] = github_metrics.get_metrics(github_config)
                except Exception as e:
                    metrics['github'] = {"error": str(e)}
            
            # Jira metrics
            jira_config = assignment.get('metrics_config', {}).get('jira', {})
            if jira_config.get('enabled', False):
                try:
                    metrics['jira'] = jira_metrics.get_metrics(jira_config)
                except Exception as e:
                    metrics['jira'] = {"error": str(e)}
            
            # OpenAI metrics
            openai_config = assignment.get('metrics_config', {}).get('openai', {})
            if openai_config.get('enabled', False):
                try:
                    metrics['openai'] = openai_metrics.get_usage_metrics(openai_config)
                except Exception as e:
                    metrics['openai'] = {"error": str(e)}
            
            # Railway metrics
            if assignment.get('metrics_config', {}).get('railway', {}).get('enabled'):
                try:
                    import asyncio
                    railway_config = assignment.get('metrics_config', {}).get('railway', {})
                    project_id = railway_config.get('project_id')
                    project_name = railway_config.get('project_name')
                    metrics['railway'] = asyncio.run(railway_metrics.get_metrics(project_id=project_id, project_name=project_name))
                except Exception as e:
                    metrics['railway'] = {"error": str(e)}
            
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/assignments/<assignment_id>/metrics")
    def get_assignment_metrics(assignment_id):
        """Get metrics for specific assignment"""
        try:
            # Load assignment configuration
            assignment_file = f"config/assignments/{assignment_id}.json"
            if not os.path.exists(assignment_file):
                return jsonify({"error": "Assignment not found"}), 404
            
            with open(assignment_file, 'r') as f:
                assignment = json.load(f)
            
            metrics = {}
            
            # AWS metrics
            if assignment.get('aws', {}).get('enabled', False):
                try:
                    metrics['aws'] = aws_metrics.get_metrics()
                except Exception as e:
                    metrics['aws'] = {"error": str(e)}
            
            # GitHub metrics
            if assignment.get('github', {}).get('enabled', False):
                try:
                    metrics['github'] = github_metrics.get_metrics(assignment['github'])
                except Exception as e:
                    metrics['github'] = {"error": str(e)}
            
            # Jira metrics
            if assignment.get('jira', {}).get('enabled', False):
                try:
                    metrics['jira'] = jira_metrics.get_metrics(assignment['jira'])
                except Exception as e:
                    metrics['jira'] = {"error": str(e)}
            
            # OpenAI metrics
            if assignment.get('openai', {}).get('enabled', False):
                try:
                    metrics['openai'] = openai_metrics.get_usage_metrics(assignment['openai'])
                except Exception as e:
                    metrics['openai'] = {"error": str(e)}
            
            # Railway metrics
            if assignment.get('metrics_config', {}).get('railway', {}).get('enabled'):
                try:
                    import asyncio
                    railway_config = assignment.get('metrics_config', {}).get('railway', {})
                    project_id = railway_config.get('project_id')
                    project_name = railway_config.get('project_name')
                    metrics['railway'] = asyncio.run(railway_metrics.get_metrics(project_id=project_id, project_name=project_name))
                except Exception as e:
                    metrics['railway'] = {"error": str(e)}
            
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/assignments/<assignment_id>/cto-insights")
    def get_cto_insights(assignment_id):
        """Get comprehensive CTO insights for specific assignment"""
        try:
            # Load assignment configuration
            assignment = assignment_service.get_assignment(assignment_id)
            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404
            
            # Check if AWS metrics are enabled
            if not assignment.get('aws', {}).get('enabled', False):
                return jsonify({"error": "AWS metrics not enabled for this assignment"}), 400
            
            # Get comprehensive AWS report
            aws_report = aws_metrics.get_comprehensive_aws_report()
            
            # Merge with assignment info
            response = {
                "assignment_info": {
                    "id": assignment.get("id"),
                    "name": assignment.get("name"),
                    "monthly_burn_rate": assignment.get("monthly_burn_rate"),
                    "team_size": assignment.get("team_size")
                }
            }
            
            # Add AWS comprehensive report data
            response.update(aws_report)
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/ask-stream", methods=["POST"])
    def ask_chatbot_stream():
        """AI-powered chatbot with streaming response"""
        try:
            data = request.get_json()
            question = data.get("question", "")
            user_id = data.get("user_id", "default")
            
            if not question:
                return jsonify({"error": "No question provided"}), 400
            
            # Return streaming response
            from flask import Response
            return Response(
                process_question_stream(question, user_id),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/ask", methods=["POST"])
    def ask_chatbot():
        """AI-powered chatbot endpoint"""
        try:
            data = request.get_json()
            question = data.get("question", "")
            user_id = data.get("user_id", "default")
            
            if not question:
                return jsonify({"error": "No question provided"}), 400
            
            # Use AI chatbot service
            result = process_question(question, user_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/history")
    def get_chatbot_history():
        """Get chatbot conversation history"""
        try:
            user_id = request.args.get("user_id", "default")
            limit = int(request.args.get("limit", 20))
            history = get_conversation_history(user_id, limit)
            return jsonify({"history": history})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/clear", methods=["POST"])
    def clear_chatbot_history():
        """Clear chatbot conversation history"""
        try:
            data = request.get_json() or {}
            user_id = data.get("user_id", "default")
            clear_conversation_history(user_id)
            return jsonify({"message": "History cleared", "success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ===== AUTHENTICATION ENDPOINTS (Phase 3) =====
    
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        """Register a new user account"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No registration data provided"}), 400
        
        email = data.get("email")
        password = data.get("password")
        display_name = data.get("display_name")
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        result = user_service.register_user(email, password, display_name)
        
        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        """Authenticate user and return token"""
        from flask import session
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No login data provided"}), 400
        
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        result = user_service.authenticate_user(email, password)
        
        if result.get("success"):
            # Store authentication in session for web pages
            session['user_email'] = email
            session['auth_token'] = result.get("token")
            session['user_data'] = result.get("user")
            session.permanent = True  # Keep session across browser restarts
            
            return jsonify(result), 200
        else:
            return jsonify(result), 401
    
    @app.route("/api/auth/logout", methods=["POST"])
    def logout():
        """Logout user and clear session"""
        from flask import session
        
        session.clear()
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
    
    @app.route("/api/auth/verify", methods=["GET"])
    @require_auth
    def verify_token():
        """Verify current token and return user info"""
        return jsonify({
            "valid": True,
            "user": get_current_user()
        })
    
    @app.route("/api/auth/users", methods=["GET"])
    @require_auth
    def list_users():
        """List all users (admin only)"""
        current_user = get_current_user()
        
        # Only admins can list users
        if current_user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        
        users = user_service.list_users()
        return jsonify({"users": users})
    
    @app.route("/api/auth/users/<user_email>/workspaces", methods=["POST"])
    @require_auth
    def grant_workspace_access(user_email):
        """Grant user access to workspace (admin only)"""
        current_user = get_current_user()
        
        # Only admins can grant access (for now)
        if current_user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No workspace data provided"}), 400
        
        workspace_id = data.get("workspace_id")
        role = data.get("role", "member")
        
        if not workspace_id:
            return jsonify({"error": "Workspace ID is required"}), 400
        
        result = user_service.add_user_to_workspace(user_email, workspace_id, role)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    # ===== WORKSPACE MANAGEMENT ENDPOINTS (Phase 1 + 3 Auth) =====
    
    @app.route("/api/workspaces", methods=["GET", "POST"])
    @require_auth
    def workspace_management():
        """Workspace management endpoint"""
        if request.method == "GET":
            # List all workspaces
            result = workspace_service.list_workspaces()
            return jsonify(result)
        
        elif request.method == "POST":
            # Create new workspace
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            workspace_id = data.get("id")
            name = data.get("name")
            description = data.get("description", "")
            
            if not workspace_id or not name:
                return jsonify({"error": "Workspace ID and name are required"}), 400
            
            result = workspace_service.create_workspace(workspace_id, name, description)
            
            if result.get("success"):
                return jsonify(result), 201
            else:
                return jsonify(result), 400
    
    @app.route("/api/workspaces/<workspace_id>", methods=["GET", "DELETE"])
    @require_workspace_access
    def workspace_detail(workspace_id):
        """Workspace detail operations"""
        if request.method == "GET":
            # Get workspace details
            workspace = workspace_service.get_workspace(workspace_id)
            if "error" in workspace:
                return jsonify(workspace), 404
            return jsonify(workspace)
        
        elif request.method == "DELETE":
            # Delete workspace
            result = workspace_service.delete_workspace(workspace_id)
            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400
    
    @app.route("/api/workspaces/<workspace_id>/assignments", methods=["GET", "POST"])
    def workspace_assignments(workspace_id):
        """Workspace assignment management"""
        if request.method == "GET":
            # Get assignments for workspace
            result = workspace_service.get_workspace_assignments(workspace_id)
            if "error" in result:
                return jsonify(result), 404
            return jsonify(result)
        
        elif request.method == "POST":
            # Add assignment to workspace
            data = request.get_json()
            if not data:
                return jsonify({"error": "No assignment data provided"}), 400
            
            assignment_id = data.get("id")
            if not assignment_id:
                return jsonify({"error": "Assignment ID is required"}), 400
            
            # Remove 'id' from data since it's passed separately
            assignment_config = {k: v for k, v in data.items() if k != "id"}
            
            result = workspace_service.add_assignment_to_workspace(
                workspace_id, 
                assignment_id, 
                assignment_config
            )
            
            if result.get("success"):
                return jsonify(result), 201
            else:
                return jsonify(result), 400
    
    @app.route("/api/workspaces/<workspace_id>/assignments/<assignment_id>", methods=["GET"])
    def workspace_assignment_detail(workspace_id, assignment_id):
        """Get specific assignment in workspace"""
        # Get all assignments and find the specific one
        result = workspace_service.get_workspace_assignments(workspace_id)
        if "error" in result:
            return jsonify(result), 404
        
        assignments = result.get("assignments", [])
        assignment = next((a for a in assignments if a.get("id") == assignment_id), None)
        
        if not assignment:
            return jsonify({"error": f"Assignment '{assignment_id}' not found in workspace '{workspace_id}'"}), 404
        
        return jsonify(assignment)
    
    # ===== PHASE 3 WORKSPACE CREDENTIALS TEST ENDPOINT =====
    
    @app.route("/api/workspaces/<workspace_id>/assignments/<assignment_id>/test-credentials", methods=["GET"])
    @require_workspace_access
    def test_workspace_credentials(workspace_id, assignment_id):
        """
        Test endpoint to verify Phase 3 workspace credentials are working.
        Returns credential sources and connector initialization status.
        """
        try:
            # Test workspace connectors
            connectors = get_workspace_connectors(workspace_id, assignment_id)
            
            results = {
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "test_results": {},
                "credential_sources": {}
            }
            
            # Test GitHub credentials
            github_connector = connectors['github']
            results["credential_sources"]["github"] = {
                "token_source": "workspace" if github_connector.token != github_metrics.token else "environment",
                "token_present": bool(github_connector.token),
                "org_source": "workspace" if hasattr(github_connector, 'org') and github_connector.org != getattr(github_metrics, 'org', None) else "environment",
                "org_present": bool(getattr(github_connector, 'org', None))
            }
            
            # Test Jira credentials
            jira_connector = connectors['jira']
            results["credential_sources"]["jira"] = {
                "token_source": "workspace" if jira_connector.token != jira_metrics.token else "environment",
                "token_present": bool(jira_connector.token),
                "url_source": "workspace" if jira_connector.base_url != jira_metrics.base_url else "environment",
                "url_present": bool(jira_connector.base_url),
                "email_present": bool(jira_connector.email)
            }
            
            # Test AWS credentials
            aws_connector = connectors['aws']
            results["credential_sources"]["aws"] = {
                "access_key_source": "workspace" if aws_connector.access_key != aws_metrics.access_key else "environment", 
                "access_key_present": bool(aws_connector.access_key),
                "secret_key_source": "workspace" if aws_connector.secret_key != aws_metrics.secret_key else "environment",
                "secret_key_present": bool(aws_connector.secret_key),
                "region_source": "workspace" if aws_connector.region != aws_metrics.region else "environment",
                "region": aws_connector.region
            }
            
            # Test credential service directly
            from services.auth.credential_service import CredentialService
            credential_service = CredentialService()
            
            results["direct_credential_test"] = {
                "github": credential_service.get_github_credentials(workspace_id, assignment_id),
                "jira": credential_service.get_jira_credentials(workspace_id, assignment_id), 
                "aws": credential_service.get_aws_credentials(workspace_id, assignment_id)
            }
            
            results["test_results"]["phase_3_status"] = "✅ WORKING" if any(
                src.get("token_source") == "workspace" or src.get("access_key_source") == "workspace"
                for src in results["credential_sources"].values()
            ) else "❌ FALLBACK_TO_ENV_VARS"
            
            return jsonify(results)
            
        except Exception as e:
            return jsonify({
                "error": "Failed to test workspace credentials",
                "details": str(e),
                "workspace_id": workspace_id,
                "assignment_id": assignment_id
            }), 500
    
    # ===== CONNECTOR TEMPLATE ENDPOINTS (Phase 2) =====
    
    @app.route("/api/workspaces/<workspace_id>/connector-templates", methods=["GET"])
    @require_workspace_access
    def get_workspace_templates(workspace_id):
        """Get all connector templates for workspace"""
        connector_type = request.args.get("type")  # Optional filter by connector type
        result = workspace_service.get_connector_templates(workspace_id, connector_type)
        
        if "error" in result:
            return jsonify(result), 404
        
        return jsonify(result)
    
    @app.route("/api/workspaces/<workspace_id>/connector-templates/<connector_type>", methods=["POST"])
    def create_connector_template(workspace_id, connector_type):
        """Create a connector template"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No template data provided"}), 400
        
        template_name = data.get("name")
        template_config = data.get("config", {})
        
        if not template_name:
            return jsonify({"error": "Template name is required"}), 400
        
        result = workspace_service.create_connector_template(
            workspace_id, 
            connector_type, 
            template_name, 
            template_config
        )
        
        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    @app.route("/api/workspaces/<workspace_id>/connector-templates/<connector_type>/<template_name>", methods=["GET", "DELETE"])
    def connector_template_detail(workspace_id, connector_type, template_name):
        """Get or delete specific connector template"""
        if request.method == "GET":
            # Get template details
            result = workspace_service.get_connector_template(workspace_id, connector_type, template_name)
            if "error" in result:
                return jsonify(result), 404
            return jsonify(result)
        
        elif request.method == "DELETE":
            # Delete template
            result = workspace_service.delete_connector_template(workspace_id, connector_type, template_name)
            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400
    
    @app.route("/api/workspaces/<workspace_id>/assignments/from-template", methods=["POST"])
    def create_assignment_from_template(workspace_id):
        """Create assignment using connector templates"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No assignment data provided"}), 400
        
        assignment_id = data.get("id")
        if not assignment_id:
            return jsonify({"error": "Assignment ID is required"}), 400
        
        # Extract templates mapping
        templates = data.get("templates", {})  # {connector_type: template_name}
        
        # Remove 'id' and 'templates' from assignment config
        assignment_config = {k: v for k, v in data.items() if k not in ["id", "templates"]}
        
        result = workspace_service.create_assignment_from_template(
            workspace_id,
            assignment_id,
            assignment_config,
            templates
        )
        
        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    @app.route("/api/workspaces/<workspace_id>/assignments/<assignment_id>/auth/<connector_type>", methods=["PUT"])
    def update_assignment_auth(workspace_id, assignment_id, connector_type):
        """Update authentication credentials for assignment connector"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No credentials provided"}), 400
        
        credentials = data.get("credentials", {})
        if not credentials:
            return jsonify({"error": "Credentials object is required"}), 400
        
        result = workspace_service.update_assignment_auth(
            workspace_id,
            assignment_id, 
            connector_type,
            credentials
        )
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    # ===== WORKSPACE SETTINGS & CREDENTIAL MANAGEMENT =====
    
    @app.route("/api/workspaces/<workspace_id>/settings", methods=["GET", "PUT"])
    def workspace_settings(workspace_id):
        """Get or update workspace settings"""
        if request.method == "GET":
            # Get workspace settings including connector configurations
            workspace = workspace_service.get_workspace(workspace_id)
            if "error" in workspace:
                return jsonify(workspace), 404
            
            # Get assignments for credential status
            assignments = workspace_service.get_workspace_assignments(workspace_id)
            
            # Return workspace info with credential status
            return jsonify({
                "workspace": workspace,
                "assignments": assignments.get("assignments", []),
                "connector_templates": workspace.get("connector_templates", {}),
                "credential_status": _get_workspace_credential_status(workspace_id)
            })
        
        elif request.method == "PUT":
            # Update workspace settings
            data = request.get_json()
            if not data:
                return jsonify({"error": "No settings data provided"}), 400
            
            result = workspace_service.update_workspace_settings(workspace_id, data)
            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400
    
    @app.route("/api/workspaces/<workspace_id>/credentials", methods=["GET"])
    def get_workspace_credentials(workspace_id):
        """Get credential status for all connectors in workspace"""
        try:
            status = _get_workspace_credential_status(workspace_id)
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": f"Failed to get credential status: {str(e)}"}), 500
    
    @app.route("/api/workspaces/<workspace_id>/credentials/<connector_type>", methods=["PUT", "DELETE"])
    @require_workspace_access  
    def manage_connector_credentials(workspace_id, connector_type):
        """Set or delete credentials for a specific connector type"""
        if request.method == "PUT":
            data = request.get_json()
            if not data:
                return jsonify({"error": "No credential data provided"}), 400
            
            credentials = data.get("credentials", {})
            assignment_id = data.get("assignment_id")
            
            if not credentials:
                return jsonify({"error": "Credentials are required"}), 400
            
            if not assignment_id:
                return jsonify({"error": "Assignment ID is required"}), 400
            
            # Validate credentials by testing them
            validation_result = _validate_connector_credentials(connector_type, credentials)
            if not validation_result.get("valid"):
                return jsonify({
                    "error": "Credential validation failed",
                    "details": validation_result.get("error", "Invalid credentials")
                }), 400
            
            # Update assignment auth
            result = workspace_service.update_assignment_auth(
                workspace_id, assignment_id, connector_type, credentials
            )
            
            if result.get("success"):
                return jsonify({
                    "success": True,
                    "message": f"{connector_type.title()} credentials updated successfully",
                    "validation": validation_result
                })
            else:
                return jsonify(result), 400
                
        elif request.method == "DELETE":
            # Clear credentials for connector type
            data = request.get_json()
            assignment_id = data.get("assignment_id") if data else None
            
            if not assignment_id:
                return jsonify({"error": "Assignment ID is required"}), 400
            
            result = workspace_service.clear_assignment_auth(workspace_id, assignment_id, connector_type)
            
            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400
    
    @app.route("/api/workspaces/<workspace_id>/credentials/<connector_type>/test", methods=["POST"])
    @require_workspace_access
    def test_connector_credentials(workspace_id, connector_type):
        """Test connector credentials without saving them"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No credential data provided"}), 400
        
        credentials = data.get("credentials", {})
        if not credentials:
            return jsonify({"error": "Credentials are required"}), 400
        
        result = _validate_connector_credentials(connector_type, credentials)
        return jsonify(result)
    
    def _get_workspace_credential_status(workspace_id):
        """Get credential configuration status for workspace"""
        try:
            workspace = workspace_service.get_workspace(workspace_id)
            if "error" in workspace:
                return {"error": "Workspace not found"}
            
            assignments = workspace_service.get_workspace_assignments(workspace_id)
            status = {
                "workspace_id": workspace_id,
                "connectors": {
                    "github": {"configured": False, "assignments": []},
                    "jira": {"configured": False, "assignments": []},
                    "aws": {"configured": False, "assignments": []},
                }
            }
            
            # Check each assignment for configured connectors
            for assignment in assignments.get("assignments", []):
                assignment_id = assignment.get("id")
                auth_instances = assignment.get("auth_instances", {})
                
                for connector_type in ["github", "jira", "aws"]:
                    if connector_type in auth_instances:
                        creds = auth_instances[connector_type].get("credentials", {})
                        if creds:
                            status["connectors"][connector_type]["configured"] = True
                            status["connectors"][connector_type]["assignments"].append({
                                "id": assignment_id,
                                "name": assignment.get("name", assignment_id),
                                "credentials_count": len(creds)
                            })
            
            return status
        except Exception as e:
            return {"error": f"Failed to get credential status: {str(e)}"}
    
    def _validate_connector_credentials(connector_type, credentials):
        """Validate connector credentials by attempting to use them"""
        try:
            if connector_type == "github":
                return _validate_github_credentials(credentials)
            elif connector_type == "jira":
                return _validate_jira_credentials(credentials)  
            elif connector_type == "aws":
                return _validate_aws_credentials(credentials)
            else:
                return {"valid": False, "error": f"Unknown connector type: {connector_type}"}
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}
    
    def _validate_github_credentials(credentials):
        """Test GitHub credentials"""
        token = credentials.get("github_token")
        if not token:
            return {"valid": False, "error": "GitHub token is required"}
        
        try:
            import requests
            headers = {"Authorization": f"token {token}", "User-Agent": "CTO-Dashboard"}
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "valid": True,
                    "user": user_data.get("login"),
                    "name": user_data.get("name"),
                    "scopes": response.headers.get("x-oauth-scopes", "").split(", ") if response.headers.get("x-oauth-scopes") else []
                }
            else:
                return {"valid": False, "error": f"GitHub API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"valid": False, "error": f"GitHub connection failed: {str(e)}"}
    
    def _validate_jira_credentials(credentials):
        """Test Jira credentials"""
        token = credentials.get("jira_token")
        email = credentials.get("jira_email")
        url = credentials.get("jira_url")
        
        if not token:
            return {"valid": False, "error": "Jira token is required"}
        if not email:
            return {"valid": False, "error": "Jira email is required"}
        if not url:
            return {"valid": False, "error": "Jira URL is required"}
        
        try:
            import requests
            import base64
            
            # Clean URL
            jira_url = url.rstrip("/")
            if not jira_url.startswith("http"):
                jira_url = f"https://{jira_url}"
            
            # Test API connection
            auth_string = base64.b64encode(f"{email}:{token}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{jira_url}/rest/api/3/myself", headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "valid": True,
                    "user": user_data.get("emailAddress"),
                    "displayName": user_data.get("displayName"),
                    "accountId": user_data.get("accountId")
                }
            else:
                return {"valid": False, "error": f"Jira API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"valid": False, "error": f"Jira connection failed: {str(e)}"}
    
    def _validate_aws_credentials(credentials):
        """Test AWS credentials"""
        access_key = credentials.get("aws_access_key")
        secret_key = credentials.get("aws_secret_key") 
        region = credentials.get("aws_region", "us-east-1")
        
        if not access_key:
            return {"valid": False, "error": "AWS access key is required"}
        if not secret_key:
            return {"valid": False, "error": "AWS secret key is required"}
        
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            # Test credentials by calling STS get-caller-identity
            client = boto3.client(
                'sts',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            
            response = client.get_caller_identity()
            return {
                "valid": True,
                "account": response.get("Account"),
                "arn": response.get("Arn"),
                "userId": response.get("UserId"),
                "region": region
            }
        except (ClientError, NoCredentialsError) as e:
            return {"valid": False, "error": f"AWS authentication failed: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"AWS connection failed: {str(e)}"}

    @app.route("/static/<path:filename>")
    def serve_static(filename):
        """Serve static files"""
        return send_from_directory('static', filename)
