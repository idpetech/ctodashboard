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
from flask import Flask, jsonify, render_template_string
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join('backend', '.env'))

app = Flask(__name__)

class EmbeddedAWSMetrics:
    """AWS metrics embedded directly in the Flask app"""
    
    def __init__(self):
        # Use existing AWS credentials from environment or boto3 default
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
    def _get_aws_client(self, service_name: str):
        """Get AWS client for the specified service"""
        try:
            return boto3.client(service_name, region_name=self.region)
        except Exception as e:
            print(f"Error creating {service_name} client: {e}")
            return None
    
    def get_real_cost_metrics(self) -> dict:
        """Get real AWS cost metrics"""
        try:
            ce_client = self._get_aws_client('ce')
            if not ce_client:
                return {"error": "Could not initialize Cost Explorer client"}
            
            # Get cost for last 30 days
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Get daily costs for trend analysis
            daily_response = ce_client.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='DAILY',
                Metrics=['BlendedCost']
            )
            
            # Get costs by service
            service_response = ce_client.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            # Parse daily costs
            daily_costs = []
            for result in daily_response.get('ResultsByTime', []):
                date = result['TimePeriod']['Start']
                cost = float(result['Total']['BlendedCost']['Amount'])
                daily_costs.append({"date": date, "cost": cost})
            
            # Parse service costs
            service_costs = {}
            total_cost = 0
            for result in service_response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    service_name = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    service_costs[service_name] = cost
                    total_cost += cost
            
            # Calculate trends
            recent_7_days = sum(d['cost'] for d in daily_costs[-7:] if d['cost'] > 0)
            previous_7_days = sum(d['cost'] for d in daily_costs[-14:-7] if d['cost'] > 0)
            trend = "increasing" if recent_7_days > previous_7_days else "decreasing"
            
            return {
                "total_cost_last_30_days": round(total_cost, 2),
                "daily_average": round(total_cost / 30, 2),
                "currency": "USD",
                "period": f"{start_date} to {end_date}",
                "weekly_trend": trend,
                "recent_7_days_cost": round(recent_7_days, 2),
                "previous_7_days_cost": round(previous_7_days, 2),
                "top_services": dict(sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:5]),
                "all_services": service_costs,
                "daily_costs": daily_costs[-7:]  # Last 7 days for charting
            }
            
        except Exception as e:
            return {"error": f"AWS Cost Explorer error: {str(e)}"}
    
    def get_resource_inventory(self) -> dict:
        """Get AWS resource inventory"""
        inventory = {}
        
        # EC2 Instances
        try:
            ec2_client = self._get_aws_client('ec2')
            if ec2_client:
                response = ec2_client.describe_instances()
                instances = []
                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        instances.append({
                            "id": instance.get('InstanceId', 'unknown'),
                            "type": instance.get('InstanceType', 'unknown'),
                            "state": instance.get('State', {}).get('Name', 'unknown')
                        })
                inventory["ec2"] = {
                    "total_instances": len(instances),
                    "running": len([i for i in instances if i['state'] == 'running']),
                    "stopped": len([i for i in instances if i['state'] == 'stopped']),
                    "instances": instances
                }
        except Exception as e:
            inventory["ec2"] = {"error": str(e)}
        
        # S3 Buckets
        try:
            s3_client = self._get_aws_client('s3')
            if s3_client:
                response = s3_client.list_buckets()
                buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
                inventory["s3"] = {
                    "total_buckets": len(buckets),
                    "buckets": buckets
                }
        except Exception as e:
            inventory["s3"] = {"error": str(e)}
        
        # RDS Instances
        try:
            rds_client = self._get_aws_client('rds')
            if rds_client:
                response = rds_client.describe_db_instances()
                databases = []
                for db in response.get('DBInstances', []):
                    databases.append({
                        "id": db.get('DBInstanceIdentifier', 'unknown'),
                        "engine": db.get('Engine', 'unknown'),
                        "status": db.get('DBInstanceStatus', 'unknown')
                    })
                inventory["rds"] = {
                    "total_databases": len(databases),
                    "databases": databases
                }
        except Exception as e:
            inventory["rds"] = {"error": str(e)}
        
        # Lightsail Instances
        try:
            lightsail_client = self._get_aws_client('lightsail')
            if lightsail_client:
                response = lightsail_client.get_instances()
                instances = response.get('instances', [])
                inventory["lightsail"] = {
                    "total_instances": len(instances),
                    "running": len([i for i in instances if i.get('state', {}).get('name') == 'running']),
                    "stopped": len([i for i in instances if i.get('state', {}).get('name') == 'stopped'])
                }
        except Exception as e:
            inventory["lightsail"] = {"error": str(e)}
        
        return inventory
    
    def get_optimization_recommendations(self) -> list:
        """Get CTO-level optimization recommendations"""
        return [
            "🎯 CTO COST OPTIMIZATION PRIORITIES:",
            "",
            "💰 IMMEDIATE ACTIONS (0-7 days):",
            "• Review all stopped EC2/Lightsail instances - terminate if unused",
            "• Check for unattached EBS volumes and unused Elastic IPs",
            "• Verify Route 53 hosted zones are all needed ($0.50/month each)",
            "",
            "📊 SHORT TERM (1-4 weeks):", 
            "• Analyze CloudWatch metrics for underutilized instances",
            "• Consider Reserved Instances for steady workloads (up to 75% savings)",
            "• Implement S3 lifecycle policies for infrequent access storage",
            "",
            "🔄 ONGOING MONITORING:",
            "• Set up AWS Budget alerts for cost anomalies",
            "• Monthly review of AWS Cost Explorer recommendations",
            "• Quarterly rightsizing analysis for all compute resources"
        ]

class EmbeddedGitHubMetrics:
    """GitHub metrics embedded directly in the Flask app"""
    
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
    def get_repo_metrics(self, org: str, repos: list) -> list:
        """Get GitHub repository metrics for multiple repos"""
        if not self.token:
            return [{"error": "GitHub token not configured"}]
        
        repo_metrics = []
        
        for repo in repos:
            try:
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                # Get repository info
                repo_url = f"{self.base_url}/repos/{org}/{repo}"
                repo_response = requests.get(repo_url, headers=headers, timeout=10)
                
                if repo_response.status_code != 200:
                    repo_metrics.append({
                        "repo_name": repo,
                        "error": f"GitHub API returned {repo_response.status_code}"
                    })
                    continue
                
                repo_data = repo_response.json()
                
                # Get recent commits (last 30 days)
                since_date = (datetime.now() - timedelta(days=30)).isoformat()
                commits_url = f"{repo_url}/commits?since={since_date}"
                commits_response = requests.get(commits_url, headers=headers, timeout=10)
                commits = commits_response.json() if commits_response.status_code == 200 else []
                
                # Get pull requests
                prs_url = f"{repo_url}/pulls?state=all&per_page=50"
                prs_response = requests.get(prs_url, headers=headers, timeout=10)
                prs = prs_response.json() if prs_response.status_code == 200 else []
                
                repo_metrics.append({
                    "repo_name": repo,
                    "commits_last_30_days": len(commits),
                    "total_prs": len(prs),
                    "open_issues": repo_data.get("open_issues_count", 0),
                    "stars": repo_data.get("stargazers_count", 0),
                    "language": repo_data.get("language", "Unknown"),
                    "last_updated": repo_data.get("updated_at", "")
                })
                
            except Exception as e:
                repo_metrics.append({
                    "repo_name": repo,
                    "error": f"GitHub API error: {str(e)}"
                })
        
        return repo_metrics

class EmbeddedJiraMetrics:
    """Jira metrics embedded directly in the Flask app"""
    
    def __init__(self):
        self.base_url = os.getenv("JIRA_URL")
        self.email = os.getenv("JIRA_EMAIL")
        self.token = os.getenv("JIRA_TOKEN")
        
    def get_project_metrics(self, project_key: str) -> dict:
        """Get Jira project metrics"""
        if not all([self.base_url, self.email, self.token]):
            return {"error": "Jira credentials not configured"}
        
        try:
            auth = (self.email, self.token)
            headers = {"Accept": "application/json"}
            
            # Get project info
            project_url = f"{self.base_url}/rest/api/3/project/{project_key}"
            project_response = requests.get(project_url, auth=auth, headers=headers, timeout=10)
            project_data = project_response.json() if project_response.status_code == 200 else {}
            
            # Get issues by status
            search_url = f"{self.base_url}/rest/api/3/search"
            jql_query = f"project = '{project_key}' AND created >= -30d"
            search_params = {
                "jql": jql_query,
                "fields": "status,priority,created,resolutiondate"
            }
            
            search_response = requests.get(search_url, auth=auth, headers=headers, params=search_params, timeout=10)
            
            if search_response.status_code != 200:
                return {"error": f"Jira API returned {search_response.status_code}: {search_response.text[:200]}"}
            
            search_data = search_response.json()
            issues = search_data.get("issues", [])
            
            # Calculate metrics
            total_issues = len(issues)
            resolved_issues = len([i for i in issues if i["fields"].get("resolutiondate")])
            
            return {
                "project_key": project_key,
                "project_name": project_data.get("name", "Unknown"),
                "total_issues_last_30_days": total_issues,
                "resolved_issues_last_30_days": resolved_issues,
                "resolution_rate": round(resolved_issues / total_issues * 100, 1) if total_issues > 0 else 0
            }
            
        except Exception as e:
            return {"error": f"Jira API error: {str(e)}"}

# Initialize all metrics services
aws_metrics = EmbeddedAWSMetrics()
github_metrics = EmbeddedGitHubMetrics()
jira_metrics = EmbeddedJiraMetrics()

@app.route("/")
def index():
    """Main dashboard page"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🚀 CTO Dashboard - All Services Integrated</title>
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
            .tab-button {
                transition: all 0.3s ease;
            }
            .tab-button:hover {
                background-color: #f3f4f6;
            }
            .active-tab {
                border-bottom: 2px solid #3b82f6;
                color: #3b82f6 !important;
                background-color: #f9fafb;
            }
            .tab-content {
                animation: fadeIn 0.3s ease-in-out;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-4xl font-bold text-blue-600 mb-8">🚀 CTO Dashboard</h1>
            
            <div id="dashboard-content" class="space-y-6">
                <div class="text-center py-8">
                    <div class="loading-spinner"></div>
                    <span class="text-gray-600">Loading assignments and metrics data...</span>
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

if __name__ == "__main__":
    print("🚀 Starting Integrated CTO Dashboard...")
    print("📍 Access at: http://localhost:3001")
    print("💡 This version has AWS functions embedded - no client-server dependency!")
    print("🔧 All AWS calls are direct function calls within the same process")
    app.run(host="0.0.0.0", port=3001, debug=True)
