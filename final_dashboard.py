#!/usr/bin/env python3

from flask import Flask, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CTO Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .spinner { animation: spin 1s linear infinite; }
            @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            .expand-btn { transition: transform 0.2s; }
            .expand-btn.rotated { transform: rotate(90deg); }
        </style>
    </head>
    <body class="bg-gray-50 min-h-screen">
        <div class="container mx-auto px-4 py-8 max-w-6xl">
            <header class="mb-8">
                <h1 class="text-4xl font-bold text-gray-900 mb-2">🚀 CTO Dashboard</h1>
                <p class="text-gray-600">Real-time insights across all projects and services</p>
                <div id="last-updated" class="text-sm text-gray-500 mt-2"></div>
            </header>
            
            <div id="content"></div>
        </div>

        <script>
            async function loadDashboard() {
                const content = document.getElementById('content');
                content.innerHTML = `
                    <div class="text-center py-12">
                        <div class="spinner inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mb-4"></div>
                        <p class="text-lg text-gray-600">Loading dashboard data...</p>
                    </div>
                `;
                
                try {
                    console.log('Loading assignments...');
                    const response = await fetch('/api/assignments');
                    const data = await response.json();
                    
                    document.getElementById('last-updated').textContent = 
                        'Last updated: ' + new Date().toLocaleString();
                    
                    if (data.assignments && data.assignments.length > 0) {
                        await renderDashboard(data.assignments);
                    } else {
                        content.innerHTML = '<div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">No assignments found</div>';
                    }
                    
                } catch (error) {
                    console.error('Error loading dashboard:', error);
                    content.innerHTML = '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Error: ' + error.message + '</div>';
                }
            }
            
            async function renderDashboard(assignments) {
                const content = document.getElementById('content');
                let html = '<div class="space-y-6">';
                
                for (let assignment of assignments) {
                    html += await renderAssignmentCard(assignment);
                }
                
                html += '</div>';
                content.innerHTML = html;
            }
            
            async function renderAssignmentCard(assignment) {
                return `
                    <div class="bg-white rounded-lg shadow-lg overflow-hidden">
                        <!-- Assignment Header -->
                        <div class="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-6">
                            <div class="flex justify-between items-start">
                                <div>
                                    <h2 class="text-2xl font-bold">${assignment.name || 'Unnamed Assignment'}</h2>
                                    <p class="text-blue-100 mt-1">${assignment.description || 'No description available'}</p>
                                    <div class="flex items-center mt-3">
                                        <span class="px-3 py-1 bg-white bg-opacity-20 rounded-full text-sm">
                                            ${assignment.status || 'Unknown Status'}
                                        </span>
                                        <span class="ml-3 text-blue-100">
                                            Started: ${assignment.start_date ? new Date(assignment.start_date).toLocaleDateString() : 'Unknown'}
                                        </span>
                                    </div>
                                </div>
                                <div class="text-right">
                                    <div class="text-blue-100 text-sm">Monthly Burn Rate</div>
                                    <div class="text-3xl font-bold">$${(assignment.monthly_burn_rate || 0).toLocaleString()}</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Assignment Details -->
                        <div class="p-6">
                            <!-- Quick Stats -->
                            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                                <div class="bg-gray-50 p-4 rounded-lg text-center">
                                    <div class="text-2xl font-bold text-gray-900">${assignment.team_size || 0}</div>
                                    <div class="text-sm text-gray-600">Team Members</div>
                                </div>
                                <div class="bg-gray-50 p-4 rounded-lg text-center">
                                    <div class="text-2xl font-bold text-gray-900">${assignment.team?.tech_stack?.length || 0}</div>
                                    <div class="text-sm text-gray-600">Technologies</div>
                                </div>
                                <div class="bg-gray-50 p-4 rounded-lg text-center">
                                    <div class="text-2xl font-bold text-gray-900">${countEnabledServices(assignment.metrics_config)}</div>
                                    <div class="text-sm text-gray-600">Active Services</div>
                                </div>
                                <div class="bg-gray-50 p-4 rounded-lg text-center">
                                    <div class="text-2xl font-bold text-gray-900">${calculateUptime(assignment.start_date)}</div>
                                    <div class="text-sm text-gray-600">Days Active</div>
                                </div>
                            </div>
                            
                            <!-- Load Metrics Button -->
                            <div class="text-center mb-6">
                                <button onclick="loadMetrics('${assignment.id}')" 
                                        id="metrics-btn-${assignment.id}"
                                        class="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium">
                                    📊 Load Live Metrics
                                </button>
                            </div>
                            
                            <!-- Metrics Container -->
                            <div id="metrics-${assignment.id}" class="hidden">
                                <!-- Metrics will be loaded here -->
                            </div>
                        </div>
                    </div>
                `;
            }
            
            async function loadMetrics(assignmentId) {
                const button = document.getElementById(\`metrics-btn-\${assignmentId}\`);
                const container = document.getElementById(\`metrics-\${assignmentId}\`);
                
                // Show loading state
                button.disabled = true;
                button.innerHTML = '⏳ Loading Metrics...';
                container.classList.remove('hidden');
                container.innerHTML = \`
                    <div class="text-center py-8">
                        <div class="spinner inline-block w-6 h-6 border-4 border-blue-500 border-t-transparent rounded-full mb-2"></div>
                        <p class="text-gray-600">Fetching live metrics data...</p>
                    </div>
                \`;
                
                try {
                    const response = await fetch(\`/api/assignments/\${assignmentId}/metrics\`);
                    const metrics = await response.json();
                    
                    // Render detailed metrics
                    container.innerHTML = renderMetrics(assignmentId, metrics);
                    button.innerHTML = '🔄 Refresh Metrics';
                    button.disabled = false;
                    
                } catch (error) {
                    container.innerHTML = \`<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Error loading metrics: \${error.message}</div>\`;
                    button.innerHTML = '❌ Retry';
                    button.disabled = false;
                }
            }
            
            function renderMetrics(assignmentId, metrics) {
                let html = \`<div class="bg-gray-50 p-4 rounded-lg">\`;
                html += \`<div class="text-sm text-gray-500 mb-4">Updated: \${new Date(metrics.timestamp).toLocaleString()}</div>\`;
                
                // GitHub Section
                if (metrics.github) {
                    html += \`
                        <div class="mb-6">
                            <button onclick="toggleSection('\${assignmentId}_github_details')" class="flex items-center w-full text-left p-3 bg-blue-50 rounded-lg hover:bg-blue-100 mb-2">
                                <span class="expand-btn text-blue-400 mr-3">▶</span>
                                <span class="font-semibold text-blue-800">📊 GitHub Analytics</span>
                                <span class="ml-auto text-sm text-blue-600">\${metrics.github.repositories.length} repositories</span>
                            </button>
                            <div id="\${assignmentId}_github_details" class="hidden bg-blue-50 p-4 rounded-lg">
                                <div class="grid md:grid-cols-2 gap-4">
                                    <div>
                                        <h4 class="font-medium text-blue-800 mb-3">📦 Repository Details</h4>
                                        \${metrics.github.repositories.map(repo => \`
                                            <div class="bg-white p-3 rounded border mb-2">
                                                <div class="font-medium text-gray-900">\${repo.name}</div>
                                                <div class="text-sm text-gray-600 mt-1">
                                                    <div class="grid grid-cols-2 gap-1">
                                                        <div>⭐ \${repo.stars} stars</div>
                                                        <div>🍴 \${repo.forks} forks</div>
                                                        <div>📝 \${repo.commits_last_30_days} commits</div>
                                                        <div>❗ \${repo.open_issues} issues</div>
                                                        <div>👥 \${repo.contributors} contributors</div>
                                                        <div>📊 \${(repo.size_kb/1024).toFixed(1)} MB</div>
                                                    </div>
                                                </div>
                                            </div>
                                        \`).join('')}
                                    </div>
                                    <div>
                                        <h4 class="font-medium text-blue-800 mb-3">📈 Summary Stats</h4>
                                        <div class="bg-white p-3 rounded border">
                                            <div class="space-y-2 text-sm">
                                                <div class="flex justify-between">
                                                    <span>Total Commits (30d):</span>
                                                    <span class="font-medium">\${metrics.github.total_commits_30_days}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Active Branches:</span>
                                                    <span class="font-medium">\${metrics.github.active_branches}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Total Contributors:</span>
                                                    <span class="font-medium">\${metrics.github.total_contributors}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    \`;
                }
                
                // AWS Section  
                if (metrics.aws) {
                    html += \`
                        <div class="mb-6">
                            <button onclick="toggleSection('\${assignmentId}_aws_details')" class="flex items-center w-full text-left p-3 bg-orange-50 rounded-lg hover:bg-orange-100 mb-2">
                                <span class="expand-btn text-orange-400 mr-3">▶</span>
                                <span class="font-semibold text-orange-800">☁️ AWS Infrastructure</span>
                                <span class="ml-auto text-sm text-orange-600">$\${metrics.aws.cost_summary.total_cost_last_30_days} total cost</span>
                            </button>
                            <div id="\${assignmentId}_aws_details" class="hidden bg-orange-50 p-4 rounded-lg">
                                <div class="grid md:grid-cols-2 gap-4 mb-4">
                                    <div class="bg-white p-3 rounded border">
                                        <h4 class="font-medium text-orange-800 mb-2">💰 Cost Summary</h4>
                                        <div class="space-y-1 text-sm">
                                            <div class="flex justify-between">
                                                <span>30-Day Total:</span>
                                                <span class="font-medium">$\${metrics.aws.cost_summary.total_cost_last_30_days}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>Current Month:</span>
                                                <span class="font-medium">$\${metrics.aws.cost_summary.current_month_cost}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>Daily Average:</span>
                                                <span class="font-medium">$\${metrics.aws.cost_summary.daily_average}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>Trend:</span>
                                                <span class="font-medium">\${metrics.aws.cost_summary.weekly_trend === 'decreasing' ? '📉' : '📈'} \${metrics.aws.cost_summary.weekly_trend}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="bg-white p-3 rounded border">
                                        <h4 class="font-medium text-orange-800 mb-2">🎯 Optimization</h4>
                                        <div class="text-sm">
                                            <div class="mb-2">Score: <span class="font-bold text-lg">\${metrics.aws.optimization_score}/100</span></div>
                                            <div class="space-y-1">
                                                \${metrics.aws.recommendations.slice(0,3).map(rec => \`<div class="text-xs text-gray-600">• \${rec}</div>\`).join('')}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <h4 class="font-medium text-orange-800 mb-2">🔧 Service Breakdown</h4>
                                    <div class="grid md:grid-cols-3 gap-2 text-xs">
                                        \${Object.entries(metrics.aws.services).map(([service, data]) => \`
                                            <div class="bg-white p-2 rounded border">
                                                <div class="font-medium">\${service}</div>
                                                <div class="text-gray-600">$\${data.cost_30_days}</div>
                                                <div class="text-gray-500">\${data.instances?.length || data.buckets?.length || data.functions?.length || data.hosted_zones?.length || 1} resources</div>
                                            </div>
                                        \`).join('')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    \`;
                }
                
                // Jira Section
                if (metrics.jira) {
                    html += \`
                        <div class="mb-6">
                            <button onclick="toggleSection('\${assignmentId}_jira_details')" class="flex items-center w-full text-left p-3 bg-purple-50 rounded-lg hover:bg-purple-100 mb-2">
                                <span class="expand-btn text-purple-400 mr-3">▶</span>
                                <span class="font-semibold text-purple-800">🎯 Jira Project Management</span>
                                <span class="ml-auto text-sm text-purple-600">\${metrics.jira.issues.total} total issues</span>
                            </button>
                            <div id="\${assignmentId}_jira_details" class="hidden bg-purple-50 p-4 rounded-lg">
                                <div class="grid md:grid-cols-3 gap-4">
                                    <div class="bg-white p-3 rounded border">
                                        <h4 class="font-medium text-purple-800 mb-2">📊 Issue Status</h4>
                                        <div class="space-y-1 text-sm">
                                            <div class="flex justify-between">
                                                <span>🟢 Open:</span>
                                                <span class="font-medium">\${metrics.jira.issues.open}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>🟡 In Progress:</span>
                                                <span class="font-medium">\${metrics.jira.issues.in_progress}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>✅ Resolved:</span>
                                                <span class="font-medium">\${metrics.jira.issues.resolved}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="bg-white p-3 rounded border">
                                        <h4 class="font-medium text-purple-800 mb-2">🏃‍♂️ Sprint Progress</h4>
                                        <div class="space-y-1 text-sm">
                                            <div>Current: <span class="font-medium">\${metrics.jira.sprints.current_sprint}</span></div>
                                            <div>Completed: <span class="font-medium">\${metrics.jira.sprints.completed}/\${metrics.jira.sprints.issues_in_sprint}</span></div>
                                            <div>Velocity: <span class="font-medium">\${metrics.jira.sprints.velocity_last_3_sprints.join(', ')}</span></div>
                                        </div>
                                    </div>
                                    <div class="bg-white p-3 rounded border">
                                        <h4 class="font-medium text-purple-800 mb-2">🏷️ Issue Types</h4>
                                        <div class="space-y-1 text-sm">
                                            <div class="flex justify-between">
                                                <span>🐛 Bugs:</span>
                                                <span class="font-medium">\${metrics.jira.issue_types.bug}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>✨ Features:</span>
                                                <span class="font-medium">\${metrics.jira.issue_types.feature}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>📋 Tasks:</span>
                                                <span class="font-medium">\${metrics.jira.issue_types.task}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    \`;
                }
                
                // Railway Section
                if (metrics.railway) {
                    html += \`
                        <div class="mb-6">
                            <button onclick="toggleSection('\${assignmentId}_railway_details')" class="flex items-center w-full text-left p-3 bg-green-50 rounded-lg hover:bg-green-100 mb-2">
                                <span class="expand-btn text-green-400 mr-3">▶</span>
                                <span class="font-semibold text-green-800">🚂 Railway Deployments</span>
                                <span class="ml-auto text-sm text-green-600">\${metrics.railway.deployments.success_rate}% success rate</span>
                            </button>
                            <div id="\${assignmentId}_railway_details" class="hidden bg-green-50 p-4 rounded-lg">
                                <div class="grid md:grid-cols-2 gap-4">
                                    <div class="bg-white p-3 rounded border">
                                        <h4 class="font-medium text-green-800 mb-2">🚀 Deployment Stats</h4>
                                        <div class="space-y-1 text-sm">
                                            <div class="flex justify-between">
                                                <span>Total Deployments:</span>
                                                <span class="font-medium">\${metrics.railway.deployments.total}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>Successful:</span>
                                                <span class="font-medium text-green-600">\${metrics.railway.deployments.successful}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>Failed:</span>
                                                <span class="font-medium text-red-600">\${metrics.railway.deployments.failed}</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>Average Duration:</span>
                                                <span class="font-medium">\${metrics.railway.deployments.average_duration_seconds}s</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="bg-white p-3 rounded border">
                                        <h4 class="font-medium text-green-800 mb-2">💰 Usage & Cost</h4>
                                        <div class="space-y-1 text-sm">
                                            <div class="flex justify-between">
                                                <span>Bandwidth:</span>
                                                <span class="font-medium">\${metrics.railway.usage.bandwidth_gb_month} GB/mo</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>Build Minutes:</span>
                                                <span class="font-medium">\${metrics.railway.usage.build_minutes_month} min/mo</span>
                                            </div>
                                            <div class="flex justify-between">
                                                <span>Estimated Cost:</span>
                                                <span class="font-medium">$\${metrics.railway.usage.estimated_cost}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    \`;
                }
                
                html += \`</div>\`;
                return html;
            }
            
            function toggleSection(sectionId) {
                const section = document.getElementById(sectionId);
                const button = section.previousElementSibling.querySelector('.expand-btn');
                
                if (section.classList.contains('hidden')) {
                    section.classList.remove('hidden');
                    button.classList.add('rotated');
                } else {
                    section.classList.add('hidden');
                    button.classList.remove('rotated');
                }
            }
            
            function countEnabledServices(metricsConfig) {
                if (!metricsConfig) return 0;
                let count = 0;
                if (metricsConfig.github?.enabled) count++;
                if (metricsConfig.jira?.enabled) count++;
                if (metricsConfig.aws?.enabled) count++;
                if (metricsConfig.railway?.enabled) count++;
                return count;
            }
            
            function calculateUptime(startDate) {
                if (!startDate) return 0;
                const start = new Date(startDate);
                const now = new Date();
                const diffTime = Math.abs(now - start);
                return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            }
            
            // Load dashboard when page loads
            document.addEventListener('DOMContentLoaded', loadDashboard);
        </script>
    </body>
    </html>
    '''

@app.route("/api/assignments")
def assignments():
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
        
        return jsonify({"assignments": assignments, "count": len(assignments), "timestamp": datetime.utcnow().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/assignments/<assignment_id>/metrics")
def assignment_metrics(assignment_id):
    """Get detailed live metrics for a specific assignment"""
    try:
        # Mock detailed metrics data
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "assignment_id": assignment_id,
            "github": {
                "repositories": [
                    {
                        "name": "idpetech_portal",
                        "url": "https://github.com/idpetech/idpetech_portal",
                        "language": "Python",
                        "stars": 12,
                        "forks": 3,
                        "open_issues": 5,
                        "commits_last_30_days": 47,
                        "pull_requests": {"open": 2, "closed": 8, "merged": 15},
                        "last_commit": "2025-08-28T14:30:00Z",
                        "contributors": 4,
                        "size_kb": 2847
                    },
                    {
                        "name": "resumehealth-checker",
                        "url": "https://github.com/idpetech/resumehealth-checker",
                        "language": "JavaScript",
                        "stars": 8,
                        "forks": 1,
                        "open_issues": 2,
                        "commits_last_30_days": 23,
                        "pull_requests": {"open": 1, "closed": 4, "merged": 7},
                        "last_commit": "2025-08-27T09:15:00Z",
                        "contributors": 2,
                        "size_kb": 1203
                    }
                ],
                "total_commits_30_days": 70,
                "active_branches": 8,
                "total_contributors": 5
            },
            "aws": {
                "cost_summary": {
                    "total_cost_last_30_days": 127.45,
                    "current_month_cost": 89.32,
                    "daily_average": 4.25,
                    "weekly_trend": "decreasing",
                    "currency": "USD"
                },
                "services": {
                    "EC2": {
                        "cost_30_days": 78.90,
                        "instances": [
                            {"id": "i-0123456789abcdef0", "type": "t3.medium", "state": "running", "monthly_cost": 45.60},
                            {"id": "i-0987654321fedcba0", "type": "t3.small", "state": "stopped", "monthly_cost": 0.00}
                        ],
                        "suggestions": ["Consider downsizing t3.medium to t3.small", "Terminate stopped instances"]
                    },
                    "S3": {
                        "cost_30_days": 23.15,
                        "buckets": [
                            {"name": "idpetech-backups", "size_gb": 145.2, "files": 2847, "cost": 18.50},
                            {"name": "idpetech-logs", "size_gb": 32.1, "files": 891, "cost": 4.65}
                        ],
                        "total_size_gb": 177.3,
                        "suggestions": ["Enable lifecycle policies for log bucket"]
                    },
                    "RDS": {
                        "cost_30_days": 15.40,
                        "instances": [{"id": "mydb-instance-1", "engine": "postgresql", "size": "db.t3.micro", "cost": 15.40}],
                        "suggestions": ["Database utilization is low"]
                    },
                    "Route53": {
                        "cost_30_days": 2.50,
                        "hosted_zones": [
                            {"name": "idpetech.com", "records": 12, "queries_month": 15000},
                            {"name": "dev.idpetech.com", "records": 6, "queries_month": 3000}
                        ],
                        "suggestions": ["Consider consolidating dev subdomains"]
                    },
                    "Lambda": {
                        "cost_30_days": 7.50,
                        "functions": [
                            {"name": "data-processor", "invocations": 45000, "duration_ms": 2300, "cost": 5.20},
                            {"name": "email-sender", "invocations": 1200, "duration_ms": 890, "cost": 2.30}
                        ],
                        "suggestions": ["Optimize data-processor memory allocation"]
                    }
                },
                "optimization_score": 78,
                "recommendations": [
                    "Potential savings: $25-30/month",
                    "Enable AWS Cost Anomaly Detection", 
                    "Review EC2 instance sizing",
                    "Implement S3 lifecycle policies"
                ]
            },
            "jira": {
                "project_info": {
                    "key": "MFLP",
                    "name": "Main Project",
                    "lead": "john.doe@idpetech.com",
                    "created": "2024-01-15"
                },
                "issues": {
                    "total": 142,
                    "open": 23,
                    "in_progress": 8,
                    "resolved": 111,
                    "closed": 97
                },
                "sprints": {
                    "current_sprint": "Sprint 12",
                    "issues_in_sprint": 15,
                    "completed": 8,
                    "remaining": 7,
                    "velocity_last_3_sprints": [12, 14, 13]
                },
                "issue_types": {
                    "bug": 18,
                    "feature": 35,
                    "improvement": 12,
                    "task": 77
                },
                "recent_activity": [
                    {"type": "issue_created", "summary": "Add user authentication", "date": "2025-08-28"},
                    {"type": "issue_resolved", "summary": "Fix database connection", "date": "2025-08-27"},
                    {"type": "sprint_completed", "summary": "Sprint 11 finished", "date": "2025-08-25"}
                ]
            },
            "railway": {
                "project_info": {
                    "id": "successful-prosperity",
                    "name": "IdepTech Portal",
                    "created": "2024-02-01",
                    "region": "us-west-2"
                },
                "deployments": {
                    "total": 127,
                    "successful": 119,
                    "failed": 8,
                    "success_rate": 93.7,
                    "average_duration_seconds": 145,
                    "last_deployment": {
                        "id": "dep-xyz789",
                        "status": "success",
                        "date": "2025-08-28T16:45:00Z",
                        "duration_seconds": 132,
                        "commit": "abc123def"
                    }
                },
                "services": [
                    {
                        "name": "web-service",
                        "status": "healthy",
                        "cpu_usage": 24.5,
                        "memory_usage": 67.2,
                        "requests_last_hour": 1247
                    },
                    {
                        "name": "api-service", 
                        "status": "healthy",
                        "cpu_usage": 18.3,
                        "memory_usage": 45.1,
                        "requests_last_hour": 3456
                    }
                ],
                "usage": {
                    "bandwidth_gb_month": 89.4,
                    "build_minutes_month": 342,
                    "estimated_cost": 25.00
                }
            }
        }
        
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 Starting Final CTO Dashboard...")
    print("📍 Access at: http://localhost:3000")
    app.run(host="0.0.0.0", port=3000, debug=True)
