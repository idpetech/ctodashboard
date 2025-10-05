import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template_string

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Simple HTML template with embedded CSS and JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CTO Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen p-4">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold text-gray-900 mb-8">CTO Dashboard</h1>
            
            <div id="loading" class="flex items-center justify-center py-12">
                <div class="text-lg text-gray-600">Loading dashboard...</div>
            </div>
            
            <div id="error" class="hidden p-4 bg-red-100 border border-red-400 text-red-700 rounded mb-4"></div>
            
            <div id="content" class="hidden space-y-6"></div>
        </div>
    </div>

    <script>
        async function loadDashboard() {
            try {
                console.log('Loading assignments...');
                const response = await fetch('/api/assignments');
                const assignments = await response.json();
                console.log('Assignments loaded:', assignments);
                
                if (!assignments || assignments.length === 0) {
                    showError('No assignments found. Check backend configuration.');
                    return;
                }
                
                displayAssignments(assignments);
                
            } catch (error) {
                console.error('Error:', error);
                showError('Failed to load dashboard: ' + error.message);
            }
        }
        
        function showError(message) {
            document.getElementById('loading').classList.add('hidden');
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
        }
        
        function displayAssignments(assignments) {
            document.getElementById('loading').classList.add('hidden');
            const content = document.getElementById('content');
            content.classList.remove('hidden');
            
            content.innerHTML = assignments.map(assignment => `
                <div class="bg-white rounded-lg shadow-lg p-6">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <h2 class="text-xl font-semibold text-gray-900">${assignment.name}</h2>
                            <p class="text-sm text-gray-600 mt-1">${assignment.description}</p>
                            <span class="inline-block px-2 py-1 text-xs rounded-full mt-2 ${
                                assignment.status === 'active' 
                                    ? 'bg-green-100 text-green-800' 
                                    : 'bg-gray-100 text-gray-800'
                            }">${assignment.status}</span>
                        </div>
                        <div class="text-right">
                            <div class="text-sm text-gray-500">Monthly Burn Rate</div>
                            <div class="text-lg font-semibold">$${assignment.monthly_burn_rate.toLocaleString()}</div>
                        </div>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                        <div>
                            <div class="text-sm text-gray-500">Team Size</div>
                            <div class="font-medium">${assignment.team_size} people</div>
                        </div>
                        <div>
                            <div class="text-sm text-gray-500">Start Date</div>
                            <div class="font-medium">${new Date(assignment.start_date).toLocaleDateString()}</div>
                        </div>
                        <div>
                            <div class="text-sm text-gray-500">Tech Stack</div>
                            <div class="font-medium">${assignment.team.tech_stack.slice(0, 3).join(', ')}</div>
                        </div>
                    </div>
                    
                    <div class="flex flex-wrap gap-2 mb-4">
                        ${assignment.metrics_config.github.enabled ? `
                            <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                                📊 GitHub (${assignment.metrics_config.github.repos.length} repos)
                            </span>
                        ` : ''}
                        ${assignment.metrics_config.jira.enabled ? `
                            <span class="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">
                                🎯 Jira (${assignment.metrics_config.jira.project_key})
                            </span>
                        ` : ''}
                        ${assignment.metrics_config.aws.enabled ? `
                            <span class="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded">
                                ☁️ AWS
                            </span>
                        ` : ''}
                        ${assignment.metrics_config.railway.enabled ? `
                            <span class="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                                🚂 Railway
                            </span>
                        ` : ''}
                    </div>
                    
                    <button 
                        onclick="loadMetrics('${assignment.id}')" 
                        class="w-full mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        id="metrics-btn-${assignment.id}"
                    >
                        Load Live Metrics
                    </button>
                    
                    <div id="metrics-${assignment.id}" class="hidden mt-4 p-4 bg-gray-50 rounded">
                        <div class="text-sm text-gray-500 mb-2">Loading metrics...</div>
                    </div>
                </div>
            `).join('');
        }
        
        async function loadMetrics(assignmentId) {
            const button = document.getElementById(`metrics-btn-${assignmentId}`);
            const metricsDiv = document.getElementById(`metrics-${assignmentId}`);
            
            button.disabled = true;
            button.textContent = 'Loading...';
            metricsDiv.classList.remove('hidden');
            
            try {
                const response = await fetch(`/api/assignments/${assignmentId}/metrics`);
                const metrics = await response.json();
                
                let metricsHtml = '<div class="space-y-3">';
                metricsHtml += `<div class="text-sm text-gray-500">Updated: ${new Date(metrics.timestamp).toLocaleString()}</div>`;
                
                if (metrics.github) {
                    metricsHtml += `
                        <div class="bg-white p-3 rounded border">
                            <div class="font-medium text-blue-800 mb-2">📊 GitHub Metrics</div>
                            <div class="text-sm text-gray-600">${metrics.github.length} repositories tracked</div>
                        </div>
                    `;
                }
                
                if (metrics.aws) {
                    metricsHtml += `
                        <div class="bg-white p-3 rounded border">
                            <div class="font-medium text-orange-800 mb-2">☁️ AWS Metrics</div>
                            <div class="text-sm text-gray-600">
                                30-day cost: $${metrics.aws.total_cost_last_30_days || 'N/A'}
                            </div>
                        </div>
                    `;
                }
                
                if (metrics.jira) {
                    metricsHtml += `
                        <div class="bg-white p-3 rounded border">
                            <div class="font-medium text-purple-800 mb-2">🎯 Jira Metrics</div>
                            <div class="text-sm text-gray-600">Project data loaded</div>
                        </div>
                    `;
                }
                
                if (metrics.railway) {
                    metricsHtml += `
                        <div class="bg-white p-3 rounded border">
                            <div class="font-medium text-green-800 mb-2">🚂 Railway Metrics</div>
                            <div class="text-sm text-gray-600">Deployment data loaded</div>
                        </div>
                    `;
                }
                
                metricsHtml += '</div>';
                metricsDiv.innerHTML = metricsHtml;
                
                button.textContent = 'Refresh Metrics';
                button.disabled = false;
                
            } catch (error) {
                metricsDiv.innerHTML = `<div class="text-red-600 text-sm">Error loading metrics: ${error.message}</div>`;
                button.textContent = 'Retry Load Metrics';
                button.disabled = false;
            }
        }
        
        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>
"""

# Routes
@app.route("/")
def dashboard():
    """Serve the main dashboard page"""
    return render_template_string(HTML_TEMPLATE)

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
    try:
        # Read assignments directly from JSON files
        assignments_dir = '/Users/haseebtoor/projects/ctodashboard/backend/assignments'
        assignments = []
        
        for filename in os.listdir(assignments_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(assignments_dir, filename), 'r') as f:
                        assignment = json.load(f)
                        if not request.args.get('include_archived', 'false').lower() == 'true':
                            if assignment.get('status') != 'archived':
                                assignments.append(assignment)
                        else:
                            assignments.append(assignment)
                except json.JSONDecodeError as e:
                    print(f"Error loading {filename}: {e}")
                    continue
        
        return jsonify(assignments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/assignments/<assignment_id>/metrics")
def get_assignment_metrics(assignment_id):
    """Get mock metrics for a specific assignment (simplified for demo)"""
    try:
        # Return mock metrics data for demo purposes
        mock_metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "assignment_id": assignment_id,
            "github": [
                {
                    "repo_name": "sample-repo",
                    "commits_last_30_days": 42,
                    "language": "Python",
                    "stars": 15,
                    "open_issues": 3,
                    "total_prs": 8,
                    "last_updated": "2025-08-28T10:00:00Z"
                }
            ],
            "aws": {
                "total_cost_last_30_days": "45.67",
                "period": "Last 30 days",
                "top_services": {
                    "EC2": "25.30",
                    "S3": "12.45",
                    "Route53": "2.50"
                }
            },
            "jira": {
                "project_name": "Sample Project",
                "total_issues_last_30_days": 23,
                "resolved_issues_last_30_days": 18,
                "resolution_rate": 78
            },
            "railway": {
                "project_name": "sample-project",
                "total_deployments": 15,
                "successful_deployments": 14,
                "success_rate": 93,
                "last_deployment": "2025-08-28T15:30:00Z"
            }
        }
        
        return jsonify(mock_metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_ENV') != 'production'
    app.run(host="0.0.0.0", port=port, debug=debug)
