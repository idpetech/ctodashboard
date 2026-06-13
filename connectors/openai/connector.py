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

    def _parse_api_error(self, response) -> str:
        try:
            payload = response.json()
            err = payload.get("error")
            if isinstance(err, dict):
                return err.get("message") or str(err)
            if isinstance(err, str):
                return err
            return response.text[:240]
        except Exception:
            return response.text[:240] if response is not None else "Unknown OpenAI API error"

    def _http_get_json(
        self, url: str, headers: Dict[str, str], params: Optional[dict] = None
    ) -> tuple[bool, dict, Optional[dict]]:
        import requests

        try:
            response = requests.get(url, headers=headers, params=params or {}, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    return True, data, None
                return False, {}, {"status": 200, "message": "Unexpected non-object JSON response"}
            return (
                False,
                {},
                {
                    "status": response.status_code,
                    "message": self._parse_api_error(response),
                },
            )
        except requests.RequestException as exc:
            return False, {}, {"status": None, "message": str(exc)}

    def _merge_org_bucket_pages(self, pages: list) -> Dict:
        merged_buckets = []
        for page in pages:
            merged_buckets.extend(page.get("data") or [])
        return {"object": "page", "data": merged_buckets, "_account_scope": "organization"}

    def _usage_query_params(self, start_time: int, *, group_by_model: bool = False) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "start_time": start_time,
            "limit": 31,
            "bucket_width": "1d",
        }
        if group_by_model:
            params["group_by[]"] = "model"
        return params

    _USAGE_GROUP_BY_MODEL = frozenset(
        {
            "completions",
            "embeddings",
            "moderations",
            "images",
            "audio_speeches",
            "audio_transcriptions",
        }
    )

    def _get_usage_data(self) -> Dict:
        """Get usage data from OpenAI organization usage APIs (Admin key required)."""
        now = datetime.now()
        start_time = int(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
        headers = self._api_headers(for_usage=True)
        org_id = (self.credentials.get("openai_org_id") or "").strip()
        admin_configured = bool((self.credentials.get("openai_admin_api_key") or "").strip())
        usage_paths = [
            ("completions", f"{self.base_url}/organization/usage/completions"),
            ("embeddings", f"{self.base_url}/organization/usage/embeddings"),
            ("moderations", f"{self.base_url}/organization/usage/moderations"),
            ("images", f"{self.base_url}/organization/usage/images"),
            ("audio_speeches", f"{self.base_url}/organization/usage/audio_speeches"),
            ("audio_transcriptions", f"{self.base_url}/organization/usage/audio_transcriptions"),
            ("vector_stores", f"{self.base_url}/organization/usage/vector_stores"),
            (
                "code_interpreter_sessions",
                f"{self.base_url}/organization/usage/code_interpreter_sessions",
            ),
        ]
        api_errors = []
        pages = []

        for label, url in usage_paths:
            params = self._usage_query_params(
                start_time, group_by_model=label in self._USAGE_GROUP_BY_MODEL
            )
            ok, payload, err = self._http_get_json(url, headers, params)
            if ok:
                if payload.get("data"):
                    pages.append(payload)
                continue
            if err:
                api_errors.append({**err, "endpoint": label})

        if pages:
            return self._merge_org_bucket_pages(pages)

        last = api_errors[-1] if api_errors else {}
        last_message = last.get("message") or "OpenAI usage API unavailable"
        if "api.usage.read" in last_message.lower():
            message = (
                "OpenAI rejected usage access: missing api.usage.read scope. "
                "Create an Organization Admin API key with Usage read permission and "
                "save it in the Admin API Key field (standard project keys cannot read org usage)."
            )
        elif not admin_configured:
            message = (
                "Organization usage metrics require an Admin API key. "
                "Add one in connector credentials (Admin API Key field) with Usage read access."
            )
        else:
            message = f"Could not read organization usage: {last_message}"

        recommendation = (
            "In OpenAI Platform → Settings → Organization → Admin keys, create an Admin key "
            "with Usage read scope. Paste it into Admin API Key, set Organization ID (org-…), save, reload."
        )

        return {
            "usage_access_limited": True,
            "message": message,
            "recommendation": recommendation,
            "http_status": last.get("status"),
            "api_errors": api_errors,
            "organization_id_configured": bool(org_id),
            "admin_key_configured": admin_configured,
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

    def _is_org_bucket_payload(self, usage_data: Dict) -> bool:
        if usage_data.get("object") != "page":
            return False
        buckets = usage_data.get("data") or []
        return (
            bool(buckets) and isinstance(buckets[0], dict) and buckets[0].get("object") == "bucket"
        )

    def _flatten_org_buckets(self, payload: Dict) -> list:
        """Normalize OpenAI organization usage/costs page payloads into flat rows."""
        rows = []
        for bucket in payload.get("data") or []:
            if not isinstance(bucket, dict):
                continue
            ts = bucket.get("start_time") or bucket.get("end_time")
            date_str = ""
            if isinstance(ts, (int, float)) and ts > 0:
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            for result in bucket.get("results") or []:
                if not isinstance(result, dict):
                    continue
                row = self._usage_result_to_row(result, date_str)
                if row:
                    rows.append(row)
        return rows

    _NON_MODEL_KEYS = frozenset({"costs", "unknown", ""})

    @classmethod
    def _is_usage_model(cls, model: str) -> bool:
        name = (model or "").strip()
        if not name or name in cls._NON_MODEL_KEYS:
            return False
        if name.startswith("organization."):
            return False
        return True

    def _usage_result_to_row(self, result: Dict, date_str: str) -> Optional[Dict]:
        """Normalize any organization usage/cost result into a flat metrics row."""
        obj_type = result.get("object") or ""
        if obj_type == "organization.costs.result":
            amount = (result.get("amount") or {}).get("value") or 0
            return {
                "date": date_str,
                "model": result.get("line_item") or "costs",
                "requests": 0,
                "context_tokens": 0,
                "generated_tokens": 0,
                "tokens": 0,
                "cost": float(amount or 0),
                "is_cost_row": True,
            }

        if obj_type == "organization.usage.images.result":
            images = int(result.get("images") or 0)
            requests = int(result.get("num_model_requests") or 0)
            model = (result.get("model") or "").strip() or "image_generation"
            return {
                "date": date_str,
                "model": model,
                "requests": requests,
                "context_tokens": 0,
                "generated_tokens": images,
                "tokens": images,
                "cost": float(result.get("cost") or 0),
            }

        if obj_type == "organization.usage.vector_stores.result":
            usage_bytes = int(result.get("usage_bytes") or 0)
            if usage_bytes <= 0:
                return None
            return {
                "date": date_str,
                "model": "vector_stores",
                "requests": 0,
                "context_tokens": usage_bytes,
                "generated_tokens": 0,
                "tokens": usage_bytes,
                "cost": float(result.get("cost") or 0),
            }

        if obj_type == "organization.usage.code_interpreter_sessions.result":
            sessions = int(result.get("num_sessions") or 0)
            if sessions <= 0:
                return None
            return {
                "date": date_str,
                "model": "code_interpreter",
                "requests": sessions,
                "context_tokens": 0,
                "generated_tokens": 0,
                "tokens": 0,
                "cost": float(result.get("cost") or 0),
            }

        input_tokens = int(result.get("input_tokens") or 0)
        output_tokens = int(result.get("output_tokens") or 0)
        input_audio = int(result.get("input_audio_tokens") or 0)
        output_audio = int(result.get("output_audio_tokens") or 0)
        context_tokens = input_tokens + input_audio
        generated_tokens = output_tokens + output_audio
        requests = int(result.get("num_model_requests") or result.get("num_sessions") or 0)
        tokens = context_tokens + generated_tokens
        model = (result.get("model") or "").strip() or "unknown"
        if tokens == 0 and requests == 0 and float(result.get("cost") or 0) == 0:
            return None
        return {
            "date": date_str,
            "model": model,
            "requests": requests,
            "context_tokens": context_tokens,
            "generated_tokens": generated_tokens,
            "tokens": tokens,
            "cost": float(result.get("cost") or 0),
        }

    def _fetch_org_costs(self, start_time: int) -> float:
        headers = self._api_headers(for_usage=True)
        try:
            response = self._make_request(
                "GET",
                f"{self.base_url}/organization/costs",
                headers=headers,
                params={"start_time": start_time, "limit": 31, "bucket_width": "1d"},
            )
            rows = self._flatten_org_buckets(response.json())
            return round(sum(row.get("cost", 0) for row in rows), 2)
        except Exception as exc:
            logger.info("OpenAI organization costs endpoint failed: %s", exc)
            return 0.0

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
            org_cost = 0.0
            if usage_data.get("_account_scope") == "organization":
                now = datetime.now()
                start_time = int(
                    now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
                )
                org_cost = self._fetch_org_costs(start_time)
            usage_analysis = self._process_usage_data(usage_data, org_cost_override=org_cost)
            result.update(usage_analysis)
            if usage_data.get("_account_scope") == "organization":
                result["account_type"] = "organization"
                usage = result.get("usage_this_month") or {}
                if (
                    usage.get("total_tokens", 0) == 0
                    and usage.get("total_requests", 0) == 0
                    and usage.get("estimated_cost", 0) == 0
                ):
                    result["usage_notice"] = (
                        f"Organization API connected for {result.get('period', 'this month')}, "
                        "but no usage was returned. Confirm the Admin key belongs to this org "
                        "and that API activity exists for the selected period."
                    )
        else:
            if usage_data.get("usage_access_limited"):
                result["account_type"] = "organization_limited"
                result["status"] = "usage_unavailable"
                result["usage_notice"] = usage_data.get(
                    "message", "Organization usage data unavailable with current credentials"
                )
                result["recommendation"] = usage_data.get("recommendation", "")
                if usage_data.get("organization_id_configured"):
                    result["organization_id"] = (
                        self.credentials.get("openai_org_id") or ""
                    ).strip()
                if usage_data.get("api_errors"):
                    result["api_errors"] = usage_data.get("api_errors")
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

    def _process_usage_data(self, usage_data: Dict, org_cost_override: float = 0.0) -> Dict:
        """Process raw usage data into metrics (legacy billing rows or org bucket pages)."""
        total_tokens = 0
        total_requests = 0
        total_cost = 0.0
        context_tokens_total = 0
        generated_tokens_total = 0
        models_used = set()
        daily_usage = []
        model_breakdown = {}
        raw_rows = []

        if self._is_org_bucket_payload(usage_data):
            raw_rows = self._flatten_org_buckets(usage_data)
        else:
            for item in usage_data.get("data", []):
                context_tokens = item.get("n_context_tokens_total", 0)
                generated_tokens = item.get("n_generated_tokens_total", 0)
                raw_rows.append(
                    {
                        "date": item.get("timestamp", item.get("date", "")),
                        "model": item.get("snapshot_id", item.get("model", "unknown")),
                        "requests": item.get("n_requests", 1),
                        "context_tokens": context_tokens,
                        "generated_tokens": generated_tokens,
                        "tokens": context_tokens + generated_tokens,
                        "cost": item.get("cost", 0.0),
                    }
                )

        for row in raw_rows:
            item_tokens = int(row.get("tokens") or 0)
            context_tokens = int(row.get("context_tokens") or 0)
            generated_tokens = int(row.get("generated_tokens") or 0)
            requests = int(row.get("requests") or 0)
            cost = float(row.get("cost") or 0)
            model = row.get("model") or "unknown"

            total_tokens += item_tokens
            context_tokens_total += context_tokens
            generated_tokens_total += generated_tokens
            total_requests += requests
            total_cost += cost
            if self._is_usage_model(model) and not row.get("is_cost_row"):
                models_used.add(model)

            if row.get("is_cost_row"):
                model = model or "costs"

            # Usage API returns ungrouped rows without a model name — keep totals only.
            if model == "unknown" and not row.get("is_cost_row"):
                if row.get("date"):
                    daily_usage.append(
                        {
                            "date": row["date"],
                            "tokens": item_tokens,
                            "requests": requests,
                            "cost": cost,
                            "model": model,
                        }
                    )
                continue

            if model not in model_breakdown:
                model_breakdown[model] = {"requests": 0, "tokens": 0, "cost": 0.0}
            model_breakdown[model]["requests"] += requests
            model_breakdown[model]["tokens"] += item_tokens
            model_breakdown[model]["cost"] += cost

            if row.get("date"):
                daily_usage.append(
                    {
                        "date": row["date"],
                        "tokens": item_tokens,
                        "requests": requests,
                        "cost": cost,
                        "model": model,
                    }
                )

        if org_cost_override > 0:
            total_cost = org_cost_override
            known_models = {
                name: stats
                for name, stats in model_breakdown.items()
                if self._is_usage_model(name)
            }
            known_tokens = sum(stats.get("tokens", 0) for stats in known_models.values())
            if known_tokens > 0:
                for name, stats in known_models.items():
                    share = stats.get("tokens", 0) / known_tokens
                    model_breakdown[name]["cost"] = round(org_cost_override * share, 4)
            elif "costs" in model_breakdown:
                model_breakdown["costs"]["cost"] = org_cost_override

        # Calculate efficiency metrics
        avg_tokens_per_request = (
            round(total_tokens / total_requests, 2) if total_requests > 0 else 0
        )
        cost_per_thousand_tokens = (
            round((total_cost / total_tokens) * 1000, 4) if total_tokens > 0 else 0
        )
        cost_per_request = round(total_cost / total_requests, 4) if total_requests > 0 else 0

        models_from_usage = sorted(
            [
                name
                for name, stats in model_breakdown.items()
                if self._is_usage_model(name)
                and (stats.get("requests", 0) > 0 or stats.get("tokens", 0) > 0)
            ],
            key=lambda name: (model_breakdown[name]["tokens"], model_breakdown[name]["requests"]),
            reverse=True,
        )

        return {
            "usage_this_month": {
                "total_tokens": total_tokens,
                "tokens_used": total_tokens,  # Dashboard compatibility
                "context_tokens": context_tokens_total,
                "generated_tokens": generated_tokens_total,
                "total_requests": total_requests,
                "requests_made": total_requests,  # Dashboard compatibility
                "estimated_cost": round(total_cost, 2),
                "avg_tokens_per_request": avg_tokens_per_request,
                "cost_per_thousand_tokens": cost_per_thousand_tokens,
                "cost_per_request": cost_per_request,
            },
            "models_used": models_from_usage
            if models_from_usage
            else (list(models_used) if models_used else ["No usage this period"]),
            "model_breakdown": model_breakdown,
            "daily_usage": daily_usage[-7:],  # Last 7 days
            "raw_data_points": len(raw_rows),
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
            if metrics.get("usage_notice"):
                insights["alerts"].append(f"ℹ️ {metrics['usage_notice']}")

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

        # Model efficiency recommendations (ignore ungrouped "unknown" bucket)
        model_breakdown = metrics.get("model_breakdown", {})
        known_breakdown = {
            name: stats
            for name, stats in model_breakdown.items()
            if self._is_usage_model(name) and (stats.get("cost", 0) > 0 or stats.get("tokens", 0) > 0)
        }
        if known_breakdown and total_cost > 0:
            most_expensive = max(known_breakdown.items(), key=lambda x: x[1]["cost"], default=None)
            if (
                most_expensive
                and most_expensive[1]["cost"] > 0
                and most_expensive[1]["cost"] > total_cost * 0.5
            ):
                insights["optimization_recommendations"].append(
                    f"Model '{most_expensive[0]}' accounts for >50% of costs - review usage"
                )
        elif model_breakdown.get("unknown", {}).get("tokens", 0) > 0 and not known_breakdown:
            insights["optimization_recommendations"].append(
                "Model names were not returned by the usage API — reload metrics after updating the connector"
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
