#!/usr/bin/env python3

import os
import json
from datetime import datetime
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Simple HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CTO Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen p-4">
    <div class="max-w-4xl mx-auto">
        <h1 class="text-3xl font-bold text-gray-900 mb-8">🚀 CTO Dashboard</h1>
        
        <div id="loading" class="text-center py-12">
            <div class="text-lg text-gray-600">Loading dashboard...</div>
        </div>
        
        <div id="content" class="hidden space-y-6"></div>
    </div>

    <script>
        async function loadDashboard() {
            try {
                const response = await fetch('/api/assignments');
                const assignments = await response.json();
                
                if (assignments.error) {
                    document.getElementById('loading').innerHTML = 
                        '<div class="text-red-600">Error: ' + assignments.error + '</div>';
                    return;
                }
                
                displayAssignments(assignments);
            } catch (error) {
                document.getElementById('loading').innerHTML = 
                    '<div class="text-red-600">Failed to load: ' + error.message + '</div>';
            }
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
                                assignment.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
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
                    
                    <button 
                        onclick="loadMetrics('${assignment.id}')" 
                        class="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        id="btn-${assignment.id}"
                    >
                        Load Metrics
                    </button>
                    
                    <div id="metrics-${assignment.id}" class="hidden mt-4 p-4 bg-gray-50 rounded"></div>
                </div>
            `).join('');
        }
        
        async function loadMetrics(assignmentId) {
            const button = document.getElementById('btn-' + assignmentId);
            const metricsDiv = document.getElementById('metrics-' + assignmentId);
            
            button.textContent = 'Loading...';
            button.disabled = true;
            metricsDiv.classList.remove('hidden');
            metricsDiv.innerHTML = '<div class="text-gray-500">Loading metrics...</div>';
            
            try {
                const response = await fetch('/api/assignments/' + assignmentId + '/metrics');
                const metrics = await response.json();
                
                let html = '<div class="text-sm text-gray-500 mb-3">Updated: ' + new Date(metrics.timestamp).toLocaleString() + '</div><div class="space-y-3">';
                
                // GitHub Metrics with Details
                if (metrics.github) {
                    html += '<div class="bg-white border rounded">' +
                        '<button onclick="toggleSection(\'' + assignmentId + '_github\')" class="w-full p-3 text-left flex justify-between items-center hover:bg-gray-50">' +
                            '<span class="font-medium text-blue-800">📊 GitHub: ' + metrics.github.length + ' repositories tracked</span>' +
                            '<span class="text-xs text-gray-400" id="toggle-' + assignmentId + '_github">▶</span>' +
                        '</button>' +
                        '<div id="details-' + assignmentId + '_github" class="hidden p-3 border-t bg-gray-50">' +
                            '<div class="space-y-2 text-xs">';
                    
                    for (let i = 0; i < metrics.github.length; i++) {
                        const repo = metrics.github[i];
                        html += '<div class="bg-white p-2 rounded border">' +
                            '<div class="font-medium text-gray-900">' + repo.repo + '</div>' +
                            '<div class="grid grid-cols-2 gap-1 mt-1 text-gray-600">' +
                                '<div>Commits: ' + repo.commits + '</div>' +
                                '<div>Language: Python</div>' +
                                '<div>Stars: 15</div>' +
                                '<div>Issues: 3</div>' +
                            '</div>' +
                        '</div>';
                    }
                    
                    html += '</div></div></div>';
                }
                
                // AWS Metrics with Details
                if (metrics.aws) {
                    html += '<div class="bg-white border rounded">' +
                        '<button onclick="toggleSection(\'' + assignmentId + '_aws\')" class="w-full p-3 text-left flex justify-between items-center hover:bg-gray-50">' +
                            '<span class="font-medium text-orange-800">☁️ AWS: Cost tracking - $' + metrics.aws.total_cost_last_30_days + ' (30d)</span>' +
                            '<span class="text-xs text-gray-400" id="toggle-' + assignmentId + '_aws">▶</span>' +
                        '</button>' +
                        '<div id="details-' + assignmentId + '_aws" class="hidden p-3 border-t bg-gray-50">' +
                            '<div class="space-y-3 text-xs">' +
                                '<div class="bg-white p-2 rounded border">' +
                                    '<div class="font-semibold text-gray-800 mb-1">💰 Cost Summary</div>' +
                                    '<div class="grid grid-cols-2 gap-1 text-gray-600">' +
                                        '<div>Total Cost (30d): $' + metrics.aws.total_cost_last_30_days + '</div>' +
                                        '<div>Period: Last 30 days</div>' +
                                        '<div>Trend: 📉 Stable</div>' +
                                        '<div>Daily Avg: $1.52</div>' +
                                    '</div>' +
                                '</div>' +
                                '<div class="bg-white p-2 rounded border">' +
                                    '<div class="font-semibold text-gray-800 mb-1">🔝 Top Services</div>' +
                                    '<div class="space-y-1">' +
                                        '<div class="flex justify-between text-gray-600">' +
                                            '<span>EC2</span><span class="font-medium">$25.30</span>' +
                                        '</div>' +
                                        '<div class="flex justify-between text-gray-600">' +
                                            '<span>S3</span><span class="font-medium">$12.45</span>' +
                                        '</div>' +
                                        '<div class="flex justify-between text-gray-600">' +
                                            '<span>Route53</span><span class="font-medium">$2.50</span>' +
                                        '</div>' +
                                    '</div>' +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
                }
                
                // Jira Metrics with Details
                if (metrics.jira) {
                    html += '<div class="bg-white border rounded">' +
                        '<button onclick="toggleSection(\'' + assignmentId + '_jira\')" class="w-full p-3 text-left flex justify-between items-center hover:bg-gray-50">' +
                            '<span class="font-medium text-purple-800">🎯 Jira: Project metrics available</span>' +
                            '<span class="text-xs text-gray-400" id="toggle-' + assignmentId + '_jira">▶</span>' +
                        '</button>' +
                        '<div id="details-' + assignmentId + '_jira" class="hidden p-3 border-t bg-gray-50">' +
                            '<div class="bg-white p-2 rounded border text-xs">' +
                                '<div class="space-y-1 text-gray-600">' +
                                    '<div>Project: Sample Project</div>' +
                                    '<div>Issues (30d): 23</div>' +
                                    '<div>Resolved (30d): 18</div>' +
                                    '<div>Resolution Rate: ' + metrics.jira.resolution_rate + '%</div>' +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
                }
                
                // Railway Metrics with Details  
                if (metrics.railway) {
                    html += '<div class="bg-white border rounded">' +
                        '<button onclick="toggleSection(\'' + assignmentId + '_railway\')" class="w-full p-3 text-left flex justify-between items-center hover:bg-gray-50">' +
                            '<span class="font-medium text-green-800">🚂 Railway: Deployment metrics available</span>' +
                            '<span class="text-xs text-gray-400" id="toggle-' + assignmentId + '_railway">▶</span>' +
                        '</button>' +
                        '<div id="details-' + assignmentId + '_railway" class="hidden p-3 border-t bg-gray-50">' +
                            '<div class="bg-white p-2 rounded border text-xs">' +
                                '<div class="space-y-1 text-gray-600">' +
                                    '<div>Project: sample-project</div>' +
                                    '<div>Total Deployments: 15</div>' +
                                    '<div>Successful: 14</div>' +
                                    '<div>Success Rate: ' + metrics.railway.success_rate + '%</div>' +
                                    '<div>Last Deploy: Aug 28, 2025 3:30 PM</div>' +
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
                }
                
                html += '</div>';
                metricsDiv.innerHTML = html;
                button.textContent = 'Refresh';
                button.disabled = false;
                
            } catch (error) {
                metricsDiv.innerHTML = '<div class="text-red-600 text-sm">Error: ' + error.message + '</div>';
                button.textContent = 'Retry';
                button.disabled = false;
            }
        }
        
        function toggleSection(sectionId) {
            const details = document.getElementById('details-' + sectionId);
            const toggle = document.getElementById('toggle-' + sectionId);
            
            if (details.classList.contains('hidden')) {
                details.classList.remove('hidden');
                toggle.textContent = '▼';
            } else {
                details.classList.add('hidden');
                toggle.textContent = '▶';
            }
        }
        
        document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route("/api/assignments")
def assignments():
    try:
        assignments_dir = 'backend/assignments'
        assignments = []
        
        if not os.path.exists(assignments_dir):
            return jsonify({"error": f"Assignments directory not found: {assignments_dir}"})
        
        for filename in os.listdir(assignments_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(assignments_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        assignment = json.load(f)
                        if assignment.get('status') != 'archived':
                            assignments.append(assignment)
                except json.JSONDecodeError as e:
                    print(f"Skipping {filename}: JSON error - {e}")
                    continue
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
                    continue
        
        return jsonify(assignments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/assignments/<assignment_id>/metrics")
def metrics(assignment_id):
    # Simple mock data that responds quickly
    mock_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "assignment_id": assignment_id,
        "github": [{"repo": "sample-repo", "commits": 42}],
        "aws": {"total_cost_last_30_days": "45.67"},
        "jira": {"resolution_rate": 78},
        "railway": {"success_rate": 93}
    }
    return jsonify(mock_data)

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
