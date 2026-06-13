"""
OpenAI API Connector - Clean, modular implementation
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from ..base.base_connector import BaseConnector
from .validator import OpenAIValidator

logger = logging.getLogger(__name__)


class OpenAIConnector(BaseConnector):
    CONNECTOR_TYPE = "openai"

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
                "billing_url": "https://platform.openai.com/settings/organization/billing",
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
                "api_key_configured": self.is_configured(),
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
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "openai_org_id": os.getenv("OPENAI_ORG_ID") or os.getenv("OPENAI_ORGANIZATION"),
            "openai_admin_api_key": os.getenv("OPENAI_ADMIN_API_KEY"),
        }

    def _usage_api_key(self) -> str:
        """Organization usage/billing endpoints require an Admin API key when available."""
        return (self.credentials.get("openai_admin_api_key") or "").strip() or (
            self.credentials.get("openai_api_key") or ""
        ).strip()

    def _api_headers(self, *, for_usage: bool = False) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._usage_api_key() if for_usage else self.credentials.get('openai_api_key')}",
            "Content-Type": "application/json",
        }
        org_id = (self.credentials.get("openai_org_id") or "").strip()
        if org_id:
            headers["OpenAI-Organization"] = org_id
        return headers

    def _get_usage_data(self) -> Dict:
        """Get usage data from OpenAI organization or legacy billing APIs."""
        now = datetime.now()
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        start_time = int(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
        headers = self._api_headers(for_usage=True)
        org_id = (self.credentials.get("openai_org_id") or "").strip()
        last_status = None

        usage_attempts = [
            (
                f"{self.base_url}/organization/usage/completions",
                {"start_time": start_time, "limit": 31, "bucket_width": "1d"},
            ),
            (
                f"{self.base_url}/organization/usage",
                {"start_date": start_date, "end_date": end_date},
            ),
            (
                f"{self.base_url}/dashboard/billing/usage",
                {"start_date": start_date, "end_date": end_date},
            ),
        ]

        for url, params in usage_attempts:
            try:
                response = self._make_request("GET", url, headers=headers, params=params)
                payload = response.json()
                if org_id or "/organization/" in url:
                    payload["_account_scope"] = "organization"
                return payload
            except Exception as exc:
                last_status = getattr(getattr(exc, "response", None), "status_code", None)
                logger.info("OpenAI usage endpoint failed (%s): %s", url, exc)

        has_org = bool(org_id)
        if has_org or (self.credentials.get("openai_admin_api_key") or "").strip():
            message = (
                "Could not read organization usage data with the configured API key(s). "
                "OpenAI organization usage requires an Admin API key with usage read access "
                "(Platform → Settings → Organization → Admin keys)."
            )
            recommendation = (
                "Add an Admin API key in connector credentials (optional Admin API Key field), "
                "confirm your Organization ID (org-…), then reload metrics."
            )
        else:
            message = (
                "Usage/billing API access is unavailable with this API key. "
                "If you upgraded to an Organization account, add your Organization ID (org-…) "
                "and an Admin API key in connector settings."
            )
            recommendation = (
                "Organization usage is not available on standard project API keys alone."
            )

        return {
            "usage_access_limited": True,
            "message": message,
            "recommendation": recommendation,
            "http_status": last_status,
            "organization_id_configured": has_org,
            "admin_key_configured": bool(
                (self.credentials.get("openai_admin_api_key") or "").strip()
            ),
        }

    def _get_billing_data(self) -> Dict:
        """Get billing and subscription data from OpenAI API."""
        headers = self._api_headers(for_usage=True)

        billing_info = {}

        # Get subscription info (usually restricted for personal accounts)
        try:
            response = self._make_request(
                "GET", f"{self.base_url}/dashboard/billing/subscription", headers=headers
            )
            billing_info["subscription"] = response.json()
        except Exception:
            logger.info("Subscription endpoint unavailable for configured OpenAI key")
            billing_info["subscription"] = {
                "access_limited": True,
                "message": "Billing details require an Admin API key or OpenAI dashboard access",
            }

        # Get credit grants (also usually restricted)
        try:
            response = self._make_request(
                "GET", f"{self.base_url}/dashboard/billing/credit_grants", headers=headers
            )
            billing_info["credits"] = response.json()
        except Exception:
            logger.info("Credit grants endpoint unavailable for configured OpenAI key")
            billing_info["credits"] = {
                "access_limited": True,
                "message": "Check https://platform.openai.com/settings/organization/billing for credit balance",
            }

        return billing_info

    def _analyze_usage_data(self, usage_data: Dict, billing_data: Dict, config: Dict) -> Dict:
        """Analyze usage and billing data to create comprehensive metrics"""
        now = datetime.now()
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        # Initialize result structure
        result = {
            "dashboard_url": "https://platform.openai.com/usage",
            "billing_url": "https://platform.openai.com/settings/organization/billing",
            "api_key_configured": True,
            "last_updated": now.isoformat(),
            "period": f"{start_date} to {end_date}",
            "status": "active",
        }

        # Process usage data
        if "error" not in usage_data and "usage_access_limited" not in usage_data:
            usage_analysis = self._process_usage_data(usage_data)
            result.update(usage_analysis)
            if usage_data.get("_account_scope") == "organization":
                result["account_type"] = "organization"
        else:
            if usage_data.get("usage_access_limited"):
                result["account_type"] = "organization_limited"
                result["usage_notice"] = usage_data.get(
                    "message", "Organization usage data unavailable with current credentials"
                )
                result["recommendation"] = usage_data.get("recommendation", "")
                if usage_data.get("organization_id_configured"):
                    result["organization_id"] = (
                        self.credentials.get("openai_org_id") or ""
                    ).strip()
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
                "cost_per_request": 0,
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

        for item in usage_data.get("data", []):
            # Token counts
            context_tokens = item.get("n_context_tokens_total", 0)
            generated_tokens = item.get("n_generated_tokens_total", 0)
            item_tokens = context_tokens + generated_tokens
            total_tokens += item_tokens

            # Request count
            requests = item.get("n_requests", 1)
            total_requests += requests

            # Cost calculation
            cost = item.get("cost", 0.0)
            total_cost += cost

            # Model tracking
            model = item.get("snapshot_id", item.get("model", "unknown"))
            models_used.add(model)

            # Model breakdown
            if model not in model_breakdown:
                model_breakdown[model] = {"requests": 0, "tokens": 0, "cost": 0.0}
            model_breakdown[model]["requests"] += requests
            model_breakdown[model]["tokens"] += item_tokens
            model_breakdown[model]["cost"] += cost

            # Daily usage
            timestamp = item.get("timestamp", item.get("date", ""))
            if timestamp:
                daily_usage.append(
                    {
                        "date": timestamp,
                        "tokens": item_tokens,
                        "requests": requests,
                        "cost": cost,
                        "model": model,
                    }
                )

        # Calculate efficiency metrics
        avg_tokens_per_request = (
            round(total_tokens / total_requests, 2) if total_requests > 0 else 0
        )
        cost_per_thousand_tokens = (
            round((total_cost / total_tokens) * 1000, 4) if total_tokens > 0 else 0
        )
        cost_per_request = round(total_cost / total_requests, 4) if total_requests > 0 else 0

        return {
            "usage_this_month": {
                "total_tokens": total_tokens,
                "tokens_used": total_tokens,  # Dashboard compatibility
                "context_tokens": sum(
                    item.get("n_context_tokens_total", 0) for item in usage_data.get("data", [])
                ),
                "generated_tokens": sum(
                    item.get("n_generated_tokens_total", 0) for item in usage_data.get("data", [])
                ),
                "total_requests": total_requests,
                "requests_made": total_requests,  # Dashboard compatibility
                "estimated_cost": round(total_cost, 2),
                "avg_tokens_per_request": avg_tokens_per_request,
                "cost_per_thousand_tokens": cost_per_thousand_tokens,
                "cost_per_request": cost_per_request,
            },
            "models_used": list(models_used) if models_used else ["No data available"],
            "model_breakdown": model_breakdown,
            "daily_usage": daily_usage[-7:],  # Last 7 days
            "raw_data_points": len(usage_data.get("data", [])),
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
                "organization_id": subscription.get("organization_id", "Not available"),
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
                "active_grants": len(credits.get("data", [])),
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
            "alerts": [],
        }

        # Handle organization accounts where usage API is blocked (wrong key type, etc.)
        if metrics.get("account_type") == "organization_limited":
            org_line = "🏢 Organization account configured"
            if metrics.get("organization_id"):
                org_line += f" ({metrics['organization_id']})"
            insights["usage_patterns"].append(org_line)
            insights["cost_efficiency"].append(
                metrics.get("usage_notice") or "Usage API not accessible with current key"
            )
            if metrics.get("recommendation"):
                insights["optimization_recommendations"].append(f"💡 {metrics['recommendation']}")
            insights["alerts"].append(
                "ℹ️ Add an OpenAI Admin API key for usage metrics (standard project keys cannot read org usage)"
            )
            return insights

        if metrics.get("account_type") == "organization":
            insights["usage_patterns"].append("🏢 Organization usage data connected")

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
            insights["optimization_recommendations"].extend(
                [
                    "🔑 Check API key permissions for usage data access",
                    "📊 Consider upgrading to Organization account for full analytics",
                    "💰 Monitor usage via OpenAI web dashboard",
                ]
            )

        return insights
