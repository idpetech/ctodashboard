#!/usr/bin/env python3
"""
Enhanced CTO Dashboard with Real AWS Data Integration
Uses the existing metrics_service.py from backend for real AWS data
"""

import os
import json
import sys
from datetime import datetime
from flask import Flask, jsonify

# Add backend directory to Python path to import metrics service
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Import real AWS metrics service
from metrics_service import AWSMetrics

app = Flask(__name__)

@app.route("/")
def index():
    """Main dashboard page with enhanced AWS integration"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🚀 CTO Dashboard - Real AWS Data</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .loading-spinner {
                border: 2px solid #f3f3f3;
                border-top: 2px solid #3498db;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                animation: spin 1s linear infinite;
                display: inline-block;
                margin-right: 8px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-4xl font-bold text-blue-600 mb-8">🚀 CTO Dashboard - Real AWS Data</h1>
            
            <div id="dashboard-content" class="space-y-6">
                <div class="text-center py-8">
                    <div class="loading-spinner"></div>
                    <span class="text-gray-600">Loading assignments and real AWS data...</span>
                </div>
            </div>
        </div>

        <script>
            async function loadDashboard() {
                try {
                    const response = await fetch('/api/assignments');
                    const data = await response.json();
                    
                    if (data.error) {
                        document.getElementById('dashboard-content').innerHTML = 
                            '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Error: ' + data.error + '</div>';
                        return;
                    }
                    
                    displayAssignments(data.assignments);
                    
                } catch (error) {
                    document.getElementById('dashboard-content').innerHTML = 
                        '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Failed to load dashboard: ' + error.message + '</div>';
                }
            }
            
            function displayAssignments(assignments) {
                let html = '<div class="grid gap-6">';
                
                if (assignments.length === 0) {
                    html += '<div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">No assignments found in backend/assignments/ directory</div>';
                } else {
                    assignments.forEach(assignment => {
                        html += '<div class="bg-white rounded-lg shadow-lg p-6">';
                        html += '<div class="flex justify-between items-start mb-4">';
                        html += '<div>';
                        html += '<h2 class="text-2xl font-bold text-gray-800">' + (assignment.name || assignment.id || 'Unknown Assignment') + '</h2>';
                        html += '<p class="text-gray-600">ID: ' + (assignment.id || 'N/A') + '</p>';
                        if (assignment.description) {
                            html += '<p class="text-gray-700 mt-2">' + assignment.description + '</p>';
                        }
                        html += '</div>';
                        
                        // Status badge
                        const statusColor = assignment.status === 'active' ? 'green' : 
                                          assignment.status === 'completed' ? 'blue' : 'yellow';
                        html += '<span class="px-3 py-1 bg-' + statusColor + '-100 text-' + statusColor + '-800 text-sm rounded-full">' + 
                                (assignment.status || 'unknown') + '</span>';
                        html += '</div>';
                        
                        // Metrics section
                        if (assignment.metrics_config) {
                            const enabledServices = countEnabledServices(assignment.metrics_config);
                            html += '<div class="bg-gray-50 rounded p-4 mb-4">';
                            html += '<h3 class="font-semibold text-gray-800 mb-2">📊 Enabled Services (' + enabledServices + ')</h3>';
                            html += '<div class="flex flex-wrap gap-2 mb-3">';
                            
                            if (assignment.metrics_config.github && assignment.metrics_config.github.enabled) {
                                html += '<span class="px-2 py-1 bg-purple-100 text-purple-800 text-sm rounded">GitHub</span>';
                            }
                            if (assignment.metrics_config.jira && assignment.metrics_config.jira.enabled) {
                                html += '<span class="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">Jira</span>';
                            }
                            if (assignment.metrics_config.aws && assignment.metrics_config.aws.enabled) {
                                html += '<span class="px-2 py-1 bg-orange-100 text-orange-800 text-sm rounded">AWS (Real Data)</span>';
                            }
                            if (assignment.metrics_config.railway && assignment.metrics_config.railway.enabled) {
                                html += '<span class="px-2 py-1 bg-green-100 text-green-800 text-sm rounded">Railway</span>';
                            }
                            
                            html += '</div>';
                            html += '<button onclick="loadRealMetrics(\'' + assignment.id + '\')" ';
                            html += 'class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">';
                            html += '🔄 Load Real AWS Metrics</button>';
                            html += '</div>';
                        }
                        
                        // Dates
                        html += '<div class="text-sm text-gray-500 mt-4">';
                        if (assignment.created_date) {
                            html += '<div>Created: ' + new Date(assignment.created_date).toLocaleDateString() + '</div>';
                        }
                        if (assignment.last_modified) {
                            html += '<div>Modified: ' + new Date(assignment.last_modified).toLocaleDateString() + '</div>';
                        }
                        html += '</div>';
                        
                        // Metrics display area
                        html += '<div id="metrics-' + assignment.id + '" class="mt-4"></div>';
                        
                        html += '</div>';
                    });
                }
                
                html += '</div>';
                document.getElementById('dashboard-content').innerHTML = html;
            }
            
            async function loadRealMetrics(assignmentId) {
                const metricsDiv = document.getElementById('metrics-' + assignmentId);
                metricsDiv.innerHTML = '<div class="bg-blue-50 p-4 rounded"><div class="loading-spinner"></div>Loading real AWS data...</div>';
                
                try {
                    const response = await fetch('/api/assignments/' + assignmentId + '/real-metrics');
                    const data = await response.json();
                    
                    if (data.error) {
                        metricsDiv.innerHTML = '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">AWS Error: ' + data.error + '</div>';
                        return;
                    }
                    
                    displayRealMetrics(data, metricsDiv);
                    
                } catch (error) {
                    metricsDiv.innerHTML = '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Failed to load real metrics: ' + error.message + '</div>';
                }
            }
            
            function displayRealMetrics(metrics, container) {
                let html = '<div class="bg-gray-50 rounded-lg p-4">';
                html += '<h3 class="text-xl font-bold text-gray-800 mb-4">📊 Real AWS Metrics - ' + new Date(metrics.timestamp).toLocaleString() + '</h3>';
                
                // AWS Real Data Section
                if (metrics.aws) {
                    html += '<div class="mb-6">';
                    html += '<h4 class="text-lg font-semibold text-orange-600 mb-3">☁️ AWS Cost Analysis (Real Data)</h4>';
                    
                    if (metrics.aws.error) {
                        html += '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">AWS API Error: ' + metrics.aws.error + '</div>';
                    } else {
                        // Cost Summary
                        html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">';
                        html += '<div class="bg-white p-4 rounded border">';
                        html += '<h5 class="font-medium text-gray-800 mb-2">💰 30-Day Total Cost</h5>';
                        html += '<div class="text-2xl font-bold text-green-600">$' + (metrics.aws.total_cost_last_30_days || 0) + '</div>';
                        html += '<div class="text-sm text-gray-600">' + (metrics.aws.currency || 'USD') + '</div>';
                        html += '</div>';
                        
                        html += '<div class="bg-white p-4 rounded border">';
                        html += '<h5 class="font-medium text-gray-800 mb-2">📈 Trend Analysis</h5>';
                        if (metrics.aws.cto_insights && metrics.aws.cto_insights.cost_trend) {
                            const trend = metrics.aws.cto_insights.cost_trend;
                            html += '<div class="text-lg font-semibold ' + (trend.weekly_trend === 'increasing' ? 'text-red-600' : 'text-green-600') + '">';
                            html += trend.weekly_trend === 'increasing' ? '📈 Increasing' : '📉 Decreasing';
                            html += '</div>';
                            html += '<div class="text-sm text-gray-600">Daily Average: $' + (trend.daily_average || 0) + '</div>';
                        } else {
                            html += '<div class="text-gray-600">No trend data available</div>';
                        }
                        html += '</div>';
                        
                        html += '<div class="bg-white p-4 rounded border">';
                        html += '<h5 class="font-medium text-gray-800 mb-2">🔧 Resource Inventory</h5>';
                        if (metrics.aws.cto_insights && metrics.aws.cto_insights.resource_inventory) {
                            const inventory = metrics.aws.cto_insights.resource_inventory;
                            let resourceCount = 0;
                            if (inventory.ec2 && inventory.ec2.total_instances) resourceCount += inventory.ec2.total_instances;
                            if (inventory.rds && inventory.rds.total_databases) resourceCount += inventory.rds.total_databases;
                            if (inventory.s3 && inventory.s3.total_buckets) resourceCount += inventory.s3.total_buckets;
                            if (inventory.lightsail && inventory.lightsail.total_instances) resourceCount += inventory.lightsail.total_instances;
                            
                            html += '<div class="text-lg font-semibold text-blue-600">' + resourceCount + ' Resources</div>';
                            html += '<div class="text-sm text-gray-600">Across all services</div>';
                        } else {
                            html += '<div class="text-gray-600">Resource count unavailable</div>';
                        }
                        html += '</div>';
                        html += '</div>';
                        
                        // Service Breakdown
                        if (metrics.aws.top_services && Object.keys(metrics.aws.top_services).length > 0) {
                            html += '<div class="bg-white p-4 rounded border mb-4">';
                            html += '<h5 class="font-medium text-gray-800 mb-3">🏷️ Top Services by Cost</h5>';
                            html += '<div class="space-y-2">';
                            
                            for (const [service, cost] of Object.entries(metrics.aws.top_services)) {
                                if (cost > 0) {
                                    html += '<div class="flex justify-between items-center">';
                                    html += '<span class="text-sm text-gray-700">' + service + '</span>';
                                    html += '<span class="font-medium text-gray-900">$' + parseFloat(cost).toFixed(2) + '</span>';
                                    html += '</div>';
                                }
                            }
                            html += '</div></div>';
                        }
                        
                        // CTO Recommendations
                        if (metrics.aws.cto_insights && metrics.aws.cto_insights.optimization_recommendations) {
                            html += '<div class="bg-yellow-50 border border-yellow-200 p-4 rounded">';
                            html += '<h5 class="font-medium text-yellow-800 mb-3">💡 CTO Optimization Recommendations</h5>';
                            html += '<div class="space-y-1 text-sm text-yellow-700">';
                            
                            const recommendations = metrics.aws.cto_insights.optimization_recommendations;
                            recommendations.slice(0, 10).forEach(rec => {
                                html += '<div>' + rec + '</div>';
                            });
                            html += '</div></div>';
                        }
                    }
                    html += '</div>';
                }
                
                // Other mock services (GitHub, Jira, Railway) for completeness
                if (metrics.github) {
                    html += '<div class="mb-4">';
                    html += '<h4 class="text-lg font-semibold text-purple-600 mb-2">🐙 GitHub (Mock Data)</h4>';
                    html += '<div class="bg-white p-3 rounded border text-sm text-gray-600">';
                    html += 'Mock GitHub data - integrate with real GitHubMetrics class from metrics_service.py';
                    html += '</div>';
                    html += '</div>';
                }
                
                html += '</div>';
                container.innerHTML = html;
            }
            
            function countEnabledServices(metricsConfig) {
                if (!metricsConfig) return 0;
                let count = 0;
                if (metricsConfig.github && metricsConfig.github.enabled) count++;
                if (metricsConfig.jira && metricsConfig.jira.enabled) count++;
                if (metricsConfig.aws && metricsConfig.aws.enabled) count++;
                if (metricsConfig.railway && metricsConfig.railway.enabled) count++;
                return count;
            }
            
            // Load dashboard when page loads
            document.addEventListener('DOMContentLoaded', loadDashboard);
        </script>
    </body>
    </html>
    '''

@app.route("/api/assignments")
def assignments():
    """Get assignments from backend directory"""
    try:
        assignments_dir = 'backend/assignments'
        assignments = []
        
        if os.path.exists(assignments_dir):
            for filename in os.listdir(assignments_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(assignments_dir, filename), 'r') as f:
                            data = json.load(f)
                            assignments.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Skipping {filename}: JSON error - {e}")
                        continue
        
        return jsonify({"assignments": assignments, "count": len(assignments), "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/assignments/<assignment_id>/real-metrics")
def real_assignment_metrics(assignment_id):
    """Get REAL AWS metrics for a specific assignment using metrics_service.py"""
    try:
        # Initialize real AWS metrics service
        aws_metrics = AWSMetrics()
        
        # Get comprehensive AWS report with real data
        real_aws_data = aws_metrics.get_cost_metrics()
        
        # Structure response similar to mock format but with real data
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "assignment_id": assignment_id,
            "data_source": "REAL AWS APIs via boto3",
            "aws": real_aws_data
        }
        
        # Add mock data for other services for now
        # TODO: Integrate real GitHub, Jira, Railway data similarly
        metrics["github"] = {"note": "Mock data - ready for real GitHub integration"}
        metrics["jira"] = {"note": "Mock data - ready for real Jira integration"}  
        metrics["railway"] = {"note": "Mock data - Railway API currently unavailable"}
        
        return jsonify(metrics)
    except Exception as e:
        return jsonify({
            "error": f"Real AWS metrics error: {str(e)}",
            "note": "Check AWS credentials and permissions",
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == "__main__":
    print("🚀 Starting Real AWS Dashboard...")
    print("📍 Access at: http://localhost:6000")
    print("💡 This version uses REAL AWS data via boto3!")
    app.run(host="0.0.0.0", port=6000, debug=True)
