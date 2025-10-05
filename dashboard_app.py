#!/usr/bin/env python3

from flask import Flask
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
            .expand-btn { transition: transform 0.2s; }
            .expand-btn.rotated { transform: rotate(90deg); }
            .section-content { max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; }
            .section-content.expanded { max-height: 1000px; }
        </style>
    </head>
    <body class="bg-gray-50 min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <header class="mb-8">
                <h1 class="text-4xl font-bold text-gray-900 mb-2">🚀 CTO Dashboard</h1>
                <p class="text-gray-600">Real-time insights across all projects and services</p>
                <div id="last-updated" class="text-sm text-gray-500 mt-2"></div>
            </header>
            
            <div id="loading" class="text-center py-12">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <p class="text-lg text-gray-600 mt-4">Loading dashboard data...</p>
            </div>
            
            <div id="dashboard-content" class="hidden space-y-6">
                <!-- Content will be loaded here -->
            </div>
        </div>

        <script>
            let dashboardData = {};

            async function loadDashboard() {
                try {
                    console.log('Loading assignments...');
                    const response = await fetch('/api/assignments');
                    const data = await response.json();
                    
                    document.getElementById('last-updated').textContent = 
                        'Last updated: ' + new Date().toLocaleString();
                    
                    if (data.assignments && data.assignments.length > 0) {
                        dashboardData = data;
                        renderDashboard(data.assignments);
                    } else {
                        showError('No assignments found');
                    }
                    
                    document.getElementById('loading').classList.add('hidden');
                    document.getElementById('dashboard-content').classList.remove('hidden');
                    
                } catch (error) {
                    console.error('Error loading dashboard:', error);
                    showError('Failed to load dashboard: ' + error.message);
                }
            }
            
            function showError(message) {
                document.getElementById('loading').innerHTML = 
                    '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">' + message + '</div>';
            }
            
            function renderDashboard(assignments) {
                const content = document.getElementById('dashboard-content');
                content.innerHTML = assignments.map(assignment => renderAssignmentCard(assignment)).join('');
            }
            
            function renderAssignmentCard(assignment) {
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
                                <div class="bg-gray-50 p-4 rounded-lg">
                                    <div class="text-2xl font-bold text-gray-900">${assignment.team_size || 0}</div>
                                    <div class="text-sm text-gray-600">Team Members</div>
                                </div>
                                <div class="bg-gray-50 p-4 rounded-lg">
                                    <div class="text-2xl font-bold text-gray-900">${assignment.team?.tech_stack?.length || 0}</div>
                                    <div class="text-sm text-gray-600">Technologies</div>
                                </div>
                                <div class="bg-gray-50 p-4 rounded-lg">
                                    <div class="text-2xl font-bold text-gray-900">${countEnabledServices(assignment.metrics_config)}</div>
                                    <div class="text-sm text-gray-600">Active Services</div>
                                </div>
                                <div class="bg-gray-50 p-4 rounded-lg">
                                    <div class="text-2xl font-bold text-gray-900">${calculateUptime(assignment.start_date)}</div>
                                    <div class="text-sm text-gray-600">Days Active</div>
                                </div>
                            </div>
                            
                            <!-- Service Sections -->
                            ${renderServiceSections(assignment)}
                            
                            <!-- Team & Tech Stack -->
                            <div class="mt-6">
                                <button onclick="toggleSection('${assignment.id}_team')" class="flex items-center w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100">
                                    <span class="expand-btn text-gray-400 mr-3">▶</span>
                                    <span class="font-semibold text-gray-800">👥 Team & Technology Stack</span>
                                </button>
                                <div id="${assignment.id}_team" class="section-content mt-2">
                                    <div class="p-4 bg-gray-50 rounded-lg">
                                        <div class="grid md:grid-cols-2 gap-6">
                                            <div>
                                                <h4 class="font-medium text-gray-800 mb-2">👥 Team Roles</h4>
                                                <div class="space-y-1">
                                                    ${(assignment.team?.roles || []).map(role => 
                                                        `<span class="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm mr-1 mb-1">${role}</span>`
                                                    ).join('')}
                                                </div>
                                            </div>
                                            <div>
                                                <h4 class="font-medium text-gray-800 mb-2">💻 Tech Stack</h4>
                                                <div class="space-y-1">
                                                    ${(assignment.team?.tech_stack || []).map(tech => 
                                                        `<span class="inline-block bg-green-100 text-green-800 px-2 py-1 rounded text-sm mr-1 mb-1">${tech}</span>`
                                                    ).join('')}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            function renderServiceSections(assignment) {
                const services = assignment.metrics_config || {};
                let html = '';
                
                // GitHub Section
                if (services.github?.enabled) {
                    html += `
                        <div class="mb-4">
                            <button onclick="toggleSection('${assignment.id}_github')" class="flex items-center w-full text-left p-3 bg-blue-50 rounded-lg hover:bg-blue-100">
                                <span class="expand-btn text-blue-400 mr-3">▶</span>
                                <span class="font-semibold text-blue-800">📊 GitHub Analytics</span>
                                <span class="ml-auto text-sm text-blue-600">${services.github.repos?.length || 0} repositories</span>
                            </button>
                            <div id="${assignment.id}_github" class="section-content mt-2">
                                <div class="p-4 bg-blue-50 rounded-lg">
                                    <div class="grid md:grid-cols-2 gap-4">
                                        <div>
                                            <h4 class="font-medium text-blue-800 mb-2">📦 Repository Overview</h4>
                                            <div class="space-y-2 text-sm">
                                                <div class="flex justify-between">
                                                    <span>Organization:</span>
                                                    <span class="font-medium">${services.github.org || 'N/A'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Active Repos:</span>
                                                    <span class="font-medium">${services.github.repos?.length || 0}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Deployment Tracking:</span>
                                                    <span class="font-medium">${services.github.track_deployments ? '✅ Enabled' : '❌ Disabled'}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div>
                                            <h4 class="font-medium text-blue-800 mb-2">📋 Tracked Repositories</h4>
                                            <div class="space-y-1">
                                                ${(services.github.repos || []).map(repo => 
                                                    `<div class="bg-white px-3 py-1 rounded border text-sm">${repo}</div>`
                                                ).join('')}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                // AWS Section
                if (services.aws?.enabled) {
                    html += `
                        <div class="mb-4">
                            <button onclick="toggleSection('${assignment.id}_aws')" class="flex items-center w-full text-left p-3 bg-orange-50 rounded-lg hover:bg-orange-100">
                                <span class="expand-btn text-orange-400 mr-3">▶</span>
                                <span class="font-semibold text-orange-800">☁️ AWS Infrastructure</span>
                                <span class="ml-auto text-sm text-orange-600">${services.aws.services?.length || 0} services monitored</span>
                            </button>
                            <div id="${assignment.id}_aws" class="section-content mt-2">
                                <div class="p-4 bg-orange-50 rounded-lg">
                                    <div class="grid md:grid-cols-2 gap-4">
                                        <div>
                                            <h4 class="font-medium text-orange-800 mb-2">🏗️ Infrastructure Details</h4>
                                            <div class="space-y-2 text-sm">
                                                <div class="flex justify-between">
                                                    <span>Account ID:</span>
                                                    <span class="font-medium font-mono">${services.aws.account_id || 'N/A'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Cost Tracking:</span>
                                                    <span class="font-medium">${services.aws.track_costs ? '✅ Enabled' : '❌ Disabled'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Services Count:</span>
                                                    <span class="font-medium">${services.aws.services?.length || 0}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div>
                                            <h4 class="font-medium text-orange-800 mb-2">🔧 Monitored Services</h4>
                                            <div class="space-y-1">
                                                ${(services.aws.services || []).map(service => 
                                                    `<div class="bg-white px-3 py-1 rounded border text-sm">${service}</div>`
                                                ).join('')}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                // Jira Section
                if (services.jira?.enabled) {
                    html += `
                        <div class="mb-4">
                            <button onclick="toggleSection('${assignment.id}_jira')" class="flex items-center w-full text-left p-3 bg-purple-50 rounded-lg hover:bg-purple-100">
                                <span class="expand-btn text-purple-400 mr-3">▶</span>
                                <span class="font-semibold text-purple-800">🎯 Jira Project Management</span>
                                <span class="ml-auto text-sm text-purple-600">Project: ${services.jira.project_key}</span>
                            </button>
                            <div id="${assignment.id}_jira" class="section-content mt-2">
                                <div class="p-4 bg-purple-50 rounded-lg">
                                    <div class="grid md:grid-cols-2 gap-4">
                                        <div>
                                            <h4 class="font-medium text-purple-800 mb-2">📊 Project Configuration</h4>
                                            <div class="space-y-2 text-sm">
                                                <div class="flex justify-between">
                                                    <span>Project Key:</span>
                                                    <span class="font-medium font-mono">${services.jira.project_key}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Bug Tracking:</span>
                                                    <span class="font-medium">${services.jira.track_bugs ? '✅ Enabled' : '❌ Disabled'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Sprint Tracking:</span>
                                                    <span class="font-medium">${services.jira.track_sprints ? '✅ Enabled' : '❌ Disabled'}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div>
                                            <h4 class="font-medium text-purple-800 mb-2">📈 Tracking Features</h4>
                                            <div class="space-y-2 text-sm">
                                                <div class="bg-white px-3 py-2 rounded border">
                                                    <div class="font-medium">Issue Management</div>
                                                    <div class="text-gray-600">Track bugs, features, and tasks</div>
                                                </div>
                                                <div class="bg-white px-3 py-2 rounded border">
                                                    <div class="font-medium">Sprint Analytics</div>
                                                    <div class="text-gray-600">Monitor sprint progress and velocity</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                // Railway Section
                if (services.railway?.enabled) {
                    html += `
                        <div class="mb-4">
                            <button onclick="toggleSection('${assignment.id}_railway')" class="flex items-center w-full text-left p-3 bg-green-50 rounded-lg hover:bg-green-100">
                                <span class="expand-btn text-green-400 mr-3">▶</span>
                                <span class="font-semibold text-green-800">🚂 Railway Deployments</span>
                                <span class="ml-auto text-sm text-green-600">Project: ${services.railway.project_id}</span>
                            </button>
                            <div id="${assignment.id}_railway" class="section-content mt-2">
                                <div class="p-4 bg-green-50 rounded-lg">
                                    <div class="grid md:grid-cols-2 gap-4">
                                        <div>
                                            <h4 class="font-medium text-green-800 mb-2">🚀 Deployment Details</h4>
                                            <div class="space-y-2 text-sm">
                                                <div class="flex justify-between">
                                                    <span>Project ID:</span>
                                                    <span class="font-medium font-mono">${services.railway.project_id}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Deployment Tracking:</span>
                                                    <span class="font-medium">${services.railway.track_deployments ? '✅ Enabled' : '❌ Disabled'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span>Usage Tracking:</span>
                                                    <span class="font-medium">${services.railway.track_usage ? '✅ Enabled' : '❌ Disabled'}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div>
                                            <h4 class="font-medium text-green-800 mb-2">📊 Monitoring Features</h4>
                                            <div class="space-y-2 text-sm">
                                                <div class="bg-white px-3 py-2 rounded border">
                                                    <div class="font-medium">Deployment Pipeline</div>
                                                    <div class="text-gray-600">Track build and deploy success rates</div>
                                                </div>
                                                <div class="bg-white px-3 py-2 rounded border">
                                                    <div class="font-medium">Resource Usage</div>
                                                    <div class="text-gray-600">Monitor CPU, memory, and bandwidth</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                return html;
            }
            
            function toggleSection(sectionId) {
                const content = document.getElementById(sectionId);
                const button = content.previousElementSibling.querySelector('.expand-btn');
                
                if (content.classList.contains('expanded')) {
                    content.classList.remove('expanded');
                    button.classList.remove('rotated');
                } else {
                    content.classList.add('expanded');
                    button.classList.add('rotated');
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
        
        return {"assignments": assignments, "count": len(assignments), "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/api/assignments/<assignment_id>/metrics")
def assignment_metrics(assignment_id):
    """Get detailed live metrics for a specific assignment"""
    try:
        # Mock detailed metrics data that would come from real APIs
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
                        "pull_requests": {
                            "open": 2,
                            "closed": 8,
                            "merged": 15
                        },
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
                        "pull_requests": {
                            "open": 1,
                            "closed": 4,
                            "merged": 7
                        },
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
                        "suggestions": ["Consider downsizing t3.medium to t3.small for development", "Terminate stopped instances"]
                    },
                    "S3": {
                        "cost_30_days": 23.15,
                        "buckets": [
                            {"name": "idpetech-backups", "size_gb": 145.2, "files": 2847, "cost": 18.50},
                            {"name": "idpetech-logs", "size_gb": 32.1, "files": 891, "cost": 4.65}
                        ],
                        "total_size_gb": 177.3,
                        "suggestions": ["Enable lifecycle policies for log bucket", "Consider compression for backup files"]
                    },
                    "RDS": {
                        "cost_30_days": 15.40,
                        "instances": [
                            {"id": "mydb-instance-1", "engine": "postgresql", "size": "db.t3.micro", "cost": 15.40}
                        ],
                        "suggestions": ["Database utilization is low, consider smaller instance"]
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
                        "suggestions": ["Optimize data-processor function memory allocation"]
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
        
        return metrics
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    print("🚀 Starting CTO Dashboard...")
    print("📍 Access at: http://localhost:3000")
    app.run(host="0.0.0.0", port=3000, debug=True)
