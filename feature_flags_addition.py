# Feature Flags - Phase 1: Foundation
# All flags disabled by default to maintain existing functionality
FEATURE_FLAGS = {
    "multi_tenancy": os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true",
    "workstream_management": os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true",
    "service_config_ui": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true",
    "advanced_billing": os.getenv("ENABLE_BILLING", "false").lower() == "true",
    "database_storage": os.getenv("ENABLE_DATABASE", "false").lower() == "true"
}

@app.route("/api/feature-flags")
def get_feature_flags():
    """Get current feature flags status"""
    return jsonify({
        "feature_flags": FEATURE_FLAGS,
        "status": "read_only",
        "note": "Feature flags are controlled via environment variables",
        "environment_variables": {
            "ENABLE_MULTI_TENANCY": os.getenv("ENABLE_MULTI_TENANCY", "false"),
            "ENABLE_WORKSTREAM_MGMT": os.getenv("ENABLE_WORKSTREAM_MGMT", "false"),
            "ENABLE_SERVICE_CONFIG_UI": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false"),
            "ENABLE_BILLING": os.getenv("ENABLE_BILLING", "false"),
            "ENABLE_DATABASE": os.getenv("ENABLE_DATABASE", "false")
        }
    })
