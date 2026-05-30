#!/usr/bin/env python3
"""
Test AWS credentials loading from workspace configuration
"""
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append('.')

def test_aws_credentials():
    """Test AWS credentials loading from workspace configuration"""
    
    logger.info("🔧 Testing AWS credentials loading from workspace")
    
    # Test workspace-scoped AWS metrics
    from services.embedded.aws_metrics import EmbeddedAWSMetrics
    
    # Create workspace-scoped instance
    aws_service = EmbeddedAWSMetrics(workspace_id="admin_workspace", assignment_id="IDPETECH")
    
    logger.info(f"AWS Access Key: {aws_service.access_key[:10] if aws_service.access_key else 'None'}...")
    logger.info(f"AWS Secret Key: {'***SET***' if aws_service.secret_key else 'None'}")
    logger.info(f"AWS Region: {aws_service.region}")
    
    # Test if credentials work
    if aws_service.access_key and aws_service.secret_key:
        logger.info("✅ AWS credentials loaded from workspace")
        
        # Try to create a client to test credentials
        try:
            import boto3
            session = boto3.Session(
                aws_access_key_id=aws_service.access_key,
                aws_secret_access_key=aws_service.secret_key,
                region_name=aws_service.region
            )
            
            # Test with STS (simplest test)
            sts_client = session.client('sts')
            identity = sts_client.get_caller_identity()
            logger.info(f"✅ AWS credentials validated! Account: {identity.get('Account')}")
            
            # Test basic resource listing
            ec2_client = session.client('ec2')
            response = ec2_client.describe_instances(MaxResults=5)
            instance_count = sum(len(r['Instances']) for r in response['Reservations'])
            logger.info(f"✅ AWS EC2 access works! Found {instance_count} instances")
            
        except Exception as e:
            logger.error(f"❌ AWS credentials validation failed: {e}")
            
    else:
        logger.error("❌ No AWS credentials loaded")
    
    # Also test non-workspace instance for comparison
    logger.info("\n🔧 Testing global AWS metrics (no workspace)")
    global_aws_service = EmbeddedAWSMetrics()
    logger.info(f"Global AWS Access Key: {global_aws_service.access_key or 'None'}")
    logger.info(f"Global AWS Secret Key: {'***SET***' if global_aws_service.secret_key else 'None'}")

if __name__ == "__main__":
    test_aws_credentials()