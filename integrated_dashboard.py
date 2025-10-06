#!/usr/bin/env python3
"""
Integrated CTO Dashboard with embedded AWS functions
All AWS logic is directly embedded - no client-server dependencies
"""

import os
import json
import boto3
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, request, send_from_directory
from flask_cors import CORS
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join('backend', '.env'))
from services.service_manager import ServiceManager, WorkstreamService, ServiceConfigService, TenantService, service_manager
from services.embedded.aws_metrics import EmbeddedAWSMetrics
from services.embedded.github_metrics import EmbeddedGitHubMetrics
from services.embedded.jira_metrics import EmbeddedJiraMetrics
from services.embedded.openai_metrics import OpenAIMetrics

# Configure Flask to serve static files from React build
static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'dist')
app = Flask(__name__, static_folder=static_folder, static_url_path='')

# Enable CORS for all routes
CORS(app, origins=["*"])

# Feature Flags - Phase 1: Foundation
# All flags disabled by default to maintain existing functionality
FEATURE_FLAGS = {
    "multi_tenancy": os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true",
    "workstream_management": os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true",
    "service_config_ui": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true",
    "advanced_billing": os.getenv("ENABLE_BILLING", "false").lower() == "true",
    "database_storage": os.getenv("ENABLE_DATABASE", "false").lower() == "true"
}

# Service Layer - Phase 1.2: Foundation
# Service classes for SaaS architecture (all disabled by default)
service_manager = ServiceManager()


class EmbeddedGitHubMetrics:
    """Jira metrics embedded directly in the Flask app"""
    return '''
                
                <!-- Chatbot Messages -->
                <div id="chatbot-messages" class="flex-1 overflow-y-auto p-4 space-y-4">
                    <div class="text-center text-gray-500 py-8">
                        <div class="text-4xl mb-4">🤖</div>
                        <h3 class="text-lg font-medium mb-2">Welcome to CTO Dashboard Assistant!</h3>
                        <p class="text-sm">I can help you with questions about:</p>
                        <ul class="text-sm mt-2 space-y-1">
                            <li>• Your assignments and projects</li>
                            <li>• AWS costs and resource usage</li>
                            <li>• GitHub metrics and activity</li>
                            <li>• Jira project status</li>
                            <li>• Team information and tech stacks</li>
                            <li>• Service health and configuration</li>
                        </ul>
                        <p class="text-sm mt-4 text-gray-400">Try asking: "What is IdepTech status?" or "Show me IdepTech AWS costs"</p>
                    </div>
                </div>
                
                <!-- Chatbot Input -->
                <div class="p-4 border-t">
                    <div class="flex space-x-2">
                        <input type="text" id="chatbot-input" placeholder="Ask me about IdepTech, assignments, costs, metrics..." class="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" onkeypress="handleChatbotKeyPress(event)">
                        <button onclick="sendChatbotMessage()" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                            Send
                        </button>
                    </div>
                    
                    <!-- Quick action buttons -->
                    <div class="flex flex-wrap gap-2 mt-2">
                        <button onclick="setChatbotInput('What is the status of IdepTech assignment?')" class="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors">
                            IdepTech Status
                        </button>
                        <button onclick="setChatbotInput('Show me IdepTech AWS costs')" class="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors">
                            IdepTech AWS Costs
                        </button>
                        <button onclick="setChatbotInput('What is IdepTech monthly burn rate?')" class="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors">
                            IdepTech Burn Rate
                        </button>
                        <button onclick="setChatbotInput('Show me IdepTech GitHub activity')" class="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors">
                            IdepTech GitHub
                        </button>
                        <button onclick="setChatbotInput('What is IdepTech team size?')" class="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors">
                            IdepTech Team
                        </button>
                    </div>
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
                if (assignments.length === 0) {
                    document.getElementById('dashboard-content').innerHTML = 
                        '<div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">No assignments found in backend/assignments/ directory</div>';
                    return;
                }
                
                // Store assignments globally for tab switching
                window.assignments = assignments;
                
                // Create tab navigation
                let html = '<div class="bg-white rounded-lg shadow-lg mb-6">';
                html += '<div class="flex border-b border-gray-200">';
                
                // Main Overview Tab
                html += '<button onclick="showTab(' + "'overview'" + ')" id="tab-overview" class="px-6 py-4 text-sm font-medium text-gray-700 hover:text-blue-600 hover:border-b-2 hover:border-blue-600 tab-button active-tab">';
                html += '📊 Overview (' + assignments.length + ')';
                html += '</button>';
                
                // Individual Assignment Tabs
                assignments.forEach(assignment => {
                    const statusEmoji = assignment.status === 'active' ? '🟢' : 
                                       assignment.status === 'completed' ? '🔵' : '🟡';
                    html += '<button onclick="showTab(' + "'assignment-" + assignment.id + "'" + ')" id="tab-assignment-' + assignment.id + '" class="px-6 py-4 text-sm font-medium text-gray-700 hover:text-blue-600 hover:border-b-2 hover:border-blue-600 tab-button">';
                    html += statusEmoji + ' ' + (assignment.name || assignment.id);
                    html += '</button>';
                });
                
                html += '</div>';
                html += '</div>';
                
                // Tab Content Areas
                html += '<div id="tab-content">';
                
                // Overview Tab Content
                html += '<div id="overview-content" class="tab-content">';
                html += generateOverviewContent(assignments);
                html += '</div>';
                
                // Individual Assignment Tab Contents
                assignments.forEach(assignment => {
                    html += '<div id="assignment-' + assignment.id + '-content" class="tab-content hidden">';
                    html += generateAssignmentContent(assignment);
                    html += '</div>';
                });
                
                html += '</div>';
                
                document.getElementById('dashboard-content').innerHTML = html;
            }
            
            function generateOverviewContent(assignments) {
                // Calculate statistics
                const activeCount = assignments.filter(a => a.status === 'active').length;
                const completedCount = assignments.filter(a => a.status === 'completed').length;
                const archivedCount = assignments.filter(a => a.status === 'archived').length;
                const totalTeamSize = assignments.reduce((sum, a) => sum + (a.team_size || 0), 0);
                const totalBurnRate = assignments.reduce((sum, a) => sum + (a.monthly_burn_rate || 0), 0);
                
                let html = '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">';
                
                // Status Cards
                html += '<div class="bg-green-50 border border-green-200 rounded-lg p-4">';
                html += '<div class="flex items-center">';
                html += '<div class="text-3xl mr-3">🟢</div>';
                html += '<div>';
                html += '<h3 class="text-lg font-semibold text-green-800">Active</h3>';
                html += '<p class="text-2xl font-bold text-green-600">' + activeCount + '</p>';
                html += '</div>';
                html += '</div></div>';
                
                html += '<div class="bg-blue-50 border border-blue-200 rounded-lg p-4">';
                html += '<div class="flex items-center">';
                html += '<div class="text-3xl mr-3">🔵</div>';
                html += '<div>';
                html += '<h3 class="text-lg font-semibold text-blue-800">Completed</h3>';
                html += '<p class="text-2xl font-bold text-blue-600">' + completedCount + '</p>';
                html += '</div>';
                html += '</div></div>';
                
                html += '<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">';
                html += '<div class="flex items-center">';
                html += '<div class="text-3xl mr-3">🟡</div>';
                html += '<div>';
                html += '<h3 class="text-lg font-semibold text-yellow-800">Archived</h3>';
                html += '<p class="text-2xl font-bold text-yellow-600">' + archivedCount + '</p>';
                html += '</div>';
                html += '</div></div>';
                
                html += '<div class="bg-purple-50 border border-purple-200 rounded-lg p-4">';
                html += '<div class="flex items-center">';
                html += '<div class="text-3xl mr-3">👥</div>';
                html += '<div>';
                html += '<h3 class="text-lg font-semibold text-purple-800">Total Team</h3>';
                html += '<p class="text-2xl font-bold text-purple-600">' + totalTeamSize + '</p>';
                html += '</div>';
                html += '</div></div>';
                
                html += '</div>';
                
                // Assignments Summary Table
                html += '<div class="bg-white rounded-lg shadow p-6">';
                html += '<h3 class="text-xl font-bold text-gray-800 mb-4">📋 All Assignments</h3>';
                html += '<div class="overflow-x-auto">';
                html += '<table class="min-w-full table-auto">';
                html += '<thead><tr class="bg-gray-50">';
                html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Name</th>';
                html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Status</th>';
                html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Team Size</th>';
                html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Monthly Burn</th>';
                html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Services</th>';
                html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Action</th>';
                html += '</tr></thead><tbody>';
                
                assignments.forEach(assignment => {
                    const statusColor = assignment.status === 'active' ? 'green' : 
                                       assignment.status === 'completed' ? 'blue' : 'yellow';
                    const statusEmoji = assignment.status === 'active' ? '🟢' : 
                                       assignment.status === 'completed' ? '🔵' : '🟡';
                    
                    html += '<tr class="border-b border-gray-200">';
                    html += '<td class="px-4 py-3">';
                    html += '<div class="font-medium text-gray-900">' + (assignment.name || assignment.id) + '</div>';
                    html += '<div class="text-sm text-gray-500">' + (assignment.description || '') + '</div>';
                    html += '</td>';
                    html += '<td class="px-4 py-3">';
                    html += '<span class="inline-flex items-center px-2 py-1 bg-' + statusColor + '-100 text-' + statusColor + '-800 text-xs rounded-full">';
                    html += statusEmoji + ' ' + (assignment.status || 'unknown');
                    html += '</span></td>';
                    html += '<td class="px-4 py-3 text-sm text-gray-900">' + (assignment.team_size || 'N/A') + '</td>';
                    html += '<td class="px-4 py-3 text-sm text-gray-900">$' + (assignment.monthly_burn_rate || 0).toLocaleString() + '</td>';
                    html += '<td class="px-4 py-3">';
                    
                    if (assignment.metrics_config) {
                        const services = [];
                        if (assignment.metrics_config.github?.enabled) services.push('GitHub');
                        if (assignment.metrics_config.jira?.enabled) services.push('Jira');
                        if (assignment.metrics_config.aws?.enabled) services.push('AWS');
                        if (assignment.metrics_config.railway?.enabled) services.push('Railway');
                        
                        services.forEach(service => {
                            const color = service === 'GitHub' ? 'purple' : 
                                         service === 'Jira' ? 'blue' : 
                                         service === 'AWS' ? 'orange' : 'green';
                            html += '<span class="inline-block px-2 py-1 bg-' + color + '-100 text-' + color + '-800 text-xs rounded mr-1 mb-1">' + service + '</span>';
                        });
                    }
                    
                    html += '</td>';
                    html += '<td class="px-4 py-3">';
                    html += '<button onclick="showTab(' + "'assignment-" + assignment.id + "'" + ')" class="bg-blue-600 text-white px-3 py-1 text-sm rounded hover:bg-blue-700">View Details</button>';
                    html += '</td>';
                    html += '</tr>';
                });
                
                html += '</tbody></table></div></div>';
                
                return html;
            }
            
            function generateAssignmentContent(assignment) {
                let html = '<div class="bg-white rounded-lg shadow-lg p-6">';
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
                
                // Assignment Details
                html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">';
                html += '<div class="bg-gray-50 rounded p-4">';
                html += '<h4 class="font-semibold text-gray-700 mb-2">👥 Team Size</h4>';
                html += '<p class="text-2xl font-bold text-blue-600">' + (assignment.team_size || 'N/A') + '</p>';
                html += '</div>';
                html += '<div class="bg-gray-50 rounded p-4">';
                html += '<h4 class="font-semibold text-gray-700 mb-2">💰 Monthly Burn</h4>';
                html += '<p class="text-2xl font-bold text-green-600">$' + (assignment.monthly_burn_rate || 0).toLocaleString() + '</p>';
                html += '</div>';
                html += '<div class="bg-gray-50 rounded p-4">';
                html += '<h4 class="font-semibold text-gray-700 mb-2">📅 Duration</h4>';
                html += '<p class="text-sm text-gray-600">Started: ' + (assignment.start_date || 'N/A') + '</p>';
                html += '<p class="text-sm text-gray-600">End: ' + (assignment.end_date || 'Ongoing') + '</p>';
                html += '</div>';
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
                    if (assignment.metrics_config.openai && assignment.metrics_config.openai.enabled) {
                        html += '<span class="px-2 py-1 bg-purple-100 text-purple-800 text-sm rounded">🤖 OpenAI</span>';
                    }
                    
                    html += '</div>';
                    html += '<button data-assignment-id="' + assignment.id + '" ';
                    html += 'onclick="loadRealMetrics(this.getAttribute(&quot;data-assignment-id&quot;))" ';
                    html += 'class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">';
                    html += '🔄 Load All Metrics</button>';
                    html += '</div>';
                }
                
                // Tech Stack
                if (assignment.team && assignment.team.tech_stack) {
                    html += '<div class="bg-gray-50 rounded p-4 mb-4">';
                    html += '<h4 class="font-semibold text-gray-700 mb-2">🛠️ Tech Stack</h4>';
                    html += '<div class="flex flex-wrap gap-2">';
                    assignment.team.tech_stack.forEach(tech => {
                        html += '<span class="px-2 py-1 bg-indigo-100 text-indigo-800 text-sm rounded">' + tech + '</span>';
                    });
                    html += '</div></div>';
                }
                
                // Metrics display area
                html += '<div id="metrics-' + assignment.id + '" class="mt-4"></div>';
                
                html += '</div>';
                
                return html;
            }
            
            async function loadRealMetrics(assignmentId) {
                const metricsDiv = document.getElementById('metrics-' + assignmentId);
                metricsDiv.innerHTML = '<div class="bg-blue-50 p-4 rounded"><div class="loading-spinner"></div>Loading all metrics data...</div>';
                
                try {
                    const response = await fetch('/api/all-metrics/' + assignmentId);
                    const data = await response.json();
                    
                    if (data.error) {
                        metricsDiv.innerHTML = '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Metrics Error: ' + data.error + '</div>';
                        return;
                    }
                    
                    displayAllMetrics(data, metricsDiv);
                    
                } catch (error) {
                    metricsDiv.innerHTML = '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Failed to load metrics: ' + error.message + '</div>';
                }
            }
            
            function displayAllMetrics(metrics, container) {
                let html = '<div class="bg-gray-50 rounded-lg p-4">';
                html += '<h3 class="text-xl font-bold text-gray-800 mb-4">📊 All Metrics - ' + new Date().toLocaleString() + '</h3>';
                
                // GitHub Metrics
                if (metrics.github && Array.isArray(metrics.github)) {
                    html += '<div class="bg-purple-50 border border-purple-200 rounded mb-4">';
                    html += '<div class="cursor-pointer p-4 hover:bg-purple-100" onclick="toggleSection(' + "'github-section'" + ')">';
                    html += '<h4 class="text-lg font-semibold text-purple-800 flex items-center">';
                    html += '<span id="github-section-icon" class="mr-2">▶️</span>';
                    html += '🚀 GitHub Repositories (' + metrics.github.length + ')';
                    html += '</h4></div>';
                    html += '<div id="github-section" class="hidden p-4 pt-0">';
                    
                    metrics.github.forEach(repo => {
                        if (repo.error) {
                            html += '<div class="bg-red-100 text-red-700 p-2 rounded mb-2">Error: ' + repo.error + '</div>';
                        } else {
                            html += '<div class="bg-white p-3 rounded border mb-2">';
                            html += '<div class="flex justify-between items-start">';
                            html += '<div>';
                            html += '<h5 class="font-medium text-gray-800">' + repo.repo_name + '</h5>';
                            html += '<div class="text-sm text-gray-600">Language: ' + repo.language + '</div>';
                            html += '</div>';
                            html += '<div class="text-right text-sm">';
                            html += '<div>⭐ ' + repo.stars + ' stars</div>';
                            html += '<div>🔄 ' + repo.commits_last_30_days + ' commits (30d)</div>';
                            html += '<div>📝 ' + repo.total_prs + ' PRs</div>';
                            html += '<div>🚨 ' + repo.open_issues + ' issues</div>';
                            html += '</div>';
                            html += '</div>';
                            html += '</div>';
                        }
                    });
                    
                    // GitHub Recommendations
                    html += '<div class="bg-purple-100 p-3 rounded mt-3">';
                    html += '<h5 class="font-medium text-purple-800 mb-2">🚀 GitHub Development Insights</h5>';
                    html += '<ul class="space-y-1 text-xs text-purple-700">';
                    
                    let totalCommits = 0;
                    let totalStars = 0;
                    let totalIssues = 0;
                    let activeRepos = 0;
                    
                    metrics.github.forEach(repo => {
                        if (!repo.error) {
                            totalCommits += repo.commits_last_30_days || 0;
                            totalStars += repo.stars || 0;
                            totalIssues += repo.open_issues || 0;
                            if (repo.commits_last_30_days > 0) activeRepos++;
                        }
                    });
                    
                    if (totalCommits < 50) {
                        html += '<li>• 🔍 Low commit activity (' + totalCommits + '/month) - consider increasing development velocity</li>';
                    } else {
                        html += '<li>• ✅ Good development activity (' + totalCommits + ' commits/month)</li>';
                    }
                    
                    if (totalIssues > 20) {
                        html += '<li>• ⚠️ High open issue count (' + totalIssues + ') - prioritize technical debt reduction</li>';
                    }
                    
                    if (activeRepos === 0) {
                        html += '<li>• 🚨 No active repositories - investigate development process</li>';
                    } else {
                        html += '<li>• 📈 ' + activeRepos + ' active repositories - maintain code quality standards</li>';
                    }
                    
                    html += '<li>• 📚 Consider implementing automated testing and CI/CD pipelines</li>';
                    html += '</ul>';
                    html += '</div>';
                    
                    html += '</div>';
                    html += '</div>';
                }
                
                // Jira Metrics
                if (metrics.jira && !metrics.jira.error) {
                    html += '<div class="bg-blue-50 border border-blue-200 rounded mb-4">';
                    html += '<div class="cursor-pointer p-4 hover:bg-blue-100" onclick="toggleSection(' + "'jira-section'" + ')">';
                    html += '<h4 class="text-lg font-semibold text-blue-800 flex items-center">';
                    html += '<span id="jira-section-icon" class="mr-2">▶️</span>';
                    html += '📋 Jira Project: ' + metrics.jira.project_name;
                    html += '</h4></div>';
                    html += '<div id="jira-section" class="hidden p-4 pt-0">';
                    html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">';
                    
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">Total Issues (30d)</div>';
                    html += '<div class="text-xl font-bold text-blue-600">' + metrics.jira.total_issues_last_30_days + '</div>';
                    html += '</div>';
                    
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">Resolved Issues</div>';
                    html += '<div class="text-xl font-bold text-green-600">' + metrics.jira.resolved_issues_last_30_days + '</div>';
                    html += '</div>';
                    
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">Resolution Rate</div>';
                    html += '<div class="text-xl font-bold text-purple-600">' + metrics.jira.resolution_rate + '%</div>';
                    html += '</div>';
                    
                    html += '</div>';
                    
                    // Jira Recommendations
                    html += '<div class="bg-blue-100 p-3 rounded mt-3">';
                    html += '<h5 class="font-medium text-blue-800 mb-2">📋 Project Management Insights</h5>';
                    html += '<ul class="space-y-1 text-xs text-blue-700">';
                    
                    const resolutionRate = metrics.jira.resolution_rate || 0;
                    const totalIssues = metrics.jira.total_issues_last_30_days || 0;
                    
                    if (resolutionRate < 70) {
                        html += '<li>• 🔴 Low resolution rate (' + resolutionRate + '%) - review sprint planning and capacity</li>';
                    } else if (resolutionRate < 85) {
                        html += '<li>• 🟡 Moderate resolution rate (' + resolutionRate + '%) - optimize workflow efficiency</li>';
                    } else {
                        html += '<li>• 🟢 Excellent resolution rate (' + resolutionRate + '%) - maintain current velocity</li>';
                    }
                    
                    if (totalIssues < 10) {
                        html += '<li>• 📉 Low issue creation (' + totalIssues + '/month) - may indicate planning gaps</li>';
                    } else if (totalIssues > 50) {
                        html += '<li>• 📈 High issue volume (' + totalIssues + '/month) - consider team capacity</li>';
                    }
                    
                    html += '<li>• 🎯 Focus on reducing cycle time and improving story estimation accuracy</li>';
                    html += '<li>• 📊 Implement regular retrospectives to identify process improvements</li>';
                    html += '</ul>';
                    html += '</div>';
                    
                    html += '</div>';
                    html += '</div>';
                } else if (metrics.jira && metrics.jira.error) {
                    html += '<div class="bg-red-100 border border-red-300 text-red-700 p-3 rounded mb-4">';
                    html += '📋 Jira Error: ' + metrics.jira.error;
                    html += '</div>';
                }
                
                // AWS Metrics
                if (metrics.aws && !metrics.aws.error) {
                    html += '<div class="bg-orange-50 border border-orange-200 rounded mb-4">';
                    html += '<div class="cursor-pointer p-4 hover:bg-orange-100" onclick="toggleSection(' + "'aws-section'" + ')">';
                    html += '<h4 class="text-lg font-semibold text-orange-800 flex items-center">';
                    html += '<span id="aws-section-icon" class="mr-2">▶️</span>';
                    html += '☁️ AWS Infrastructure';
                    html += '</h4></div>';
                    html += '<div id="aws-section" class="hidden p-4 pt-0">';
                    
                    // Cost Summary
                    html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">';
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">30-Day Total Cost</div>';
                    html += '<div class="text-xl font-bold text-green-600">$' + (metrics.aws.total_cost_last_30_days || 0) + '</div>';
                    html += '<div class="text-xs text-gray-500">' + (metrics.aws.currency || 'USD') + '</div>';
                    html += '</div>';
                    
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">Weekly Trend</div>';
                    html += '<div class="text-lg font-semibold ' + (metrics.aws.weekly_trend === 'increasing' ? 'text-red-600' : 'text-green-600') + '">';
                    html += metrics.aws.weekly_trend === 'increasing' ? '📈 Up' : '📉 Down';
                    html += '</div>';
                    html += '<div class="text-xs text-gray-500">Avg: $' + (metrics.aws.daily_average || 0) + '/day</div>';
                    html += '</div>';
                    
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">Resources</div>';
                    let resourceCount = 0;
                    if (metrics.aws.inventory) {
                        if (metrics.aws.inventory.ec2) resourceCount += metrics.aws.inventory.ec2.total_instances || 0;
                        if (metrics.aws.inventory.rds) resourceCount += metrics.aws.inventory.rds.total_databases || 0;
                        if (metrics.aws.inventory.s3) resourceCount += metrics.aws.inventory.s3.total_buckets || 0;
                        if (metrics.aws.inventory.lightsail) resourceCount += metrics.aws.inventory.lightsail.total_instances || 0;
                    }
                    html += '<div class="text-xl font-bold text-blue-600">' + resourceCount + '</div>';
                    html += '<div class="text-xs text-gray-500">Total resources</div>';
                    html += '</div>';
                    html += '</div>';
                    
                    // Top Services
                    if (metrics.aws.top_services && Object.keys(metrics.aws.top_services).length > 0) {
                        html += '<div class="bg-white p-3 rounded border mb-3">';
                        html += '<h5 class="font-medium text-gray-800 mb-2">Top Services by Cost</h5>';
                        html += '<div class="space-y-1">';
                        
                        for (const [service, cost] of Object.entries(metrics.aws.top_services)) {
                            if (cost > 0) {
                                html += '<div class="flex justify-between text-sm">';
                                html += '<span class="text-gray-700">' + service + '</span>';
                                html += '<span class="font-medium">$' + parseFloat(cost).toFixed(2) + '</span>';
                                html += '</div>';
                            }
                        }
                        html += '</div></div>';
                    }
                    
                    // AWS Recommendations
                    html += '<div class="bg-orange-100 p-3 rounded mt-3">';
                    html += '<h5 class="font-medium text-orange-800 mb-2">☁️ Infrastructure Optimization</h5>';
                    html += '<ul class="space-y-1 text-xs text-orange-700">';
                    
                    const monthlyCost = metrics.aws.total_cost_last_30_days || 0;
                    const trend = metrics.aws.weekly_trend;
                    
                    if (monthlyCost > 1000) {
                        html += '<li>• 💰 High monthly spend ($' + monthlyCost + ') - prioritize cost optimization</li>';
                    } else if (monthlyCost > 100) {
                        html += '<li>• 💡 Moderate spend ($' + monthlyCost + ') - monitor for efficiency gains</li>';
                    } else {
                        html += '<li>• ✅ Cost-effective infrastructure ($' + monthlyCost + '/month)</li>';
                    }
                    
                    if (trend === 'increasing') {
                        html += '<li>• 📈 Rising costs - implement immediate cost controls and monitoring</li>';
                    } else {
                        html += '<li>• 📉 Cost trend stable/decreasing - maintain optimization practices</li>';
                    }
                    
                    html += '<li>• 🔧 Review unutilized resources and consider Reserved Instance savings</li>';
                    html += '<li>• 📊 Set up billing alerts and automated cost anomaly detection</li>';
                    html += '<li>• 🏷️ Implement comprehensive resource tagging for cost allocation</li>';
                    html += '</ul>';
                    html += '</div>';
                    
                    html += '</div>';
                    html += '</div>';
                } else if (metrics.aws && metrics.aws.error) {
                    html += '<div class="bg-red-100 border border-red-300 text-red-700 p-3 rounded mb-4">';
                    html += '☁️ AWS Error: ' + metrics.aws.error;
                    html += '</div>';
                }
                
                // OpenAI Metrics
                if (metrics.openai && !metrics.openai.error) {
                    html += '<div class="bg-purple-50 border border-purple-200 rounded mb-4">';
                    html += '<div class="cursor-pointer p-4 hover:bg-purple-100" onclick="toggleSection(' + "'openai-section'" + ')">';
                    html += '<h4 class="text-lg font-semibold text-purple-800 flex items-center">';
                    html += '<span id="openai-section-icon" class="mr-2">▶️</span>';
                    html += '🤖 OpenAI API Usage';
                    html += '</h4></div>';
                    html += '<div id="openai-section" class="hidden p-4 pt-0">';
                    
                    // Usage Summary
                    html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">';
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">Tokens Used</div>';
                    html += '<div class="text-xl font-bold text-purple-600">' + (metrics.openai.usage_this_month?.tokens_used || 0).toLocaleString() + '</div>';
                    html += '</div>';
                    
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">Requests Made</div>';
                    html += '<div class="text-xl font-bold text-blue-600">' + (metrics.openai.usage_this_month?.requests_made || 0) + '</div>';
                    html += '</div>';
                    
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<div class="text-sm text-gray-600">Estimated Cost</div>';
                    html += '<div class="text-xl font-bold text-green-600">$' + (metrics.openai.usage_this_month?.estimated_cost || 0) + '</div>';
                    html += '</div>';
                    html += '</div>';
                    
                    // Models Used
                    if (metrics.openai.models_used && metrics.openai.models_used.length > 0) {
                        html += '<div class="bg-white p-3 rounded border mb-3">';
                        html += '<h5 class="font-medium text-gray-800 mb-2">Models Used</h5>';
                        html += '<div class="flex flex-wrap gap-2">';
                        metrics.openai.models_used.forEach(model => {
                            html += '<span class="px-2 py-1 bg-purple-100 text-purple-800 text-sm rounded">' + model + '</span>';
                        });
                        html += '</div></div>';
                    }
                    
                    // Dashboard Links
                    html += '<div class="bg-white p-3 rounded border mb-3">';
                    html += '<h5 class="font-medium text-gray-800 mb-2">Dashboard Links</h5>';
                    html += '<div class="space-y-2">';
                    html += '<div><a href="' + metrics.openai.dashboard_url + '" target="_blank" class="text-blue-600 hover:underline text-sm">📊 OpenAI Usage Dashboard →</a></div>';
                    html += '<div><a href="' + metrics.openai.billing_url + '" target="_blank" class="text-green-600 hover:underline text-sm">💰 Check Account Balance →</a></div>';
                    html += '</div></div>';
                    
                    // Note about account balance
                    if (metrics.openai.note) {
                        html += '<div class="bg-orange-100 p-3 rounded">';
                        html += '<div class="text-sm text-orange-700">ℹ️ ' + metrics.openai.note + '</div>';
                        html += '</div>';
                    }
                    
                    html += '</div>';
                    html += '</div>';
                } else if (metrics.openai && metrics.openai.error) {
                    html += '<div class="bg-red-100 border border-red-300 text-red-700 p-3 rounded mb-4">';
                    html += '🤖 OpenAI Error: ' + metrics.openai.error;
                    html += '</div>';
                }
                
                // Railway would go here when implemented
                
                // CTO Recommendations Section - Comprehensive for all services
                html += '<div class="bg-yellow-50 border border-yellow-200 p-4 rounded">';
                html += '<h4 class="text-lg font-semibold text-yellow-800 mb-3">💡 CTO Strategic Recommendations</h4>';
                html += '<div class="space-y-3 text-sm text-yellow-700">';
                
                // GitHub Recommendations
                if (metrics.github) {
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<h5 class="font-medium text-purple-800 mb-2">🚀 GitHub Development Insights</h5>';
                    html += '<ul class="space-y-1 text-xs">';
                    
                    let totalCommits = 0;
                    let totalStars = 0;
                    let totalIssues = 0;
                    let activeRepos = 0;
                    
                    if (Array.isArray(metrics.github)) {
                        metrics.github.forEach(repo => {
                            if (!repo.error) {
                                totalCommits += repo.commits_last_30_days || 0;
                                totalStars += repo.stars || 0;
                                totalIssues += repo.open_issues || 0;
                                if (repo.commits_last_30_days > 0) activeRepos++;
                            }
                        });
                    }
                    
                    if (totalCommits < 50) {
                        html += '<li>• 🔍 Low commit activity (' + totalCommits + '/month) - consider increasing development velocity</li>';
                    } else {
                        html += '<li>• ✅ Good development activity (' + totalCommits + ' commits/month)</li>';
                    }
                    
                    if (totalIssues > 20) {
                        html += '<li>• ⚠️ High open issue count (' + totalIssues + ') - prioritize technical debt reduction</li>';
                    }
                    
                    if (activeRepos === 0) {
                        html += '<li>• 🚨 No active repositories - investigate development process</li>';
                    } else {
                        html += '<li>• 📈 ' + activeRepos + ' active repositories - maintain code quality standards</li>';
                    }
                    
                    html += '<li>• 📚 Consider implementing automated testing and CI/CD pipelines</li>';
                    html += '</ul></div>';
                }
                
                // Jira Recommendations
                if (metrics.jira && !metrics.jira.error) {
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<h5 class="font-medium text-blue-800 mb-2">📋 Project Management Insights</h5>';
                    html += '<ul class="space-y-1 text-xs">';
                    
                    const resolutionRate = metrics.jira.resolution_rate || 0;
                    const totalIssues = metrics.jira.total_issues_last_30_days || 0;
                    
                    if (resolutionRate < 70) {
                        html += '<li>• 🔴 Low resolution rate (' + resolutionRate + '%) - review sprint planning and capacity</li>';
                    } else if (resolutionRate < 85) {
                        html += '<li>• 🟡 Moderate resolution rate (' + resolutionRate + '%) - optimize workflow efficiency</li>';
                    } else {
                        html += '<li>• 🟢 Excellent resolution rate (' + resolutionRate + '%) - maintain current velocity</li>';
                    }
                    
                    if (totalIssues < 10) {
                        html += '<li>• 📉 Low issue creation (' + totalIssues + '/month) - may indicate planning gaps</li>';
                    } else if (totalIssues > 50) {
                        html += '<li>• 📈 High issue volume (' + totalIssues + '/month) - consider team capacity</li>';
                    }
                    
                    html += '<li>• 🎯 Focus on reducing cycle time and improving story estimation accuracy</li>';
                    html += '<li>• 📊 Implement regular retrospectives to identify process improvements</li>';
                    html += '</ul></div>';
                }
                
                // AWS Recommendations
                if (metrics.aws && !metrics.aws.error) {
                    html += '<div class="bg-white p-3 rounded border">';
                    html += '<h5 class="font-medium text-orange-800 mb-2">☁️ Infrastructure Optimization</h5>';
                    html += '<ul class="space-y-1 text-xs">';
                    
                    const monthlyCost = metrics.aws.total_cost_last_30_days || 0;
                    const trend = metrics.aws.weekly_trend;
                    
                    if (monthlyCost > 1000) {
                        html += '<li>• 💰 High monthly spend ($' + monthlyCost + ') - prioritize cost optimization</li>';
                    } else if (monthlyCost > 100) {
                        html += '<li>• 💡 Moderate spend ($' + monthlyCost + ') - monitor for efficiency gains</li>';
                    } else {
                        html += '<li>• ✅ Cost-effective infrastructure ($' + monthlyCost + '/month)</li>';
                    }
                    
                    if (trend === 'increasing') {
                        html += '<li>• 📈 Rising costs - implement immediate cost controls and monitoring</li>';
                    } else {
                        html += '<li>• 📉 Cost trend stable/decreasing - maintain optimization practices</li>';
                    }
                    
                    html += '<li>• 🔧 Review unutilized resources and consider Reserved Instance savings</li>';
                    html += '<li>• 📊 Set up billing alerts and automated cost anomaly detection</li>';
                    html += '<li>• 🏷️ Implement comprehensive resource tagging for cost allocation</li>';
                    html += '</ul></div>';
                }
                
                // Overall Strategic Recommendations
                html += '<div class="bg-gradient-to-r from-blue-50 to-purple-50 p-3 rounded border border-blue-200">';
                html += '<h5 class="font-medium text-gray-800 mb-2">🎯 Strategic CTO Priorities</h5>';
                html += '<ul class="space-y-1 text-xs text-gray-700">';
                html += '<li>• 📈 <strong>Velocity:</strong> Align development speed with business objectives</li>';
                html += '<li>• 💰 <strong>Cost Efficiency:</strong> Optimize infrastructure spend without compromising performance</li>';
                html += '<li>• 🔄 <strong>Process:</strong> Streamline workflows to reduce cycle time and improve quality</li>';
                html += '<li>• 📊 <strong>Metrics:</strong> Establish KPIs that tie technical performance to business outcomes</li>';
                html += '<li>• 🛡️ <strong>Risk Management:</strong> Balance technical debt with feature delivery</li>';
                html += '</ul></div>';
                
                html += '</div>';
                html += '</div>';
                
                html += '</div>';
                container.innerHTML = html;
            }
            
            function displayRealMetrics(metrics, container) {
                let html = '<div class="bg-gray-50 rounded-lg p-4">';
                html += '<h3 class="text-xl font-bold text-gray-800 mb-4">📊 Real AWS Metrics - ' + new Date().toLocaleString() + '</h3>';
                
                // Cost Summary
                html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">';
                html += '<div class="bg-white p-4 rounded border">';
                html += '<h5 class="font-medium text-gray-800 mb-2">💰 30-Day Total Cost</h5>';
                html += '<div class="text-2xl font-bold text-green-600">$' + (metrics.total_cost_last_30_days || 0) + '</div>';
                html += '<div class="text-sm text-gray-600">' + (metrics.currency || 'USD') + '</div>';
                html += '</div>';
                
                html += '<div class="bg-white p-4 rounded border">';
                html += '<h5 class="font-medium text-gray-800 mb-2">📈 Weekly Trend</h5>';
                html += '<div class="text-lg font-semibold ' + (metrics.weekly_trend === 'increasing' ? 'text-red-600' : 'text-green-600') + '">';
                html += metrics.weekly_trend === 'increasing' ? '📈 Increasing' : '📉 Decreasing';
                html += '</div>';
                html += '<div class="text-sm text-gray-600">Daily Average: $' + (metrics.daily_average || 0) + '</div>';
                html += '</div>';
                
                html += '<div class="bg-white p-4 rounded border">';
                html += '<h5 class="font-medium text-gray-800 mb-2">🔧 Resource Count</h5>';
                let resourceCount = 0;
                if (metrics.inventory) {
                    if (metrics.inventory.ec2) resourceCount += metrics.inventory.ec2.total_instances || 0;
                    if (metrics.inventory.rds) resourceCount += metrics.inventory.rds.total_databases || 0;
                    if (metrics.inventory.s3) resourceCount += metrics.inventory.s3.total_buckets || 0;
                    if (metrics.inventory.lightsail) resourceCount += metrics.inventory.lightsail.total_instances || 0;
                }
                html += '<div class="text-lg font-semibold text-blue-600">' + resourceCount + ' Resources</div>';
                html += '<div class="text-sm text-gray-600">Across all services</div>';
                html += '</div>';
                html += '</div>';
                
                // Service Breakdown
                if (metrics.top_services && Object.keys(metrics.top_services).length > 0) {
                    html += '<div class="bg-white p-4 rounded border mb-4">';
                    html += '<h5 class="font-medium text-gray-800 mb-3">🏷️ Top Services by Cost</h5>';
                    html += '<div class="space-y-2">';
                    
                    for (const [service, cost] of Object.entries(metrics.top_services)) {
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
                if (metrics.recommendations) {
                    html += '<div class="bg-yellow-50 border border-yellow-200 p-4 rounded">';
                    html += '<h5 class="font-medium text-yellow-800 mb-3">💡 CTO Optimization Recommendations</h5>';
                    html += '<div class="space-y-1 text-sm text-yellow-700">';
                    
                    metrics.recommendations.slice(0, 10).forEach(rec => {
                        html += '<div>' + rec + '</div>';
                    });
                    html += '</div></div>';
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
            
            function toggleSection(sectionId) {
                const section = document.getElementById(sectionId);
                const icon = document.getElementById(sectionId + '-icon');
                
                if (section && icon) {
                    if (section.classList.contains('hidden')) {
                        section.classList.remove('hidden');
                        icon.textContent = '🔽️';
                    } else {
                        section.classList.add('hidden');
                        icon.textContent = '▶️';
                    }
                }
            }
            
            function showTab(tabId) {
                // Hide all tab contents
                const tabContents = document.querySelectorAll('.tab-content');
                tabContents.forEach(content => {
                    content.classList.add('hidden');
                });
                
                // Remove active class from all tab buttons
                const tabButtons = document.querySelectorAll('.tab-button');
                tabButtons.forEach(button => {
                    button.classList.remove('active-tab');
                });
                
                // Show selected tab content
                const selectedContent = document.getElementById(tabId + '-content');
                if (selectedContent) {
                    selectedContent.classList.remove('hidden');
                }
                
                // Add active class to selected tab button
                const selectedButton = document.getElementById('tab-' + tabId);
                if (selectedButton) {
                    selectedButton.classList.add('active-tab');
                }
            }
            
            // Chatbot Functions
            function toggleChatbot() {
                const modal = document.getElementById('chatbot-modal');
                modal.classList.toggle('hidden');
                
                // Load conversation history when opening
                if (!modal.classList.contains('hidden')) {
                    loadChatbotHistory();
                }
            }

            async function loadChatbotHistory() {
                const messages = document.getElementById('chatbot-messages');
                
                try {
                    const response = await fetch('/api/chatbot/history?user_id=dashboard_user&limit=20');
                    const data = await response.json();
                    
                    if (data.history && data.history.length > 0) {
                        // Clear existing messages except welcome message
                        messages.innerHTML = '';
                        
                        // Add conversation history
                        data.history.forEach(msg => {
                            const messageDiv = document.createElement('div');
                            if (msg.user_id === 'dashboard_user') {
                                messageDiv.className = 'flex justify-end';
                                messageDiv.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-blue-500 text-white"><div class="whitespace-pre-wrap">' + msg.question + '</div></div>';
                            } else {
                                messageDiv.className = 'flex justify-start';
                                messageDiv.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-gray-100 text-gray-900"><div class="whitespace-pre-wrap">' + msg.response + '</div></div>';
                            }
                            messages.appendChild(messageDiv);
                        });
                    }
                    
                    // Scroll to bottom
                    messages.scrollTop = messages.scrollHeight;
                    
                } catch (error) {
                    console.error('Error loading chat history:', error);
                }
            }

            async function clearChatbotHistory() {
                if (confirm('Are you sure you want to clear the conversation history?')) {
                    try {
                        const response = await fetch('/api/chatbot/clear', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                user_id: 'dashboard_user'
                            })
                        });
                        
                        if (response.ok) {
                            // Clear messages and show welcome message
                            const messages = document.getElementById('chatbot-messages');
                            messages.innerHTML = '<div class="text-center text-gray-500 py-8"><div class="text-4xl mb-4">🤖</div><h3 class="text-lg font-medium mb-2">Welcome to CTO Dashboard Assistant!</h3><p class="text-sm">I can help you with questions about:</p><ul class="text-sm mt-2 space-y-1"><li>• Your assignments and projects</li><li>• AWS costs and resource usage</li><li>• GitHub metrics and activity</li><li>• Jira project status</li><li>• Team information and tech stacks</li><li>• Service health and configuration</li></ul><p class="text-sm mt-4 text-gray-400">Try asking: "What is IdepTech status?" or "Show me IdepTech AWS costs"</p></div>';
                        }
                    } catch (error) {
                        console.error('Error clearing chat history:', error);
                    }
                }
            }

            function handleChatbotKeyPress(event) {
                if (event.key === 'Enter') {
                    sendChatbotMessage();
                }
            }

            function setChatbotInput(text) {
                const input = document.getElementById('chatbot-input');
                input.value = text;
                input.focus();
            }

            async function sendChatbotMessage() {
                const input = document.getElementById('chatbot-input');
                const messages = document.getElementById('chatbot-messages');
                const question = input.value.trim();
                
                if (!question) return;
                
                // Add user message
                const userMessage = document.createElement('div');
                userMessage.className = 'flex justify-end';
                userMessage.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-blue-500 text-white"><div class="whitespace-pre-wrap">' + question + '</div></div>';
                messages.appendChild(userMessage);
                
                // Clear input
                input.value = '';
                
                // Add loading message
                const loadingMessage = document.createElement('div');
                loadingMessage.className = 'flex justify-start';
                loadingMessage.innerHTML = '<div class="bg-gray-100 rounded-lg px-4 py-2"><div class="flex items-center space-x-2"><div class="flex space-x-1"><div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div><div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div><div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div></div><span class="text-sm text-gray-500">Thinking...</span></div></div>';
                messages.appendChild(loadingMessage);
                
                // Scroll to bottom
                messages.scrollTop = messages.scrollHeight;
                
                try {
                    const response = await fetch('/api/chatbot/ask', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            question: question,
                            user_id: 'dashboard_user'
                        })
                    });
                    
                    const data = await response.json();
                    
                    // Remove loading message
                    loadingMessage.remove();
                    
                    // Add bot response
                    const botMessage = document.createElement('div');
                    botMessage.className = 'flex justify-start';
                    botMessage.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-gray-100 text-gray-900"><div class="whitespace-pre-wrap">' + data.response + '</div></div>';
                    messages.appendChild(botMessage);
                    
                } catch (error) {
                    // Remove loading message
                    loadingMessage.remove();
                    
                    // Add error message
                    const errorMessage = document.createElement('div');
                    errorMessage.className = 'flex justify-start';
                    errorMessage.innerHTML = '<div class="max-w-[80%] rounded-lg px-4 py-2 bg-red-100 text-red-800"><div class="whitespace-pre-wrap">Sorry, I encountered an error. Please try again.</div></div>';
                    messages.appendChild(errorMessage);
                }
                
                // Scroll to bottom
                messages.scrollTop = messages.scrollHeight;
            }

            // Load dashboard when page loads
            document.addEventListener('DOMContentLoaded', loadDashboard);
        </script>
    </body>
    </html>
    '''

@app.route("/health")

@app.route("/api/feature-flags")
def get_feature_flags():
    """Get current feature flags status"""
    return jsonify({
        "feature_flags": FEATURE_FLAGS,
        "status": "read_only",
        "note": "Feature flags are controlled via environment variables",
        "environment_variables": {
            "ENABLE_MULTI_TENANCY": os.getenv("ENABLE_MULTI_TENANCY", "false"),
            "ENABLE_WORKSTREAM_MGMT": os.getenv("ENABLE_WORKSTREAM_MGMT", "false"),
            "ENABLE_SERVICE_CONFIG_UI": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false"),
            "ENABLE_BILLING": os.getenv("ENABLE_BILLING", "false"),
            "ENABLE_DATABASE": os.getenv("ENABLE_DATABASE", "false")
        }
    })

@app.route("/api/services/status")
def get_services_status():
    """Get status of all services"""
    return jsonify({
        "service_manager": {
            "enabled_services": list(service_manager.services.keys()),
            "total_services": len(service_manager.services)
        },
        "feature_flags": FEATURE_FLAGS,
        "status": "read_only"
    })

@app.route("/api/workstreams", methods=["GET", "POST"])
def workstreams_endpoint():
    """Workstream management endpoint (disabled by default)"""
    if request.method == "GET":
        workstream_service = service_manager.get_service("workstream")
        if not workstream_service:
            return jsonify({"error": "Workstream management disabled", "enabled": False})
        
        return jsonify({
            "workstreams": workstream_service.get_workstreams(),
            "enabled": True
        })
    
    elif request.method == "POST":
        workstream_service = service_manager.get_service("workstream")
        if not workstream_service:
            return jsonify({"error": "Workstream management disabled", "enabled": False})
        
        data = request.get_json()
        result = workstream_service.create_workstream(
            data.get("name", ""),
            data.get("config", {})
        )
        return jsonify(result)

@app.route("/api/service-configs", methods=["GET", "POST"])
def service_configs_endpoint():
    """Service configuration endpoint (disabled by default)"""
    if request.method == "GET":
        config_service = service_manager.get_service("config")
        if not config_service:
            return jsonify({"error": "Service configuration UI disabled", "enabled": False})
        
        workstream_id = request.args.get("workstream_id")
        return jsonify({
            "configs": config_service.get_service_configs(workstream_id),
            "enabled": True
        })
    
    elif request.method == "POST":
        config_service = service_manager.get_service("config")
        if not config_service:
            return jsonify({"error": "Service configuration UI disabled", "enabled": False})
        
        data = request.get_json()
        result = config_service.add_service_config(
            data.get("workstream_id", ""),
            data.get("service_type", ""),
            data.get("config", {})
        )
        return jsonify(result)

def health_check():

    """Simple health check endpoint"""
    try:
        return jsonify({
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "services": {
                "aws": "available",
                "github": "available", 
                "jira": "available",
                "openai": "available"
            }
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

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

@app.route("/api/aws-metrics")
def aws_metrics_endpoint():
    """Get real AWS metrics using embedded functions - no network dependency"""
    try:
        # Get cost metrics directly (function call, not network request)
        cost_data = aws_metrics.get_real_cost_metrics()
        
        # Get resource inventory directly
        inventory = aws_metrics.get_resource_inventory()
        
        # Get recommendations directly
        recommendations = aws_metrics.get_optimization_recommendations()
        
        # Combine all data
        response = {
            "timestamp": datetime.now().isoformat(),
            "data_source": "Direct AWS API calls (embedded)",
            **cost_data,  # Spread cost data into response
            "inventory": inventory,
            "recommendations": recommendations
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"AWS metrics error: {str(e)}",
            "note": "Check AWS credentials and permissions",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/github-metrics/<assignment_id>")
def github_metrics_endpoint(assignment_id):
    """Get real GitHub metrics using embedded functions - no network dependency"""
    try:
        # Get assignment configuration to extract GitHub settings
        assignments_dir = 'backend/assignments'
        assignment_file = os.path.join(assignments_dir, f"{assignment_id}.json")
        
        if not os.path.exists(assignment_file):
            return jsonify({"error": f"Assignment {assignment_id} not found"}), 404
        
        with open(assignment_file, 'r') as f:
            assignment_config = json.load(f)
        
        github_config = assignment_config.get("metrics_config", {}).get("github", {})
        
        if not github_config.get("enabled", False):
            return jsonify({"error": "GitHub metrics not enabled for this assignment"}), 400
        
        org = github_config.get("org", "")
        repos = github_config.get("repos", [])
        
        # Get GitHub metrics directly
        repo_metrics = github_metrics.get_repo_metrics(org, repos)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "data_source": "Direct GitHub API calls (embedded)",
            "assignment_id": assignment_id,
            "org": org,
            "repos": repo_metrics
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"GitHub metrics error: {str(e)}",
            "note": "Check GitHub token and repository access",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/jira-metrics/<assignment_id>")
def jira_metrics_endpoint(assignment_id):
    """Get real Jira metrics using embedded functions - no network dependency"""
    try:
        # Get assignment configuration to extract Jira settings
        assignments_dir = 'backend/assignments'
        assignment_file = os.path.join(assignments_dir, f"{assignment_id}.json")
        
        if not os.path.exists(assignment_file):
            return jsonify({"error": f"Assignment {assignment_id} not found"}), 404
        
        with open(assignment_file, 'r') as f:
            assignment_config = json.load(f)
        
        jira_config = assignment_config.get("metrics_config", {}).get("jira", {})
        
        if not jira_config.get("enabled", False):
            return jsonify({"error": "Jira metrics not enabled for this assignment"}), 400
        
        project_key = jira_config.get("project_key", "")
        
        # Get Jira metrics directly
        project_metrics = jira_metrics.get_project_metrics(project_key)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "data_source": "Direct Jira API calls (embedded)",
            "assignment_id": assignment_id,
            **project_metrics  # Spread project data into response
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"Jira metrics error: {str(e)}",
            "note": "Check Jira credentials and project access",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/all-metrics/<assignment_id>")
def all_metrics_endpoint(assignment_id):
    """Get all metrics for an assignment using embedded functions - no network dependency"""
    try:
        # Get assignment configuration
        assignments_dir = 'backend/assignments'
        assignment_file = os.path.join(assignments_dir, f"{assignment_id}.json")
        
        if not os.path.exists(assignment_file):
            return jsonify({"error": f"Assignment {assignment_id} not found"}), 404
        
        with open(assignment_file, 'r') as f:
            assignment_config = json.load(f)
        
        metrics_config = assignment_config.get("metrics_config", {})
        all_metrics = {
            "timestamp": datetime.now().isoformat(),
            "data_source": "Direct API calls (embedded)",
            "assignment_id": assignment_id,
            "assignment_name": assignment_config.get("name", "Unknown")
        }
        
        # Get GitHub metrics if enabled
        github_config = metrics_config.get("github", {})
        if github_config.get("enabled", False):
            org = github_config.get("org", "")
            repos = github_config.get("repos", [])
            all_metrics["github"] = github_metrics.get_repo_metrics(org, repos)
        
        # Get Jira metrics if enabled
        jira_config = metrics_config.get("jira", {})
        if jira_config.get("enabled", False):
            project_key = jira_config.get("project_key", "")
            all_metrics["jira"] = jira_metrics.get_project_metrics(project_key)
        
        # Get AWS metrics if enabled
        aws_config = metrics_config.get("aws", {})
        if aws_config.get("enabled", False):
            cost_data = aws_metrics.get_real_cost_metrics()
            inventory = aws_metrics.get_resource_inventory()
            recommendations = aws_metrics.get_optimization_recommendations()
            
            all_metrics["aws"] = {
                **cost_data,
                "inventory": inventory,
                "recommendations": recommendations
            }
        
        return jsonify(all_metrics)
        
    except Exception as e:
        return jsonify({
            "error": f"All metrics error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

class OpenAIMetrics:
    """OpenAI API usage and cost tracking"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1")
        
    def get_usage_metrics(self, config: dict) -> dict:
        """Get OpenAI usage metrics and dashboard link"""
        if not self.api_key:
            return {"error": "OpenAI API key not configured"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Get current date range for this month
            now = datetime.now()
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
            
            # Get usage data from OpenAI API
            usage_url = f"{self.base_url}/usage?date={start_date}"
            
            response = requests.get(usage_url, headers=headers)
            
            if response.status_code == 200:
                usage_data = response.json()
                
                # Calculate totals from the usage data
                total_tokens = 0
                total_requests = 0
                total_cost = 0.0
                models_used = set()
                
                for item in usage_data.get('data', []):
                    total_tokens += item.get('n_context_tokens_total', 0) + item.get('n_generated_tokens_total', 0)
                    total_requests += 1
                    total_cost += item.get('cost', 0.0)
                    if item.get('model'):
                        models_used.add(item.get('model'))
                
                dashboard_url = config.get("api_dashboard_url", "https://platform.openai.com/usage")
                
                return {
                    "dashboard_url": dashboard_url,
                    "billing_url": "https://platform.openai.com/settings/organization/billing",
                    "api_key_configured": True,
                    "usage_this_month": {
                        "tokens_used": total_tokens,
                        "requests_made": total_requests,
                        "estimated_cost": round(total_cost, 2)
                    },
                    "models_used": list(models_used) if models_used else ["No data available"],
                    "last_updated": datetime.now().isoformat(),
                    "status": "active",
                    "period": f"{start_date} to {end_date}",
                    "raw_data_available": len(usage_data.get('data', [])) > 0,
                    "note": "Account balance not available via API - check billing dashboard"
                }
            else:
                return {
                    "error": f"OpenAI API returned {response.status_code}: {response.text}",
                    "dashboard_url": config.get("api_dashboard_url", "https://platform.openai.com/usage"),
                    "billing_url": "https://platform.openai.com/settings/organization/billing",
                    "api_key_configured": True
                }
            
        except Exception as e:
            return {
                "error": f"OpenAI metrics error: {str(e)}",
                "dashboard_url": config.get("api_dashboard_url", "https://platform.openai.com/usage"),
                "billing_url": "https://platform.openai.com/settings/organization/billing",
                "api_key_configured": bool(self.api_key)
            }

# Initialize OpenAI metrics
openai_metrics = OpenAIMetrics()

@app.route("/api/assignments/<assignment_id>/metrics")
def assignment_metrics(assignment_id):
    """Get metrics for a specific assignment including OpenAI"""
    try:
        # Load assignment configuration
        assignment_file = f"backend/assignments/{assignment_id}.json"
        if not os.path.exists(assignment_file):
            return jsonify({"error": "Assignment not found"}), 404
        
        with open(assignment_file, 'r') as f:
            assignment_config = json.load(f)
        
        metrics_config = assignment_config.get("metrics_config", {})
        all_metrics = {
            "assignment_id": assignment_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get GitHub metrics if enabled
        github_config = metrics_config.get("github", {})
        if github_config.get("enabled", False):
            org = github_config.get("org", "")
            repos = github_config.get("repos", [])
            all_metrics["github"] = github_metrics.get_repo_metrics(org, repos)
        
        # Get Jira metrics if enabled
        jira_config = metrics_config.get("jira", {})
        if jira_config.get("enabled", False):
            project_key = jira_config.get("project_key", "")
            all_metrics["jira"] = jira_metrics.get_project_metrics(project_key)
        
        # Get AWS metrics if enabled
        aws_config = metrics_config.get("aws", {})
        if aws_config.get("enabled", False):
            cost_data = aws_metrics.get_real_cost_metrics()
            inventory = aws_metrics.get_resource_inventory()
            recommendations = aws_metrics.get_optimization_recommendations()
            
            all_metrics["aws"] = {
                **cost_data,
                "inventory": inventory,
                "recommendations": recommendations
            }
        
        # Get OpenAI metrics if enabled
        openai_config = metrics_config.get("openai", {})
        if openai_config.get("enabled", False):
            all_metrics["openai"] = openai_metrics.get_usage_metrics(openai_config)
        
        return jsonify(all_metrics)
        
    except Exception as e:
        return jsonify({
            "error": f"Assignment metrics error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/chatbot/ask", methods=["POST"])
def chatbot_ask():
    """Full AI chatbot endpoint with LangChain capabilities"""
    try:
        data = request.get_json()
        question = data.get("question", "")
        user_id = data.get("user_id", "default")
        
        # Import chatbot service for full AI capabilities
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
        from chatbot_service import chatbot_service
        import asyncio
        
        # Process the question with full AI capabilities
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(chatbot_service.process_question(question, user_id))
        finally:
            loop.close()
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": f"Chatbot error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/chatbot/history")
def chatbot_history():
    """Get chatbot conversation history"""
    try:
        user_id = request.args.get("user_id", "default")
        limit = int(request.args.get("limit", 10))
        
        # Import chatbot service for full history capabilities
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
        from chatbot_service import chatbot_service
        
        # Get conversation history
        history = chatbot_service.get_conversation_history(user_id, limit)
        return jsonify({"history": history})
        
    except Exception as e:
        return jsonify({
            "error": f"Chatbot history error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/chatbot/clear", methods=["POST"])
def chatbot_clear():
    """Clear chatbot conversation history"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", "default")
        
        # Import chatbot service for full capabilities
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
        from chatbot_service import chatbot_service
        
        # Clear conversation history
        chatbot_service.clear_conversation_history(user_id)
        return jsonify({"message": "Conversation history cleared"})
        
    except Exception as e:
        return jsonify({
            "error": f"Error clearing history: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/static/<path:filename>")
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

if __name__ == "__main__":
    # Use PORT from environment (for Render deployment) or default to 3001
    port = int(os.getenv("PORT", 3001))
    
    print("🚀 Starting Integrated CTO Dashboard...")
    print(f"📍 Access at: http://localhost:{port}")
    print("💡 This version has AWS functions embedded - no client-server dependency!")
    print("🔧 All AWS calls are direct function calls within the same process")
    
    # Disable debug mode in production
    debug_mode = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
