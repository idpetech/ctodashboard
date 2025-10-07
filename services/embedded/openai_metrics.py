import os
import requests
from datetime import datetime

class OpenAIMetrics:
    """OpenAI API usage and cost tracking"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1")
        
    def get_usage_metrics(self, config: dict) -> dict:
        """Get OpenAI usage metrics and dashboard link"""
        if not self.api_key:
            return {"error": "OpenAI API key not configured"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Get current date range for this month
            now = datetime.now()
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
            
            # Get usage data from OpenAI API
            usage_url = f"{self.base_url}/usage?date={start_date}"
            
            response = requests.get(usage_url, headers=headers)
            
            if response.status_code == 200:
                usage_data = response.json()
                
                # Calculate totals from the usage data
                total_tokens = 0
                total_requests = 0
                total_cost = 0.0
                models_used = set()
                
                for item in usage_data.get('data', []):
                    total_tokens += item.get('n_context_tokens_total', 0) + item.get('n_generated_tokens_total', 0)
                    total_requests += 1
                    total_cost += item.get('cost', 0.0)
                    if item.get('model'):
                        models_used.add(item.get('model'))
                
                dashboard_url = config.get("api_dashboard_url", "https://platform.openai.com/usage")
                
                return {
                    "dashboard_url": dashboard_url,
                    "billing_url": "https://platform.openai.com/settings/organization/billing",
                    "api_key_configured": True,
                    "usage_this_month": {
                        "tokens_used": total_tokens,
                        "requests_made": total_requests,
                        "estimated_cost": round(total_cost, 2)
                    },
                    "models_used": list(models_used) if models_used else ["No data available"],
                    "last_updated": datetime.now().isoformat(),
                    "status": "active",
                    "period": f"{start_date} to {end_date}",
                    "raw_data_available": len(usage_data.get('data', [])) > 0,
                    "note": "Account balance not available via API - check billing dashboard"
                }
            else:
                return {
                    "error": f"OpenAI API returned {response.status_code}: {response.text}",
                    "dashboard_url": config.get("api_dashboard_url", "https://platform.openai.com/usage"),
                    "billing_url": "https://platform.openai.com/settings/organization/billing",
                    "api_key_configured": True
                }
            
        except Exception as e:
            return {
                "error": f"OpenAI metrics error: {str(e)}",
                "dashboard_url": config.get("api_dashboard_url", "https://platform.openai.com/usage"),
                "billing_url": "https://platform.openai.com/settings/organization/billing",
                "api_key_configured": bool(self.api_key)
            }

# Initialize OpenAI metrics
openai_metrics = OpenAIMetrics()
