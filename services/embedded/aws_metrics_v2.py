# AWS Metrics V2 - Comprehensive AWS metrics service
# Copied from backend/metrics_service.py::AWSMetrics
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError

class EmbeddedAWSMetricsV2:
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

