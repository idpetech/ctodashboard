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

# Configure Flask paths
base_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(base_dir, 'frontend', 'dist')
template_folder = os.path.join(base_dir, 'templates')
app = Flask(__name__, static_folder=static_folder, static_url_path='', template_folder=template_folder)

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

class ServiceManager:
    """Central service manager with feature flag integration"""
    
    def __init__(self):
        self.feature_flags = FEATURE_FLAGS
        self.services = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize services based on feature flags"""
        if self.feature_flags.get("workstream_management", False):
            self.services["workstream"] = WorkstreamService()
        
        if self.feature_flags.get("service_config_ui", False):
            self.services["config"] = ServiceConfigService()
        
        if self.feature_flags.get("multi_tenancy", False):
            self.services["tenant"] = TenantService()
    
    def get_service(self, service_name: str):
        """Get service instance if enabled"""
        return self.services.get(service_name)
    
    def is_service_enabled(self, service_name: str) -> bool:
        """Check if service is enabled via feature flag"""
        return service_name in self.services

class WorkstreamService:
    """Workstream management service (disabled by default)"""
    
    def __init__(self):
        self.workstreams = []
        self.enabled = FEATURE_FLAGS.get("workstream_management", False)
    
    def create_workstream(self, name: str, config: dict) -> dict:
        """Create new workstream (disabled by default)"""
        if not self.enabled:
            return {"error": "Workstream management disabled"}
        
        workstream = {
            "id": f"ws_{len(self.workstreams) + 1}",
            "name": name,
            "config": config,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        self.workstreams.append(workstream)
        return workstream
    
    def get_workstreams(self) -> list:
        """Get all workstreams (disabled by default)"""
        if not self.enabled:
            return {"error": "Workstream management disabled"}
        return self.workstreams

class ServiceConfigService:
    """Service configuration management (disabled by default)"""
    
    def __init__(self):
        self.configs = {}
        self.enabled = FEATURE_FLAGS.get("service_config_ui", False)
    
    def add_service_config(self, workstream_id: str, service_type: str, config: dict) -> dict:
        """Add service configuration (disabled by default)"""
        if not self.enabled:
            return {"error": "Service configuration UI disabled"}
        
        config_id = f"{workstream_id}_{service_type}"
        self.configs[config_id] = {
            "workstream_id": workstream_id,
            "service_type": service_type,
            "config": config,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        return self.configs[config_id]
    
    def get_service_configs(self, workstream_id: str = None) -> dict:
        """Get service configurations (disabled by default)"""
        if not self.enabled:
            return {"error": "Service configuration UI disabled"}
        
        if workstream_id:
            return {k: v for k, v in self.configs.items() if v["workstream_id"] == workstream_id}
        return self.configs

class TenantService:
    """Multi-tenancy service (disabled by default)"""
    
    def __init__(self):
        self.tenants = {}
        self.enabled = FEATURE_FLAGS.get("multi_tenancy", False)
    
    def create_tenant(self, name: str, config: dict) -> dict:
        """Create new tenant (disabled by default)"""
        if not self.enabled:
            return {"error": "Multi-tenancy disabled"}
        
        tenant_id = f"tenant_{len(self.tenants) + 1}"
        self.tenants[tenant_id] = {
            "id": tenant_id,
            "name": name,
            "config": config,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        return self.tenants[tenant_id]

# Initialize service manager
service_manager = ServiceManager()


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


# Import and register routes
from routes.api_routes import register_routes
register_routes(app)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3001))
    app.run(host="0.0.0.0", port=port, debug=True)
