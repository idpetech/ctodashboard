"""
OpenAI credential validation
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class OpenAIValidator:
    """Handles OpenAI credential validation"""

    @staticmethod
    def validate_credentials(credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Test OpenAI credentials by calling the API

        Args:
            credentials: Dictionary containing 'openai_api_key'

        Returns:
            Validation result with success/error information
        """
        api_key = credentials.get("openai_api_key")

        if not api_key:
            return {"valid": False, "error": "OpenAI API key is required"}

        try:
            import requests

            # Test credentials by calling OpenAI API
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            # Use the models endpoint as a simple test (doesn't consume tokens)
            response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)

            if response.status_code == 200:
                models_data = response.json()
                available_models = [model["id"] for model in models_data.get("data", [])[:5]]
                org_from_header = response.headers.get("openai-organization")
                org_from_creds = (credentials.get("openai_org_id") or "").strip()

                return {
                    "valid": True,
                    "organization": org_from_header or org_from_creds or None,
                    "organization_from_header": org_from_header,
                    "models_available": len(models_data.get("data", [])),
                    "sample_models": available_models,
                    "usage_note": (
                        "Organization usage metrics require an Admin API key in connector settings."
                        if not (credentials.get("openai_admin_api_key") or "").strip()
                        else None
                    ),
                }
            elif response.status_code == 401:
                return {"valid": False, "error": "Invalid OpenAI API key or expired"}
            elif response.status_code == 403:
                return {"valid": False, "error": "OpenAI API key lacks required permissions"}
            elif response.status_code == 429:
                return {"valid": False, "error": "OpenAI API rate limit exceeded - try again later"}
            else:
                return {"valid": False, "error": f"OpenAI API error: {response.status_code}"}

        except requests.exceptions.ConnectionError:
            return {
                "valid": False,
                "error": "Cannot connect to OpenAI API - check internet connection",
            }
        except requests.exceptions.Timeout:
            return {"valid": False, "error": "OpenAI API request timed out"}
        except Exception as e:
            logger.error(f"OpenAI validation error: {e}", exc_info=True)
            return {"valid": False, "error": f"OpenAI connection failed: {str(e)}"}

    @staticmethod
    def get_required_fields() -> list[str]:
        """Get required credential fields for OpenAI"""
        return ["openai_api_key"]
