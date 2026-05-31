"""
OpenAI API Connector - Clean, modular implementation
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..base.base_connector import BaseConnector
from .validator import OpenAIValidator

logger = logging.getLogger(__name__)

class OpenAIConnector(BaseConnector):
    """
    OpenAI API connector with comprehensive usage and billing tracking
    
    Provides CTO-focused insights including cost analysis, usage patterns,
    model efficiency metrics, and budget forecasting.
    """
    
    def __init__(self, workspace_id: Optional[str] = None, assignment_id: Optional[str] = None):
        super().__init__(workspace_id, assignment_id)
        self.base_url = "https://api.openai.com/v1"
    
    def get_metrics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive OpenAI usage metrics with billing insights"""
        if not self.is_configured():
            return {
                "error": "OpenAI API key not configured",
                "dashboard_url": "https://platform.openai.com/usage",
                "billing_url": "https://platform.openai.com/settings/organization/billing"
            }
        
        try:
            # Get comprehensive usage and billing data
            usage_data = self._get_usage_data()
            billing_data = self._get_billing_data()
            
            # Combine and analyze the data
            metrics = self._analyze_usage_data(usage_data, billing_data, config)
            
            return metrics
            
        except Exception as e:
            logger.error("OpenAI metrics error: %s", e, exc_info=True)
            return {
                "error": f"OpenAI metrics error: {str(e)}",
                "dashboard_url": "https://platform.openai.com/usage",
                "billing_url": "https://platform.openai.com/settings/organization/billing",
                "api_key_configured": self.is_configured()
            }
    
    def validate_credentials(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Validate OpenAI credentials"""
        return OpenAIValidator.validate_credentials(credentials)
    
    def get_required_fields(self) -> list[str]:
        """Get required credential fields"""
        return OpenAIValidator.get_required_fields()
    
    def _load_environment_credentials(self):
        """Load OpenAI API key from environment"""
        self.credentials = {
            "openai_api_key": os.getenv("OPENAI_API_KEY")
        }
    
    def _get_usage_data(self) -> Dict:
        """Get usage data from OpenAI API - optimized for personal accounts"""
        headers = {"Authorization": f"Bearer {self.credentials['openai_api_key']}"}
        
        # Get current month data
        now = datetime.now()
        start_date = now.replace(day=1).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        # For personal accounts, most billing endpoints return 403
        # Try organization usage endpoint first (newer API)
        try:
            response = self._make_request(
                "GET",
                f"{self.base_url}/organization/usage",
                headers=headers,
                params={"start_date": start_date, "end_date": end_date}
            )
            return response.json()
            
        except Exception:
            logger.info("Organization usage endpoint not available for personal account")
            
        # Try dashboard billing endpoint (older API)
        try:
            response = self._make_request(
                "GET",
                f"{self.base_url}/dashboard/billing/usage",
                headers=headers,
                params={"start_date": start_date, "end_date": end_date}
            )
            return response.json()
        except Exception as e:
            logger.info("Billing usage endpoint restricted for personal account: %s", e)
            
        # For personal accounts, return informative message instead of error
        return {
            "personal_account_notice": True,
            "message": "Personal OpenAI accounts have limited access to usage/billing data",
            "recommendation": "Usage tracking available for Organization accounts only"
        }
    
    def _get_billing_data(self) -> Dict:
        """Get billing and subscription data from OpenAI API - handles personal accounts"""
        headers = {"Authorization": f"Bearer {self.credentials['openai_api_key']}"}
        
        billing_info = {}
        
        # Get subscription info (usually restricted for personal accounts)
        try:
            response = self._make_request("GET", f"{self.base_url}/dashboard/billing/subscription", headers=headers)
            billing_info["subscription"] = response.json()
        except Exception:
            logger.info("Subscription endpoint restricted for personal account")
            billing_info["subscription"] = {
                "personal_account": True,
                "message": "Billing details available in OpenAI web dashboard only"
            }
        
        # Get credit grants (also usually restricted)
        try:
            response = self._make_request("GET", f"{self.base_url}/dashboard/billing/credit_grants", headers=headers)
            billing_info["credits"] = response.json()
        except Exception:
            logger.info("Credit grants endpoint restricted for personal account") 
            billing_info["credits"] = {
                "personal_account": True,
                "message": "Check https://platform.openai.com/settings/organization/billing for credit balance"
            }
            
        return billing_info
    
    def _analyze_usage_data(self, usage_data: Dict, billing_data: Dict, config: Dict) -> Dict:
        """Analyze usage and billing data to create comprehensive metrics"""
        now = datetime.now()
        start_date = now.replace(day=1).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        # Initialize result structure
        result = {
            "dashboard_url": "https://platform.openai.com/usage",
            "billing_url": "https://platform.openai.com/settings/organization/billing",
            "api_key_configured": True,
            "last_updated": now.isoformat(),
            "period": f"{start_date} to {end_date}",
            "status": "active"
        }
        
        # Process usage data
        if "error" not in usage_data and "personal_account_notice" not in usage_data:
            usage_analysis = self._process_usage_data(usage_data)
            result.update(usage_analysis)
        else:
            if "personal_account_notice" in usage_data:
                result["account_type"] = "personal"
                result["usage_notice"] = usage_data.get("message", "Personal account - limited usage data")
                result["recommendation"] = usage_data.get("recommendation", "Upgrade to Organization account for detailed usage tracking")
            else:
                result["usage_error"] = usage_data.get("error")
                logger.warning("Usage data not available: %s", usage_data.get("error"))
            
            # Provide fallback structure for dashboard compatibility
            result["usage_this_month"] = {
                "total_tokens": 0,
                "tokens_used": 0,
                "context_tokens": 0,
                "generated_tokens": 0,
                "total_requests": 0,
                "requests_made": 0,
                "estimated_cost": 0,
                "avg_tokens_per_request": 0,
                "cost_per_thousand_tokens": 0,
                "cost_per_request": 0
            }
        
        # Process billing data
        billing_analysis = self._process_billing_data(billing_data)
        result.update(billing_analysis)
        
        # Add CTO insights
        cto_insights = self._generate_cto_insights(result)
        result["cto_insights"] = cto_insights
        
        return result
    
    def _process_usage_data(self, usage_data: Dict) -> Dict:
        """Process raw usage data into metrics"""
        total_tokens = 0
        total_requests = 0
        total_cost = 0.0
        models_used = set()
        daily_usage = []
        model_breakdown = {}
        
        for item in usage_data.get('data', []):
            # Token counts
            context_tokens = item.get('n_context_tokens_total', 0)
            generated_tokens = item.get('n_generated_tokens_total', 0)
            item_tokens = context_tokens + generated_tokens
            total_tokens += item_tokens
            
            # Request count
            requests = item.get('n_requests', 1)
            total_requests += requests
            
            # Cost calculation
            cost = item.get('cost', 0.0)
            total_cost += cost
            
            # Model tracking
            model = item.get('snapshot_id', item.get('model', 'unknown'))
            models_used.add(model)
            
            # Model breakdown
            if model not in model_breakdown:
                model_breakdown[model] = {"requests": 0, "tokens": 0, "cost": 0.0}
            model_breakdown[model]["requests"] += requests
            model_breakdown[model]["tokens"] += item_tokens
            model_breakdown[model]["cost"] += cost
            
            # Daily usage
            timestamp = item.get('timestamp', item.get('date', ''))
            if timestamp:
                daily_usage.append({
                    "date": timestamp,
                    "tokens": item_tokens,
                    "requests": requests,
                    "cost": cost,
                    "model": model
                })
        
        # Calculate efficiency metrics
        avg_tokens_per_request = round(total_tokens / total_requests, 2) if total_requests > 0 else 0
        cost_per_thousand_tokens = round((total_cost / total_tokens) * 1000, 4) if total_tokens > 0 else 0
        cost_per_request = round(total_cost / total_requests, 4) if total_requests > 0 else 0
        
        return {
            "usage_this_month": {
                "total_tokens": total_tokens,
                "tokens_used": total_tokens,  # Dashboard compatibility
                "context_tokens": sum(item.get('n_context_tokens_total', 0) for item in usage_data.get('data', [])),
                "generated_tokens": sum(item.get('n_generated_tokens_total', 0) for item in usage_data.get('data', [])),
                "total_requests": total_requests,
                "requests_made": total_requests,  # Dashboard compatibility
                "estimated_cost": round(total_cost, 2),
                "avg_tokens_per_request": avg_tokens_per_request,
                "cost_per_thousand_tokens": cost_per_thousand_tokens,
                "cost_per_request": cost_per_request
            },
            "models_used": list(models_used) if models_used else ["No data available"],
            "model_breakdown": model_breakdown,
            "daily_usage": daily_usage[-7:],  # Last 7 days
            "raw_data_points": len(usage_data.get('data', []))
        }
    
    def _process_billing_data(self, billing_data: Dict) -> Dict:
        """Process billing data into account information"""
        billing_info = {}
        
        # Process subscription data
        subscription = billing_data.get("subscription", {})
        if "error" not in subscription:
            billing_info["account"] = {
                "plan": subscription.get("plan", {}).get("title", "Unknown"),
                "billing_email": subscription.get("account_email", "Not available"),
                "organization_id": subscription.get("organization_id", "Not available")
            }
        else:
            billing_info["account"] = {"error": subscription.get("error")}
        
        # Process credit grants
        credits = billing_data.get("credits", {})
        if "error" not in credits:
            total_credits = sum(grant.get("amount", 0) for grant in credits.get("data", []))
            used_credits = sum(grant.get("used_amount", 0) for grant in credits.get("data", []))
            remaining_credits = total_credits - used_credits
            
            billing_info["credits"] = {
                "total_granted": round(total_credits, 2),
                "total_used": round(used_credits, 2),
                "remaining": round(remaining_credits, 2),
                "active_grants": len(credits.get("data", []))
            }
        else:
            billing_info["credits"] = {"error": credits.get("error")}
            
        return billing_info
    
    def _generate_cto_insights(self, metrics: Dict) -> Dict:
        """Generate CTO-focused insights and recommendations"""
        insights = {
            "cost_efficiency": [],
            "usage_patterns": [],
            "optimization_recommendations": [],
            "budget_tracking": {},
            "alerts": []
        }
        
        # Handle personal account limitations
        if metrics.get("account_type") == "personal":
            insights["usage_patterns"].append("📱 Personal OpenAI account detected")
            insights["cost_efficiency"].append("💡 Limited usage tracking for personal accounts")
            insights["optimization_recommendations"].extend([
                "📊 Upgrade to Organization account for detailed usage analytics",
                "💰 Monitor usage manually via OpenAI dashboard",
                "🔍 Consider usage tracking at application level"
            ])
            insights["alerts"].append("ℹ️ Usage data limited due to personal account restrictions")
            return insights
        
        usage = metrics.get("usage_this_month", {})
        total_cost = usage.get("estimated_cost", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        # Cost efficiency analysis
        if total_cost > 0:
            insights["cost_efficiency"].append(f"Current monthly spend: ${total_cost}")
            
            if total_cost > 100:
                insights["alerts"].append("⚠️ Monthly spend exceeds $100")
            
            daily_rate = total_cost / datetime.now().day
            projected_monthly = daily_rate * 30
            insights["budget_tracking"]["projected_monthly_cost"] = round(projected_monthly, 2)
            
            if projected_monthly > total_cost * 1.5:
                insights["alerts"].append("📈 Usage trending higher than current pace")
        else:
            # No cost data available
            insights["cost_efficiency"].append("💡 No usage cost data available")
            insights["optimization_recommendations"].append(
                "🔑 Verify API key has billing access or upgrade to Organization account"
            )
        
        # Usage pattern analysis
        if total_tokens > 0:
            insights["usage_patterns"].append(f"Total tokens this month: {total_tokens:,}")
            
            cost_per_1k = usage.get("cost_per_thousand_tokens", 0)
            if cost_per_1k > 0.1:  # High cost per 1k tokens
                insights["optimization_recommendations"].append(
                    "Consider using GPT-3.5-turbo for non-critical tasks to reduce costs"
                )
        else:
            insights["usage_patterns"].append("📊 No usage data available this month")
        
        # Model efficiency recommendations
        model_breakdown = metrics.get("model_breakdown", {})
        if model_breakdown:
            most_expensive = max(model_breakdown.items(), key=lambda x: x[1]["cost"], default=None)
            if most_expensive and most_expensive[1]["cost"] > total_cost * 0.5:
                insights["optimization_recommendations"].append(
                    f"Model '{most_expensive[0]}' accounts for >50% of costs - review usage"
                )
        
        # Request efficiency
        avg_tokens = usage.get("avg_tokens_per_request", 0)
        if avg_tokens > 2000:
            insights["optimization_recommendations"].append(
                "High average tokens per request - consider prompt optimization"
            )
        
        # General recommendations for accounts with no data
        if not insights["optimization_recommendations"] and total_cost == 0 and total_tokens == 0:
            insights["optimization_recommendations"].extend([
                "🔑 Check API key permissions for usage data access",
                "📊 Consider upgrading to Organization account for full analytics",
                "💰 Monitor usage via OpenAI web dashboard"
            ])
            
        return insights