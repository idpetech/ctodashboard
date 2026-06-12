"""API route module — see routes.api.register_routes."""

import os

from flask import jsonify, request

from services.stripe_billing_service import is_billing_enabled


def register_system_routes(app):
    """Register system routes."""

    @app.route("/api/feature-flags")
    def get_feature_flags():
        """Get current feature flag status"""
        return jsonify(
            {
                "multi_tenancy": os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true",
                "workstream_management": os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower()
                == "true",
                "service_config_ui": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower()
                == "true",
                "advanced_billing": is_billing_enabled(),
                "database_storage": os.getenv("ENABLE_DATABASE", "false").lower() == "true",
                "portfolio_dashboard": os.getenv("ENABLE_PORTFOLIO_DASHBOARD", "false").lower()
                == "true",
                "portfolios": os.getenv("ENABLE_PORTFOLIOS", "false").lower() == "true",
                "csv_import": os.getenv("ENABLE_CSV_IMPORT", "false").lower() == "true",
                "attention_engine": os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() == "true",
                "ctolens_briefing": os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true",
                "signal_engine": os.getenv("ENABLE_SIGNAL_ENGINE", "false").lower() == "true",
                "recommendation_engine": os.getenv("ENABLE_RECOMMENDATION_ENGINE", "false").lower()
                == "true",
                "ai_executive_briefing": os.getenv("ENABLE_AI_EXECUTIVE_BRIEFING", "false").lower()
                == "true",
                "ctolens_scheduled_enrichment": os.getenv(
                    "ENABLE_CTOLENS_SCHEDULED_ENRICHMENT", "false"
                ).lower()
                == "true",
                "product_analytics": os.getenv("ENABLE_PRODUCT_ANALYTICS", "false").lower()
                == "true",
            }
        )

    @app.route("/api/services/status")
    def get_services_status():
        """Get status of all services"""
        return jsonify(
            {
                "service_manager": "available",
                "workstream_service": "available",
                "service_config_service": "available",
                "tenant_service": "available",
            }
        )

    @app.route("/api/workstreams", methods=["GET", "POST"])
    def workstreams():
        """Workstream management endpoint"""
        if not os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true":
            return jsonify({"error": "Workstream management is disabled"}), 403

        if request.method == "GET":
            return jsonify({"workstreams": []})
        elif request.method == "POST":
            return jsonify({"error": "Workstream creation not implemented"}), 501

    @app.route("/api/service-configs", methods=["GET", "POST"])
    def service_configs():
        """Service configuration management endpoint"""
        if not os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true":
            return jsonify({"error": "Service configuration UI is disabled"}), 403

        if request.method == "GET":
            return jsonify({"service_configs": []})
        elif request.method == "POST":
            return jsonify({"error": "Service configuration creation not implemented"}), 501
