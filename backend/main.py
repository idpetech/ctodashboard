import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

# Configure Flask to serve static files from React build
static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')
app = Flask(__name__, static_folder=static_folder, static_url_path='')

# Enable CORS for all routes (mainly for development)
CORS(app, origins=["*"])

# API Routes - all prefixed with /api
@app.route("/api")
def api_root():
    return jsonify({"message": "CTO Dashboard API", "status": "healthy"})

@app.route("/api/health")
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

@app.route("/api/assignments")
def get_assignments():
    """Get all assignments from JSON configuration files"""
    from assignment_service import AssignmentService
    
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    service = AssignmentService()
    assignments = service.get_all_assignments(include_archived=include_archived)
    
    return jsonify(assignments)

@app.route("/api/assignments/<assignment_id>")
def get_assignment(assignment_id):
    """Get a specific assignment configuration"""
    from assignment_service import AssignmentService
    
    service = AssignmentService()
    assignment = service.get_assignment(assignment_id)
    
    if not assignment:
        return jsonify({"error": f"Assignment {assignment_id} not found"}), 404
    
    return jsonify(assignment)

@app.route("/api/assignments/<assignment_id>/metrics")
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

@app.route("/api/assignments/<assignment_id>/cto-insights")
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

# Chatbot API Routes
@app.route("/api/chatbot/ask", methods=["POST"])
def chatbot_ask():
    """Ask a question to the chatbot"""
    from chatbot_service import chatbot_service
    
    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Question is required"}), 400
        
        question = data["question"]
        user_id = data.get("user_id", "default")
        
        # Process the question asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(chatbot_service.process_question(question, user_id))
        finally:
            loop.close()
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": f"Chatbot error: {str(e)}"}), 500

@app.route("/api/chatbot/history")
def chatbot_history():
    """Get chatbot conversation history"""
    from chatbot_service import chatbot_service
    
    try:
        user_id = request.args.get("user_id", "default")
        limit = int(request.args.get("limit", 10))
        
        history = chatbot_service.get_conversation_history(user_id, limit)
        return jsonify({"history": history})
        
    except Exception as e:
        return jsonify({"error": f"Error getting history: {str(e)}"}), 500

@app.route("/api/chatbot/clear", methods=["POST"])
def chatbot_clear():
    """Clear chatbot conversation history"""
    from chatbot_service import chatbot_service
    
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", "default")
        
        chatbot_service.clear_conversation_history(user_id)
        return jsonify({"message": "Conversation history cleared"})
        
    except Exception as e:
        return jsonify({"error": f"Error clearing history: {str(e)}"}), 500

# Serve React static files
@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serve static assets from React build"""
    return send_from_directory(os.path.join(app.static_folder, 'assets'), path)

# Serve React app for all non-API routes (client-side routing)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """Serve React app for frontend routes, API routes handled above"""
    # Skip API routes - let them be handled by the API endpoints above
    if path.startswith('api/') or path in ['health', 'assignments']:
        # This should not happen as API routes are defined above, but just in case
        return jsonify({"error": "API endpoint not found"}), 404
    
    # For any other route, serve the React app's index.html
    index_path = os.path.join(app.static_folder, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return jsonify({"error": "Frontend build not found. Run 'npm run build' in the frontend directory."}), 404

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_ENV') != 'production'
    app.run(host="0.0.0.0", port=port, debug=debug)
