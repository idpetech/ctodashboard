"""Modular API route registration."""

from routes.api.analytics import register_analytics_routes
from routes.api.assignments import register_assignments_routes
from routes.api.audit import register_audit_routes
from routes.api.auth_billing import register_auth_billing_routes
from routes.api.briefing import register_briefing_routes
from routes.api.chatbot import register_chatbot_routes
from routes.api.import_export import register_import_export_routes
from routes.api.pages import register_pages_routes
from routes.api.portfolios import register_portfolios_routes
from routes.api.system import register_system_routes
from routes.api.workspaces import register_workspaces_routes


def register_routes(app):
    """Register all API and dashboard routes with the Flask app."""
    register_pages_routes(app)
    register_system_routes(app)
    register_assignments_routes(app)
    register_chatbot_routes(app)
    register_auth_billing_routes(app)
    register_workspaces_routes(app)
    register_portfolios_routes(app)
    register_briefing_routes(app)
    register_audit_routes(app)
    register_import_export_routes(app)
    register_analytics_routes(app)
