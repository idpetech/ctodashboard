#!/usr/bin/env python3
"""
Test workspace-scoped AWS metrics directly
"""
import sys
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append('.')

def test_aws_workspace_metrics():
    """Test workspace-scoped AWS metrics"""
    
    logger.info("🔧 Testing workspace-scoped AWS metrics")
    
    # Test getting workspace connectors
    from routes.api_routes import get_workspace_connectors
    
    workspace_id = "admin_workspace"
    assignment_id = "IDPETECH"
    
    logger.info(f"Getting workspace connectors for {workspace_id}/{assignment_id}")
    
    connectors = get_workspace_connectors(workspace_id, assignment_id)
    
    logger.info(f"Available connectors: {list(connectors.keys())}")
    
    # Test AWS connector specifically
    aws_connector = connectors['aws']
    logger.info(f"AWS connector type: {type(aws_connector)}")
    
    # Test AWS credentials
    logger.info(f"AWS access key: {aws_connector.access_key[:10] if aws_connector.access_key else 'None'}...")
    logger.info(f"AWS secret key: {'***SET***' if aws_connector.secret_key else 'None'}")
    logger.info(f"AWS region: {aws_connector.region}")
    
    # Test getting AWS metrics
    try:
        logger.info("Getting AWS metrics...")
        aws_metrics = aws_connector.get_metrics()
        logger.info("✅ AWS metrics retrieved successfully!")
        
        # Print summary
        if 'cost_analysis' in aws_metrics:
            cost_info = aws_metrics['cost_analysis']
            if 'error' in cost_info:
                logger.warning(f"Cost analysis error: {cost_info['error']}")
            else:
                logger.info(f"Cost analysis: {cost_info}")
        
        if 'resources' in aws_metrics:
            resources = aws_metrics['resources']
            if 'inventory' in resources:
                inventory = resources['inventory']
                logger.info(f"EC2 instances: {inventory.get('ec2', {}).get('total_instances', 'N/A')}")
                logger.info(f"S3 buckets: {inventory.get('s3', {}).get('total_buckets', 'N/A')}")
                logger.info(f"RDS databases: {inventory.get('rds', {}).get('total_databases', 'N/A')}")
        
        return aws_metrics
        
    except Exception as e:
        logger.error(f"❌ Error getting AWS metrics: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    metrics = test_aws_workspace_metrics()
    if metrics:
        print("\n" + "="*50)
        print("FULL AWS METRICS:")
        print(json.dumps(metrics, indent=2))