# Clean metrics service - each platform has its own class
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import requests
import boto3
from botocore.exceptions import ClientError


class GitHubMetrics:
    """GitHub API integration for code metrics"""
    
    def __init__(self):
        # Get config from environment variables (never hardcode!)
        self.token = os.getenv("GITHUB_TOKEN")
        self.base_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
        self.org = os.getenv("GITHUB_ORG", "")  # Organization name
        
    def get_repo_metrics(self, repo: str, org: str = None) -> Dict:
        """Get metrics for a specific repository"""
        if not self.token:
            return {"error": "GitHub token not configured"}
        
        # Use provided org or fall back to instance variable  
        current_org = org or self.org
        if not current_org:
            return {"error": "GitHub organization not provided"}
        
        
        try:
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get repository info
            repo_url = f"{self.base_url}/repos/{current_org}/{repo}"
            repo_response = requests.get(repo_url, headers=headers)
            
            if repo_response.status_code != 200:
                return {
                    "error": f"GitHub API returned {repo_response.status_code}: {repo_response.text}",
                    "debug_url": repo_url,
                    "debug_token_length": len(self.token) if self.token else 0,
                    "debug_org": current_org,
                    "debug_repo": repo
                }
            
            repo_data = repo_response.json()
            
            # Get recent commits (last 30 days)
            since_date = (datetime.now() - timedelta(days=30)).isoformat()
            commits_url = f"{repo_url}/commits?since={since_date}"
            commits_response = requests.get(commits_url, headers=headers)
            commits = commits_response.json() if commits_response.status_code == 200 else []
            
            # Get pull requests
            prs_url = f"{repo_url}/pulls?state=all&per_page=50"
            prs_response = requests.get(prs_url, headers=headers)
            prs = prs_response.json() if prs_response.status_code == 200 else []
            
            return {
                "repo_name": repo,
                "commits_last_30_days": len(commits),
                "total_prs": len(prs),
                "open_issues": repo_data.get("open_issues_count", 0),
                "stars": repo_data.get("stargazers_count", 0),
                "language": repo_data.get("language", "Unknown"),
                "last_updated": repo_data.get("updated_at", "")
            }
            
        except Exception as e:
            return {"error": f"GitHub API error: {str(e)}"}


class JiraMetrics:
    """Jira API integration for project management metrics"""
    
    def __init__(self):
        # Get config from environment variables (never hardcode!)
        self.base_url = os.getenv("JIRA_URL")  # e.g. "https://company.atlassian.net"
        self.email = os.getenv("JIRA_EMAIL")
        self.token = os.getenv("JIRA_TOKEN")
        self.project_key = os.getenv("JIRA_PROJECT_KEY", "")
        
    def get_project_metrics(self, project_key: str = None) -> Dict:
        """Get metrics for the configured project"""
        if not all([self.base_url, self.email, self.token]):
            return {"error": "Jira credentials not configured"}
        
        # Use provided project_key or fall back to instance variable
        current_project_key = project_key or self.project_key
        if not current_project_key:
            return {"error": "Jira project key not provided"}
        
        try:
            # Jira uses basic auth with email + API token
            auth = (self.email, self.token)
            headers = {"Accept": "application/json"}
            
            # Get project info
            project_url = f"{self.base_url}/rest/api/3/project/{current_project_key}"
            project_response = requests.get(project_url, auth=auth, headers=headers)
            project_data = project_response.json() if project_response.status_code == 200 else {}
            
            # Get issues by status
            search_url = f"{self.base_url}/rest/api/3/search"
            jql_query = f"project = '{current_project_key}' AND created >= -30d"
            search_params = {
                "jql": jql_query,
                "fields": "status,priority,created,resolutiondate"
            }
            
            search_response = requests.get(search_url, auth=auth, headers=headers, params=search_params)
            
            if search_response.status_code != 200:
                return {"error": f"Jira API returned {search_response.status_code}: {search_response.text}"}
            
            search_data = search_response.json()
            issues = search_data.get("issues", []) if isinstance(search_data, dict) else []
            
            # Calculate metrics
            total_issues = len(issues)
            resolved_issues = len([i for i in issues if i["fields"].get("resolutiondate")])
            
            return {
                "project_key": current_project_key,
                "total_issues_last_30_days": total_issues,
                "resolved_issues_last_30_days": resolved_issues,
                "resolution_rate": round(resolved_issues / total_issues * 100, 1) if total_issues > 0 else 0,
                "project_name": project_data.get("name", "Unknown")
            }
            
        except Exception as e:
            return {"error": f"Jira API error: {str(e)}"}


class AWSMetrics:
    """AWS Cost Explorer and Resource Management integration for CTO insights"""
    
    def __init__(self):
        # AWS credentials from environment variables (never hardcode!)
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # Initialize AWS clients lazily
        self._ce_client = None
        self._ec2_client = None
        self._lightsail_client = None
        self._rds_client = None
    
    def _get_aws_client(self, service_name: str):
        """Get AWS client for the specified service"""
        try:
            return boto3.client(
                service_name,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
        except Exception as e:
            print(f"Error creating {service_name} client: {e}")
            return None
    
    def get_comprehensive_aws_report(self) -> Dict:
        """Get comprehensive AWS report with detailed resource information for CTO decision-making"""
        if not all([self.access_key, self.secret_key]):
            return {"error": "AWS credentials not configured"}
        
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "cost_analysis": self._get_cost_analysis(),
                "lightsail_resources": self._get_lightsail_details(),
                "ec2_resources": self._get_ec2_details(),
                "rds_resources": self._get_rds_details(),
                "route53_resources": self._get_route53_details(),
                "s3_resources": self._get_s3_details(),
                "recommendations": self._get_cost_optimization_recommendations()
            }
            
            return report
            
        except Exception as e:
            return {"error": f"AWS comprehensive report error: {str(e)}"}
    
    def _get_cost_analysis(self) -> Dict:
        """Get detailed cost analysis with trends"""
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
                "total_cost_30_days": round(total_cost, 2),
                "daily_average": round(total_cost / 30, 2),
                "weekly_trend": trend,
                "recent_7_days_cost": round(recent_7_days, 2),
                "previous_7_days_cost": round(previous_7_days, 2),
                "service_breakdown": dict(sorted(service_costs.items(), key=lambda x: x[1], reverse=True)),
                "daily_costs": daily_costs[-7:],  # Last 7 days for charting
                "period": f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            return {"error": f"Cost analysis error: {str(e)}"}
    
    def _get_lightsail_details(self) -> Dict:
        """Get detailed Lightsail instance information"""
        try:
            lightsail_client = self._get_aws_client('lightsail')
            if not lightsail_client:
                return {"error": "Could not initialize Lightsail client"}
            
            instances = lightsail_client.get_instances()
            
            instance_details = []
            total_monthly_cost = 0
            
            for instance in instances.get('instances', []):
                bundle_id = instance.get('bundleId', 'unknown')
                state = instance.get('state', {}).get('name', 'unknown')
                
                # Get bundle pricing info
                bundle_info = {}
                try:
                    bundles = lightsail_client.get_bundles()
                    for bundle in bundles.get('bundles', []):
                        if bundle.get('bundleId') == bundle_id:
                            bundle_info = {
                                "cpu_count": bundle.get('cpuCount', 'unknown'),
                                "ram_size_gb": round(bundle.get('ramSizeInGb', 0), 1),
                                "disk_size_gb": bundle.get('diskSizeInGb', 'unknown'),
                                "monthly_price": bundle.get('price', 0),
                                "transfer_gb": bundle.get('transferPerMonthInGb', 'unknown')
                            }
                            total_monthly_cost += bundle.get('price', 0)
                            break
                except Exception:
                    bundle_info = {"error": "Could not fetch bundle details"}
                
                instance_detail = {
                    "name": instance.get('name', 'unnamed'),
                    "bundle_id": bundle_id,
                    "state": state,
                    "created_at": instance.get('createdAt', '').strftime('%Y-%m-%d') if instance.get('createdAt') else 'unknown',
                    "public_ip": instance.get('publicIpAddress', 'none'),
                    "private_ip": instance.get('privateIpAddress', 'none'),
                    "blueprint_name": instance.get('blueprintName', 'unknown'),
                    "bundle_details": bundle_info,
                    "is_static_ip": bool(instance.get('isStaticIp', False)),
                    "tags": instance.get('tags', []),
                    "resource_type": instance.get('resourceType', 'Instance'),
                    "location": instance.get('location', {}).get('regionName', 'unknown')
                }
                
                instance_details.append(instance_detail)
            
            # Cost optimization suggestions for Lightsail
            suggestions = []
            running_instances = [i for i in instance_details if i['state'] == 'running']
            stopped_instances = [i for i in instance_details if i['state'] == 'stopped']
            
            if stopped_instances:
                suggestions.append(f"💡 {len(stopped_instances)} stopped instances still incurring costs - consider terminating if not needed")
            
            if len(running_instances) > 1:
                suggestions.append("💡 Multiple running instances - consider consolidating workloads if possible")
            
            high_cost_instances = [i for i in instance_details if i['bundle_details'].get('monthly_price', 0) > 10]
            if high_cost_instances:
                suggestions.append(f"💡 {len(high_cost_instances)} high-cost instances (>${high_cost_instances[0]['bundle_details']['monthly_price']}/month) - verify they're fully utilized")
            
            return {
                "total_instances": len(instance_details),
                "running_instances": len(running_instances),
                "stopped_instances": len(stopped_instances),
                "estimated_monthly_cost": round(total_monthly_cost, 2),
                "instances": instance_details,
                "cost_optimization_suggestions": suggestions
            }
            
        except Exception as e:
            return {"error": f"Lightsail details error: {str(e)}"}
    
    def _get_ec2_details(self) -> Dict:
        """Get EC2 instance details"""
        try:
            ec2_client = self._get_aws_client('ec2')
            if not ec2_client:
                return {"instances": [], "note": "EC2 client not available"}
            
            response = ec2_client.describe_instances()
            
            instances = []
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_data = {
                        "instance_id": instance.get('InstanceId', 'unknown'),
                        "instance_type": instance.get('InstanceType', 'unknown'),
                        "state": instance.get('State', {}).get('Name', 'unknown'),
                        "public_ip": instance.get('PublicIpAddress', 'none'),
                        "private_ip": instance.get('PrivateIpAddress', 'none'),
                        "launch_time": instance.get('LaunchTime', '').strftime('%Y-%m-%d %H:%M') if instance.get('LaunchTime') else 'unknown',
                        "vpc_id": instance.get('VpcId', 'none'),
                        "subnet_id": instance.get('SubnetId', 'none'),
                        "security_groups": [sg.get('GroupName', sg.get('GroupId', 'unknown')) for sg in instance.get('SecurityGroups', [])],
                        "tags": {tag.get('Key', 'unknown'): tag.get('Value', '') for tag in instance.get('Tags', [])}
                    }
                    instances.append(instance_data)
            
            running_instances = [i for i in instances if i['state'] == 'running']
            stopped_instances = [i for i in instances if i['state'] == 'stopped']
            
            return {
                "total_instances": len(instances),
                "running_instances": len(running_instances), 
                "stopped_instances": len(stopped_instances),
                "instances": instances,
                "suggestions": ["💡 Monitor instance utilization to optimize sizing"] if instances else []
            }
            
        except Exception as e:
            return {"error": f"EC2 details error: {str(e)}"}
    
    def _get_rds_details(self) -> Dict:
        """Get RDS database details"""
        try:
            rds_client = self._get_aws_client('rds')
            if not rds_client:
                return {"databases": [], "note": "RDS client not available"}
            
            response = rds_client.describe_db_instances()
            
            databases = []
            for db in response.get('DBInstances', []):
                db_data = {
                    "db_instance_id": db.get('DBInstanceIdentifier', 'unknown'),
                    "db_instance_class": db.get('DBInstanceClass', 'unknown'),
                    "engine": db.get('Engine', 'unknown'),
                    "engine_version": db.get('EngineVersion', 'unknown'),
                    "status": db.get('DBInstanceStatus', 'unknown'),
                    "allocated_storage": f"{db.get('AllocatedStorage', 0)} GB",
                    "storage_type": db.get('StorageType', 'unknown'),
                    "multi_az": db.get('MultiAZ', False),
                    "vpc_id": db.get('DBSubnetGroup', {}).get('VpcId', 'none'),
                    "created_time": db.get('InstanceCreateTime', '').strftime('%Y-%m-%d') if db.get('InstanceCreateTime') else 'unknown',
                    "backup_retention_period": f"{db.get('BackupRetentionPeriod', 0)} days"
                }
                databases.append(db_data)
            
            return {
                "total_databases": len(databases),
                "databases": databases,
                "suggestions": ["💡 Review backup retention periods and storage allocation"] if databases else []
            }
            
        except Exception as e:
            return {"error": f"RDS details error: {str(e)}"}
    
    def _get_route53_details(self) -> Dict:
        """Get Route 53 hosted zone details"""
        try:
            route53_client = self._get_aws_client('route53')
            if not route53_client:
                return {"hosted_zones": [], "note": "Route53 client not available"}
            
            response = route53_client.list_hosted_zones()
            
            zones = []
            for zone in response.get('HostedZones', []):
                zone_data = {
                    "zone_id": zone.get('Id', '').split('/')[-1],
                    "name": zone.get('Name', 'unknown'),
                    "record_count": zone.get('ResourceRecordSetCount', 0),
                    "private_zone": zone.get('Config', {}).get('PrivateZone', False),
                    "comment": zone.get('Config', {}).get('Comment', 'No comment')
                }
                zones.append(zone_data)
            
            return {
                "total_hosted_zones": len(zones),
                "hosted_zones": zones,
                "suggestions": ["💡 Review unused hosted zones - each costs $0.50/month"] if len(zones) > 1 else []
            }
            
        except Exception as e:
            return {"error": f"Route53 details error: {str(e)}"}
    
    def _get_s3_details(self) -> Dict:
        """Get S3 bucket details"""
        try:
            s3_client = self._get_aws_client('s3')
            if not s3_client:
                return {"buckets": [], "note": "S3 client not available"}
            
            response = s3_client.list_buckets()
            
            buckets = []
            total_size = 0
            
            for bucket in response.get('Buckets', []):
                bucket_name = bucket.get('Name', 'unknown')
                
                # Get bucket size (this is an approximation)
                try:
                    cloudwatch = self._get_aws_client('cloudwatch')
                    if cloudwatch:
                        size_response = cloudwatch.get_metric_statistics(
                            Namespace='AWS/S3',
                            MetricName='BucketSizeBytes',
                            Dimensions=[
                                {'Name': 'BucketName', 'Value': bucket_name},
                                {'Name': 'StorageType', 'Value': 'StandardStorage'}
                            ],
                            StartTime=datetime.now() - timedelta(days=2),
                            EndTime=datetime.now(),
                            Period=86400,
                            Statistics=['Maximum']
                        )
                        
                        bucket_size = 0
                        if size_response.get('Datapoints'):
                            bucket_size = max(dp['Maximum'] for dp in size_response['Datapoints'])
                            total_size += bucket_size
                        
                        bucket_data = {
                            "name": bucket_name,
                            "creation_date": bucket.get('CreationDate', '').strftime('%Y-%m-%d') if bucket.get('CreationDate') else 'unknown',
                            "size_bytes": bucket_size,
                            "size_readable": self._format_bytes(bucket_size)
                        }
                    else:
                        bucket_data = {
                            "name": bucket_name,
                            "creation_date": bucket.get('CreationDate', '').strftime('%Y-%m-%d') if bucket.get('CreationDate') else 'unknown',
                            "size_bytes": "N/A",
                            "size_readable": "N/A (CloudWatch unavailable)"
                        }
                        
                except Exception:
                    bucket_data = {
                        "name": bucket_name,
                        "creation_date": bucket.get('CreationDate', '').strftime('%Y-%m-%d') if bucket.get('CreationDate') else 'unknown',
                        "size_bytes": "N/A",
                        "size_readable": "N/A (Error fetching size)"
                    }
                
                buckets.append(bucket_data)
            
            return {
                "total_buckets": len(buckets),
                "buckets": buckets,
                "total_size_readable": self._format_bytes(total_size) if total_size > 0 else "N/A",
                "suggestions": ["💡 Review bucket contents and consider lifecycle policies for cost optimization"] if buckets else []
            }
            
        except Exception as e:
            return {"error": f"S3 details error: {str(e)}"}
    
    def _format_bytes(self, bytes_value: float) -> str:
        """Format bytes into human readable format"""
        if bytes_value == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def _get_cost_optimization_recommendations(self) -> List[str]:
        """Generate CTO-level cost optimization recommendations"""
        recommendations = [
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
            "• Review data transfer costs and optimize architecture",
            "",
            "🔄 ONGOING MONITORING:",
            "• Set up AWS Budget alerts for cost anomalies",
            "• Monthly review of AWS Cost Explorer recommendations",
            "• Quarterly rightsizing analysis for all compute resources",
            "• Track cost per project/environment with proper tagging",
            "",
            "🚨 RED FLAGS TO INVESTIGATE:",
            "• Instances running 24/7 that could be scheduled",
            "• High data transfer costs (review architecture)",
            "• Multiple environments with similar configurations",
            "• Services with consistently low utilization (<20%)"
        ]
        
        return recommendations
        
    def get_cost_metrics(self) -> Dict:
        """Get comprehensive AWS insights for CTO decision making
        
        Returns both the original simple format (for frontend compatibility)
        and enhanced detailed insights for CTO analysis.
        """
        if not all([self.access_key, self.secret_key]):
            return {"error": "AWS credentials not configured"}
        
        try:
            # Get the comprehensive report
            comprehensive_report = self.get_comprehensive_aws_report()
            
            if "error" in comprehensive_report:
                return comprehensive_report
            
            # Extract basic cost data for frontend compatibility
            cost_analysis = comprehensive_report.get("cost_analysis", {})
            
            if "error" in cost_analysis:
                return cost_analysis
            
            # Create backward-compatible response with enhanced data
            response = {
                # Original fields for frontend compatibility
                "total_cost_last_30_days": cost_analysis.get("total_cost_30_days", 0),
                "currency": "USD",
                "period": cost_analysis.get("period", "N/A"),
                "top_services": dict(list(cost_analysis.get("service_breakdown", {}).items())[:5]),
                
                # Enhanced CTO insights
                "cto_insights": {
                    "cost_trend": {
                        "weekly_trend": cost_analysis.get("weekly_trend", "unknown"),
                        "daily_average": cost_analysis.get("daily_average", 0),
                        "recent_7_days_cost": cost_analysis.get("recent_7_days_cost", 0),
                        "previous_7_days_cost": cost_analysis.get("previous_7_days_cost", 0),
                        "daily_costs": cost_analysis.get("daily_costs", [])
                    },
                    "resource_inventory": {
                        "route53": comprehensive_report.get("route53_resources", {}),
                        "s3": comprehensive_report.get("s3_resources", {}),
                        "lightsail": comprehensive_report.get("lightsail_resources", {}),
                        "ec2": comprehensive_report.get("ec2_resources", {}),
                        "rds": comprehensive_report.get("rds_resources", {})
                    },
                    "optimization_recommendations": comprehensive_report.get("recommendations", []),
                    "detailed_service_breakdown": cost_analysis.get("service_breakdown", {})
                }
            }
            
            return response
            
        except Exception as e:
            return {"error": f"AWS metrics error: {str(e)}"}


class RailwayMetrics:
    """Railway API integration for deployment metrics
    
    NOTE: As of August 2024, Railway appears to have deprecated their public API.
    All known GraphQL and REST endpoints return 404. This service provides
    placeholder metrics until Railway's API becomes available again.
    """
    
    def __init__(self):
        # Railway config from environment variables (never hardcode!)
        self.token = os.getenv("RAILWAY_TOKEN")
        self.base_url = os.getenv("RAILWAY_API_URL", "https://backboard.railway.app/graphql")
        self.project_id = os.getenv("RAILWAY_PROJECT_ID")
        
        # Railway API Status: Currently unavailable (all endpoints return 404)
        self.api_available = False
        
    async def get_deployment_metrics(self) -> Dict:
        """Get Railway deployment metrics
        
        Currently returns helpful error information as Railway API is unavailable.
        Future implementations should check Railway's current API documentation.
        """
        if not self.token:
            return {
                "error": "Railway token not configured",
                "status": "missing_token"
            }
        
        # Quick check: try a simple endpoint first to avoid complex operations
        try:
            import requests
            test_response = requests.get(
                'https://backboard.railway.app/api/projects',
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=5
            )
            
            # If we get anything other than 404, the API might be available
            if test_response.status_code != 404:
                # Proceed with the full GraphQL attempt
                return await self._attempt_graphql_query()
            else:
                # API is unavailable - return helpful fallback info
                return self._get_fallback_metrics()
                
        except Exception as e:
            # Network or other error - return fallback
            return self._get_fallback_metrics(f"Connection error: {str(e)}")
    
    def _get_fallback_metrics(self, additional_error: str = None) -> Dict:
        """Return helpful fallback metrics when Railway API is unavailable"""
        return {
            "status": "api_unavailable",
            "error": "Railway API endpoints are currently unavailable (all return 404)",
            "project_id": self.project_id,
            "attempted_endpoint": self.base_url,
            "api_status": "As of August 2024, Railway appears to have deprecated public API access",
            "suggestion": "Check Railway dashboard manually or use Railway CLI for deployment status",
            "fallback_data": {
                "project_name": f"Project: {self.project_id}",
                "total_deployments": "N/A", 
                "successful_deployments": "N/A",
                "success_rate": "N/A",
                "last_deployment": "Check Railway dashboard"
            },
            "next_steps": [
                "1. Check Railway's official documentation for API changes",
                "2. Verify if Railway has moved to CLI-only approach",
                "3. Consider using Railway CLI in deployment pipeline",
                "4. Check if token needs to be regenerated"
            ],
            "additional_error": additional_error
        }
    
    async def _attempt_graphql_query(self) -> Dict:
        """Attempt the original GraphQL query if API seems available"""
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # Railway uses GraphQL - get project deployments
            query = """
            query GetProject($projectId: String!) {
                project(id: $projectId) {
                    name
                    deployments(first: 10) {
                        edges {
                            node {
                                id
                                status
                                createdAt
                                meta
                            }
                        }
                    }
                }
            }
            """
            
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json={
                        "query": query,
                        "variables": {"projectId": self.project_id}
                    }
                ) as response:
                    # Check if response is not 200 first
                    if response.status != 200:
                        response_text = await response.text()
                        return self._get_fallback_metrics(f"GraphQL endpoint returned {response.status}: {response_text[:100]}")
                    
                    # Try to parse JSON response
                    try:
                        data = await response.json()
                    except Exception as json_error:
                        response_text = await response.text()
                        return self._get_fallback_metrics(f"Invalid JSON response: {str(json_error)}")
                    
                    if "errors" in data:
                        return self._get_fallback_metrics(f"GraphQL errors: {data['errors']}")
                    
                    project = data.get("data", {}).get("project", {})
                    deployments = project.get("deployments", {}).get("edges", [])
                    
                    # Calculate metrics - SUCCESS! We got real data
                    total_deployments = len(deployments)
                    successful_deployments = len([
                        d for d in deployments 
                        if d["node"]["status"] == "SUCCESS"
                    ])
                    
                    return {
                        "status": "success",
                        "project_name": project.get("name", "Unknown"),
                        "total_deployments": total_deployments,
                        "successful_deployments": successful_deployments,
                        "success_rate": round(successful_deployments / total_deployments * 100, 1) if total_deployments > 0 else 0,
                        "last_deployment": deployments[0]["node"]["createdAt"] if deployments else None
                    }
                    
        except Exception as e:
            return self._get_fallback_metrics(f"GraphQL query failed: {str(e)}")


class MetricsAggregator:
    """Aggregates metrics from all services"""
    
    def __init__(self):
        self.github = GitHubMetrics()
        self.jira = JiraMetrics()
        self.aws = AWSMetrics()
        self.railway = RailwayMetrics()
    
    async def get_all_metrics(self, assignment_config: Dict) -> Dict:
        """Get metrics for an assignment from all configured services"""
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "assignment_id": assignment_config.get("id", "unknown")
        }
        
        # Get GitHub metrics if configured
        github_config = assignment_config.get("metrics_config", {}).get("github", {})
        if github_config.get("enabled", False):
            github_data = []
            repos = github_config.get("repos", [])
            org = github_config.get("org", "")
            for repo in repos:
                repo_metrics = self.github.get_repo_metrics(repo, org)
                github_data.append(repo_metrics)
            metrics["github"] = github_data
        
        # Get Jira metrics if configured
        jira_config = assignment_config.get("metrics_config", {}).get("jira", {})
        if jira_config.get("enabled", False):
            project_key = jira_config.get("project_key", "")
            metrics["jira"] = self.jira.get_project_metrics(project_key)
        
        # Get AWS metrics if configured
        aws_config = assignment_config.get("metrics_config", {}).get("aws", {})
        if aws_config.get("enabled", False):
            metrics["aws"] = self.aws.get_cost_metrics()
        
        # Get Railway metrics if configured
        railway_config = assignment_config.get("metrics_config", {}).get("railway", {})
        if railway_config.get("enabled", False):
            os.environ["RAILWAY_PROJECT_ID"] = railway_config.get("project_id", "")
            metrics["railway"] = await self.railway.get_deployment_metrics()
        
        return metrics