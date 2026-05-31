import os
import requests
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

class OpenAIMetrics:
    """Enhanced OpenAI API usage and cost tracking with billing insights"""

    def __init__(self, workspace_id=None, assignment_id=None):
        # Phase 3: Support workspace credentials with environment variable fallback
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id
        
        # Initialize credentials (preserves existing behavior if no workspace context)
        self._init_credentials()
        
        self.base_url = "https://api.openai.com/v1"
        
    def _init_credentials(self):
        """Initialize OpenAI credentials with workspace support and env var fallback"""
        if self.workspace_id and self.assignment_id:
            try:
                # Load credentials directly from workspace assignment JSON
                from services.workspace.workspace_service import WorkspaceService
                workspace_service = WorkspaceService()
                assignment = workspace_service.get_assignment(self.workspace_id, self.assignment_id)
                
                if assignment and assignment.get('metrics_config', {}).get('openai', {}).get('auth_instance', {}).get('credentials'):
                    openai_creds = assignment['metrics_config']['openai']['auth_instance']['credentials']
                    self.api_key = openai_creds.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
                    logger.info("Loaded OpenAI credentials from workspace assignment")
                else:
                    raise ValueError("No OpenAI credentials in assignment")
            except Exception as e:
                logger.warning("Could not load workspace credentials, falling back to env vars: %s", e)
                # OpenAI credentials from environment variables
                self.api_key = os.getenv("OPENAI_API_KEY")
        else:
            # Fallback to environment variables (preserves existing behavior)
            self.api_key = os.getenv("OPENAI_API_KEY")
        
    def get_usage_metrics(self, config: dict) -> dict:
        """Get comprehensive OpenAI usage metrics with billing insights"""
        if not self.api_key:
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
                "api_key_configured": bool(self.api_key)
            }
    
    def _get_usage_data(self) -> Dict:
        """Get usage data from OpenAI API"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Get current month data
        now = datetime.now()
        start_date = now.replace(day=1).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        # Try the organization usage endpoint (most accurate)
        usage_url = f"{self.base_url}/organization/usage"
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = requests.get(usage_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            # Fallback to older usage endpoint
            logger.info("Organization usage endpoint not available, trying alternative")
            usage_url = f"{self.base_url}/dashboard/billing/usage"
            response = requests.get(usage_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
        
        # If both fail, return error info
        logger.warning("Usage API failed: %s - %s", response.status_code, response.text[:100])
        return {"error": f"API Error {response.status_code}", "status_code": response.status_code}
    
    def _get_billing_data(self) -> Dict:
        """Get billing and subscription data from OpenAI API"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        billing_info = {}
        
        try:
            # Get subscription info
            subscription_url = f"{self.base_url}/dashboard/billing/subscription"
            response = requests.get(subscription_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                billing_info["subscription"] = response.json()
            else:
                billing_info["subscription"] = {"error": f"API Error {response.status_code}"}
                
        except Exception as e:
            billing_info["subscription"] = {"error": str(e)}
        
        try:
            # Get credit grants
            credits_url = f"{self.base_url}/dashboard/billing/credit_grants"
            response = requests.get(credits_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                billing_info["credits"] = response.json()
            else:
                billing_info["credits"] = {"error": f"API Error {response.status_code}"}
                
        except Exception as e:
            billing_info["credits"] = {"error": str(e)}
            
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
        if "error" not in usage_data:
            usage_analysis = self._process_usage_data(usage_data)
            result.update(usage_analysis)
        else:
            result["usage_error"] = usage_data.get("error")
            logger.warning("Usage data not available: %s", usage_data.get("error"))
        
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
                model_breakdown[model] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
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
                "context_tokens": sum(item.get('n_context_tokens_total', 0) for item in usage_data.get('data', [])),
                "generated_tokens": sum(item.get('n_generated_tokens_total', 0) for item in usage_data.get('data', [])),
                "total_requests": total_requests,
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
        
        usage = metrics.get("usage_this_month", {})
        total_cost = usage.get("estimated_cost", 0)
        total_tokens = usage.get("total_tokens", 0)
        usage.get("total_requests", 0)
        
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
        
        # Usage pattern analysis
        if total_tokens > 0:
            insights["usage_patterns"].append(f"Total tokens this month: {total_tokens:,}")
            
            cost_per_1k = usage.get("cost_per_thousand_tokens", 0)
            if cost_per_1k > 0.1:  # High cost per 1k tokens
                insights["optimization_recommendations"].append(
                    "Consider using GPT-3.5-turbo for non-critical tasks to reduce costs"
                )
        
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
        
        # General recommendations
        if not insights["optimization_recommendations"]:
            insights["optimization_recommendations"].append(
                "Usage patterns look efficient - continue monitoring for changes"
            )
            
        return insights

# Initialize OpenAI metrics
openai_metrics = OpenAIMetrics()
