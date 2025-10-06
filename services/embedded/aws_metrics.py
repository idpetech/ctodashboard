# AWS Metrics Service
# Extracted from integrated_dashboard.py

import os
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

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
                return {"error": "AWS Cost Explorer client not available"}
            
            # Get current date range for last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Format dates for AWS API
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Get cost and usage data
            response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_str,
                    'End': end_str
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            # Process the response
            daily_costs = []
            service_costs = {}
            total_cost = 0.0
            
            for result in response.get('ResultsByTime', []):
                date = result['TimePeriod']['Start']
                cost = float(result['Total']['BlendedCost']['Amount'])
                daily_costs.append({
                    'date': date,
                    'cost': cost
                })
                total_cost += cost
                
                # Aggregate by service
                for group in result.get('Groups', []):
                    service = group['Keys'][0]
                    service_cost = float(group['Metrics']['BlendedCost']['Amount'])
                    if service in service_costs:
                        service_costs[service] += service_cost
                    else:
                        service_costs[service] = service_cost
            
            # Calculate daily average
            daily_average = total_cost / len(daily_costs) if daily_costs else 0
            
            # Get recent 7 days cost
            recent_7_days = sum([d['cost'] for d in daily_costs[-7:]])
            previous_7_days = sum([d['cost'] for d in daily_costs[-14:-7]]) if len(daily_costs) >= 14 else 0
            
            # Determine trend
            if recent_7_days > previous_7_days * 1.1:
                trend = "increasing"
            elif recent_7_days < previous_7_days * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
            
            return {
                "total_cost_last_30_days": round(total_cost, 2),
                "daily_average": round(daily_average, 2),
                "daily_costs": daily_costs,
                "top_services": dict(sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:5]),
                "all_services": service_costs,
                "currency": "USD",
                "period": f"{start_str} to {end_str}",
                "recent_7_days_cost": round(recent_7_days, 2),
                "previous_7_days_cost": round(previous_7_days, 2),
                "weekly_trend": trend,
                "recommendations": self._get_cost_recommendations(total_cost, service_costs)
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                return {"error": "AWS API error: User needs ce:GetCostAndUsage permission"}
            else:
                return {"error": f"AWS API error: {error_code}"}
        except Exception as e:
            return {"error": f"AWS metrics error: {str(e)}"}
    
    def get_real_resource_metrics(self) -> dict:
        """Get real AWS resource inventory"""
        try:
            inventory = {
                "ec2": {"instances": [], "running": 0, "stopped": 0, "total_instances": 0},
                "lightsail": {"running": 0, "stopped": 0, "total_instances": 0},
                "rds": {"databases": [], "total_databases": 0},
                "s3": {"buckets": [], "total_buckets": 0}
            }
            
            # EC2 instances
            ec2_client = self._get_aws_client('ec2')
            if ec2_client:
                try:
                    response = ec2_client.describe_instances()
                    for reservation in response.get('Reservations', []):
                        for instance in reservation.get('Instances', []):
                            instance_info = {
                                'id': instance['InstanceId'],
                                'type': instance['InstanceType'],
                                'state': instance['State']['Name'],
                                'launch_time': instance['LaunchTime'].isoformat(),
                                'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                            }
                            inventory['ec2']['instances'].append(instance_info)
                            inventory['ec2']['total_instances'] += 1
                            if instance['State']['Name'] == 'running':
                                inventory['ec2']['running'] += 1
                            elif instance['State']['Name'] == 'stopped':
                                inventory['ec2']['stopped'] += 1
                except ClientError as e:
                    if e.response['Error']['Code'] != 'AccessDenied':
                        print(f"EC2 error: {e}")
            
            # RDS databases
            rds_client = self._get_aws_client('rds')
            if rds_client:
                try:
                    response = rds_client.describe_db_instances()
                    for db in response.get('DBInstances', []):
                        db_info = {
                            'id': db['DBInstanceIdentifier'],
                            'engine': db['Engine'],
                            'status': db['DBInstanceStatus'],
                            'class': db['DBInstanceClass'],
                            'allocated_storage': db['AllocatedStorage']
                        }
                        inventory['rds']['databases'].append(db_info)
                        inventory['rds']['total_databases'] += 1
                except ClientError as e:
                    if e.response['Error']['Code'] != 'AccessDenied':
                        print(f"RDS error: {e}")
            
            # S3 buckets
            s3_client = self._get_aws_client('s3')
            if s3_client:
                try:
                    response = s3_client.list_buckets()
                    inventory['s3']['buckets'] = [bucket['Name'] for bucket in response.get('Buckets', [])]
                    inventory['s3']['total_buckets'] = len(inventory['s3']['buckets'])
                except ClientError as e:
                    if e.response['Error']['Code'] != 'AccessDenied':
                        print(f"S3 error: {e}")
            
            return {"inventory": inventory}
            
        except Exception as e:
            return {"error": f"AWS resource metrics error: {str(e)}"}
    
    def _get_cost_recommendations(self, total_cost: float, service_costs: dict) -> list:
        """Generate cost optimization recommendations"""
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
            "",
            "🔄 ONGOING MONITORING:",
            "• Set up AWS Budget alerts for cost anomalies",
            "• Monthly review of AWS Cost Explorer recommendations",
            "• Quarterly rightsizing analysis for all compute resources"
        ]
        
        # Add specific recommendations based on top services
        top_service = max(service_costs.items(), key=lambda x: x[1]) if service_costs else None
        if top_service and top_service[1] > total_cost * 0.3:
            service_name = top_service[0]
            recommendations.append(f"")
            recommendations.append(f"🔍 TOP SERVICE FOCUS: {service_name} accounts for {top_service[1]/total_cost*100:.1f}% of costs")
            recommendations.append(f"• Review {service_name} usage patterns and optimization opportunities")
        
        return recommendations
