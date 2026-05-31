#!/usr/bin/env python3
"""
Test enhanced OpenAI metrics connector with workspace support
"""
import sys
import logging
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append('.')

def test_openai_enhanced_metrics():
    """Test enhanced OpenAI metrics with both global and workspace configurations"""
    
    logger.info("🔧 Testing Enhanced OpenAI Metrics Connector")
    logger.info("=" * 60)
    
    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("⚠️  No OPENAI_API_KEY environment variable found")
        logger.info("Testing will show configuration structure without real API calls")
    else:
        logger.info(f"✅ OpenAI API key configured: {api_key[:12]}...")
    
    # Test 1: Global OpenAI metrics (backward compatibility)
    logger.info("\n🌍 Testing Global OpenAI Metrics (backward compatibility)")
    print("-" * 50)
    
    from services.embedded.openai_metrics import OpenAIMetrics
    
    global_openai = OpenAIMetrics()
    logger.info(f"Global API key configured: {'Yes' if global_openai.api_key else 'No'}")
    
    try:
        global_metrics = global_openai.get_usage_metrics({
            "api_dashboard_url": "https://platform.openai.com/usage"
        })
        logger.info("✅ Global metrics retrieval completed")
        
        # Show structure
        logger.info("📊 Global metrics structure:")
        for key in global_metrics.keys():
            if key == 'usage_this_month' and isinstance(global_metrics[key], dict):
                logger.info(f"  - {key}: {len(global_metrics[key])} fields")
            elif key == 'cto_insights' and isinstance(global_metrics[key], dict):
                logger.info(f"  - {key}: {len(global_metrics[key])} categories")
            else:
                logger.info(f"  - {key}: {type(global_metrics[key]).__name__}")
        
        if 'error' in global_metrics:
            logger.warning(f"⚠️  Global metrics error: {global_metrics['error']}")
        else:
            usage = global_metrics.get('usage_this_month', {})
            logger.info(f"📈 Usage summary: {usage.get('total_requests', 0)} requests, ${usage.get('estimated_cost', 0)} cost")
    
    except Exception as e:
        logger.error(f"❌ Global metrics test failed: {e}")
    
    # Test 2: Workspace-scoped OpenAI metrics
    logger.info("\n🏢 Testing Workspace-Scoped OpenAI Metrics")
    print("-" * 50)
    
    try:
        workspace_openai = OpenAIMetrics(workspace_id="admin_workspace", assignment_id="IDPETECH")
        logger.info(f"Workspace API key configured: {'Yes' if workspace_openai.api_key else 'No'}")
        
        workspace_metrics = workspace_openai.get_usage_metrics({
            "api_dashboard_url": "https://platform.openai.com/usage"
        })
        logger.info("✅ Workspace metrics retrieval completed")
        
        # Show CTO insights specifically
        if 'cto_insights' in workspace_metrics:
            insights = workspace_metrics['cto_insights']
            logger.info("🧠 CTO Insights generated:")
            
            if insights.get('alerts'):
                logger.info(f"  🚨 Alerts: {len(insights['alerts'])}")
                for alert in insights['alerts'][:2]:  # Show first 2
                    logger.info(f"    - {alert}")
            
            if insights.get('optimization_recommendations'):
                logger.info(f"  💡 Optimizations: {len(insights['optimization_recommendations'])}")
                for rec in insights['optimization_recommendations'][:2]:  # Show first 2
                    logger.info(f"    - {rec}")
            
            budget = insights.get('budget_tracking', {})
            if 'projected_monthly_cost' in budget:
                logger.info(f"  💰 Projected monthly: ${budget['projected_monthly_cost']}")
        
        if 'error' in workspace_metrics:
            logger.warning(f"⚠️  Workspace metrics error: {workspace_metrics['error']}")
    
    except Exception as e:
        logger.error(f"❌ Workspace metrics test failed: {e}", exc_info=True)
    
    # Test 3: API endpoint testing (if key available)
    if api_key:
        logger.info("\n🔌 Testing Direct OpenAI API Endpoints")
        print("-" * 50)
        
        try:
            import requests
            
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # Test usage endpoint
            logger.info("Testing /organization/usage endpoint...")
            response = requests.get(
                "https://api.openai.com/v1/organization/usage",
                headers=headers,
                params={"start_date": "2026-05-01", "end_date": "2026-05-30"},
                timeout=10
            )
            logger.info(f"Usage API response: {response.status_code}")
            
            if response.status_code == 404:
                logger.info("Organization endpoint not available, trying billing endpoint...")
                response = requests.get(
                    "https://api.openai.com/v1/dashboard/billing/usage",
                    headers=headers,
                    params={"start_date": "2026-05-01", "end_date": "2026-05-30"},
                    timeout=10
                )
                logger.info(f"Billing usage API response: {response.status_code}")
            
            # Test subscription endpoint
            logger.info("Testing /dashboard/billing/subscription endpoint...")
            response = requests.get(
                "https://api.openai.com/v1/dashboard/billing/subscription",
                headers=headers,
                timeout=10
            )
            logger.info(f"Subscription API response: {response.status_code}")
            
        except Exception as e:
            logger.error(f"❌ Direct API test failed: {e}")
    
    logger.info("\n🎉 Enhanced OpenAI Connector Testing Complete!")
    logger.info("=" * 60)
    
    return True

def show_expected_features():
    """Show what features the enhanced connector provides"""
    logger.info("\n📋 Enhanced OpenAI Connector Features")
    logger.info("=" * 60)
    
    features = {
        "🔧 Technical Features": [
            "Workspace-scoped API key management",
            "Fallback to environment variables",
            "Multiple API endpoint support",
            "Comprehensive error handling",
            "Rate limiting awareness"
        ],
        "📊 Usage Metrics": [
            "Monthly token usage (input/output breakdown)",
            "Request count and patterns", 
            "Cost per model analysis",
            "Daily usage trending",
            "Efficiency metrics (cost per token/request)"
        ],
        "💰 Billing Insights": [
            "Account subscription details",
            "Credit grants and remaining balance",
            "Monthly spend projection",
            "Budget threshold alerts",
            "Cost trend analysis"
        ],
        "🧠 CTO-Focused Analytics": [
            "Cost efficiency recommendations",
            "Usage pattern analysis", 
            "Model optimization suggestions",
            "Budget tracking and forecasting",
            "Anomaly detection and alerts"
        ]
    }
    
    for category, items in features.items():
        logger.info(f"\n{category}:")
        for item in items:
            logger.info(f"  ✅ {item}")
    
    logger.info("\n💡 Integration Benefits:")
    logger.info("  • Real-time cost monitoring for CTOs")
    logger.info("  • Proactive optimization recommendations")
    logger.info("  • Multi-workspace cost tracking")
    logger.info("  • Automated budget alerts")
    logger.info("  • Historical trend analysis")

if __name__ == "__main__":
    show_expected_features()
    test_openai_enhanced_metrics()