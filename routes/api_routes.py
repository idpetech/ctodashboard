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

# Initialize services
service_manager = ServiceManager()
aws_metrics = EmbeddedAWSMetrics()
github_metrics = EmbeddedGitHubMetrics()
jira_metrics = EmbeddedJiraMetrics()
openai_metrics = OpenAIMetrics()

def register_routes(app):
    """Register all routes with the Flask app"""
    
    @app.route("/")
    def index():
        """Main dashboard page"""
        return render_template("dashboard.html")

    @app.route("/health")
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({
            "status": "read_only",
            "note": "Feature flags are controlled via environment variables",
            "feature_flags": {
                "multi_tenancy": os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true",
                "workstream_management": os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true",
                "service_config_ui": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true",
                "advanced_billing": os.getenv("ENABLE_BILLING", "false").lower() == "true",
                "database_storage": os.getenv("ENABLE_DATABASE", "false").lower() == "true"
            },
            "environment_variables": {
                "ENABLE_MULTI_TENANCY": os.getenv("ENABLE_MULTI_TENANCY", "false"),
                "ENABLE_WORKSTREAM_MGMT": os.getenv("ENABLE_WORKSTREAM_MGMT", "false"),
                "ENABLE_SERVICE_CONFIG_UI": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false"),
                "ENABLE_BILLING": os.getenv("ENABLE_BILLING", "false"),
                "ENABLE_DATABASE": os.getenv("ENABLE_DATABASE", "false")
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
        assignments_dir = "backend/assignments"
        assignments = []
        
        if os.path.exists(assignments_dir):
            for filename in os.listdir(assignments_dir):
                if filename.endswith('.json'):
                    assignment_id = filename[:-5]  # Remove .json extension
                    filepath = os.path.join(assignments_dir, filename)
                    
                    try:
                        with open(filepath, 'r') as f:
                            assignment_data = json.load(f)
                            assignment_data['id'] = assignment_id
                            assignments.append(assignment_data)
                    except Exception as e:
                        print(f"Error loading assignment {assignment_id}: {e}")
        
        return jsonify(assignments)

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
            assignment_file = f"backend/assignments/{assignment_id}.json"
            if not os.path.exists(assignment_file):
                return jsonify({"error": "Assignment not found"}), 404
            
            with open(assignment_file, 'r') as f:
                assignment = json.load(f)
            
            if not assignment.get('github', {}).get('enabled', False):
                return jsonify({"error": "GitHub not enabled for this assignment"}), 400
            
            metrics = github_metrics.get_metrics(assignment['github'])
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/jira-metrics/<assignment_id>")
    def get_jira_metrics(assignment_id):
        """Get Jira metrics for specific assignment"""
        try:
            # Load assignment configuration
            assignment_file = f"backend/assignments/{assignment_id}.json"
            if not os.path.exists(assignment_file):
                return jsonify({"error": "Assignment not found"}), 404
            
            with open(assignment_file, 'r') as f:
                assignment = json.load(f)
            
            if not assignment.get('jira', {}).get('enabled', False):
                return jsonify({"error": "Jira not enabled for this assignment"}), 400
            
            metrics = jira_metrics.get_metrics(assignment['jira'])
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/all-metrics/<assignment_id>")
    def get_all_metrics(assignment_id):
        """Get all metrics for specific assignment"""
        try:
            # Load assignment configuration
            assignment_file = f"backend/assignments/{assignment_id}.json"
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
            
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/assignments/<assignment_id>/metrics")
    def get_assignment_metrics(assignment_id):
        """Get metrics for specific assignment"""
        try:
            # Load assignment configuration
            assignment_file = f"backend/assignments/{assignment_id}.json"
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
            
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/ask", methods=["POST"])
    def ask_chatbot():
        """Ask chatbot a question"""
        try:
            data = request.get_json()
            question = data.get('question', '')
            
            if not question:
                return jsonify({"error": "No question provided"}), 400
            
            # Simple response for now (can be enhanced with AI later)
            response = f"I received your question: '{question}'. This is a placeholder response."
            
            return jsonify({"response": response})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/history")
    def get_chatbot_history():
        """Get chatbot conversation history"""
        return jsonify({"history": []})

    @app.route("/api/chatbot/clear", methods=["POST"])
    def clear_chatbot_history():
        """Clear chatbot conversation history"""
        return jsonify({"message": "History cleared"})

    @app.route("/static/<path:filename>")
    def serve_static(filename):
        """Serve static files"""
        return send_from_directory('static', filename)
