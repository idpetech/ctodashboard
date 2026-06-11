"""API route module — see routes.api.register_routes."""

import os
from datetime import datetime

from flask import jsonify, redirect, render_template, request, send_from_directory

from routes.api.deps import (
    _track_product_event,
    logger,
)


def register_pages_routes(app):
    """Register pages routes."""

    @app.route("/r/<share_token>")
    def public_shared_report(share_token):
        """Public read-only executive report (no login)."""
        try:
            from services.report_share_service import (
                build_report_template_context,
                get_share_report,
            )
            from services.security.secure_database import secure_db

            report, err = get_share_report(
                secure_db,
                share_token,
                user_agent=request.headers.get("User-Agent", ""),
                record_view=True,
            )
            if err:
                return render_template("report_share.html", error=err), 404

            ctx = build_report_template_context(report)
            return render_template("report_share.html", error=None, **ctx)
        except Exception:
            logger.exception("Public report view failed")
            return render_template(
                "report_share.html",
                error="Unable to load this report right now.",
            ), 500

    @app.route("/dashboard")
    def dashboard():
        """Main dashboard page - moved from root to /dashboard"""
        from flask import session

        if session.get("user_email"):
            _track_product_event(
                "dashboard_view",
                metadata={"path": "/dashboard"},
                user_id=session.get("user_email"),
            )
        return render_template("dashboard.html")

    @app.route("/workspace/<workspace_id>/settings")
    def workspace_settings_page(workspace_id):
        """Workspace settings — assignments, connectors, CTOLens schedule."""
        return render_template("workspace_settings.html")

    @app.route("/settings")
    @app.route("/workspace/settings")
    def workspace_settings_redirect():
        """Redirect to default workspace settings for Railway deployment"""
        return redirect("/workspace/default_workspace/settings")

    @app.route("/auth-test")
    def auth_test():
        """Authentication system test page"""

        return send_from_directory("static", "auth_test.html")

    @app.route("/health")
    def health_check():
        """Health check endpoint showing service configuration status"""
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "github": "configured" if os.getenv("GITHUB_TOKEN") else "not_configured",
                    "jira": "configured" if os.getenv("JIRA_TOKEN") else "not_configured",
                    "aws": "configured" if os.getenv("AWS_ACCESS_KEY_ID") else "not_configured",
                    "railway": "configured" if os.getenv("RAILWAY_TOKEN") else "not_configured",
                    "openai": "configured" if os.getenv("OPENAI_API_KEY") else "not_configured",
                },
            }
        )
