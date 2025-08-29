import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, origins=["*"])  # Allow all origins for simplicity

@app.route("/")
def read_root():
    return jsonify({"message": "CTO Dashboard API", "status": "healthy"})

@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "github": "configured" if os.getenv("GITHUB_TOKEN") else "not_configured",
            "jira": "configured" if os.getenv("JIRA_TOKEN") else "not_configured", 
            "aws": "configured" if os.getenv("AWS_ACCESS_KEY_ID") else "not_configured",
            "railway": "configured" if os.getenv("RAILWAY_TOKEN") else "not_configured"
        }
    })

@app.route("/assignments")
def get_assignments():
    """Get all assignments from JSON configuration files"""
    from assignment_service import AssignmentService
    
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    service = AssignmentService()
    assignments = service.get_all_assignments(include_archived=include_archived)
    
    return jsonify(assignments)

@app.route("/assignments/<assignment_id>")
def get_assignment(assignment_id):
    """Get a specific assignment configuration"""
    from assignment_service import AssignmentService
    
    service = AssignmentService()
    assignment = service.get_assignment(assignment_id)
    
    if not assignment:
        return jsonify({"error": f"Assignment {assignment_id} not found"}), 404
    
    return jsonify(assignment)

@app.route("/assignments/<assignment_id>/metrics")
def get_assignment_metrics(assignment_id):
    """Get real-time metrics for a specific assignment"""
    from assignment_service import AssignmentService
    from metrics_service import MetricsAggregator
    
    # Get assignment configuration from JSON file
    service = AssignmentService()
    assignment_config = service.get_assignment(assignment_id)
    
    if not assignment_config:
        return jsonify({"error": f"Assignment {assignment_id} not found"}), 404
    
    # Get metrics from all configured services (convert async to sync)
    aggregator = MetricsAggregator()
    metrics = asyncio.run(aggregator.get_all_metrics(assignment_config))
    
    return jsonify(metrics)

@app.route("/assignments/<assignment_id>/cto-insights")
def get_cto_insights(assignment_id):
    """Get detailed CTO-level insights for a specific assignment"""
    from assignment_service import AssignmentService
    from metrics_service import AWSMetrics
    
    # Get assignment configuration
    service = AssignmentService()
    assignment_config = service.get_assignment(assignment_id)
    
    if not assignment_config:
        return jsonify({"error": f"Assignment {assignment_id} not found"}), 404
    
    # Get comprehensive AWS insights
    aws_config = assignment_config.get("metrics_config", {}).get("aws", {})
    if not aws_config.get("enabled", False):
        return jsonify({"error": "AWS metrics not enabled for this assignment"}), 400
    
    aws_metrics = AWSMetrics()
    comprehensive_report = aws_metrics.get_comprehensive_aws_report()
    
    # Add assignment context
    comprehensive_report["assignment_info"] = {
        "id": assignment_config.get("id"),
        "name": assignment_config.get("name"),
        "monthly_burn_rate": assignment_config.get("monthly_burn_rate"),
        "team_size": assignment_config.get("team_size")
    }
    
    return jsonify(comprehensive_report)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
