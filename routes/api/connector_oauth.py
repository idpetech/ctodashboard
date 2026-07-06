"""OAuth install/callback routes for GitHub App and Jira 3LO connectors."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlencode

from flask import jsonify, redirect, request

from routes.api.deps import (
    get_require_web_auth,
    get_require_workspace_access,
    get_workspace_service,
)
from services.connectors.github_app_auth import (
    get_installation,
    github_app_configured,
    github_app_slug,
    installation_account_login,
    validate_installation_token,
)
from services.connectors.jira_oauth import (
    build_authorize_url,
    exchange_code_for_tokens,
    jira_oauth_configured,
    list_accessible_resources,
    pick_jira_resource,
    token_expiry_epoch,
    validate_oauth_connection,
)
from services.connectors.oauth_flags import (
    connector_oauth_ui_enabled,
    github_app_connector_enabled,
    jira_oauth_connector_enabled,
    oauth_capabilities,
)
from services.connectors.oauth_state import OAuthStateError, build_oauth_state, parse_oauth_state
from services.security.db_credentials import secure_db

logger = logging.getLogger(__name__)


def _app_base_url() -> str:
    configured = (
        (os.getenv("APP_BASE_URL") or os.getenv("PUBLIC_APP_URL") or "").strip().rstrip("/")
    )
    if configured:
        return configured
    return request.url_root.rstrip("/")


def _oauth_return_redirect(
    workspace_id: str,
    *,
    connector: str,
    status: str,
    message: str = "",
    assignment_id: str = "",
    return_to: str = "dashboard",
) -> str:
    params = {"oauth": connector, "oauth_status": status, "workspace": workspace_id}
    if assignment_id:
        params["assignment_id"] = assignment_id
    if message:
        params["oauth_message"] = message[:200]
    if return_to == "settings":
        return f"/workspace/{workspace_id}/settings?{urlencode(params)}"
    return f"/dashboard?{urlencode(params)}"


def _settings_redirect(workspace_id: str, *, connector: str, status: str, message: str = "") -> str:
    return _oauth_return_redirect(
        workspace_id,
        connector=connector,
        status=status,
        message=message,
        return_to="settings",
    )


def register_connector_oauth_routes(app):
    """Register connector OAuth routes (feature-flagged)."""

    @app.route("/api/connectors/oauth/capabilities", methods=["GET"])
    def connector_oauth_capabilities():
        return jsonify(oauth_capabilities())

    @app.route("/api/workspaces/<workspace_id>/oauth/github/start", methods=["GET"])
    @get_require_workspace_access()
    def api_github_oauth_start(workspace_id):
        if not github_app_connector_enabled() or not connector_oauth_ui_enabled():
            return jsonify({"error": "GitHub App connector OAuth is disabled"}), 403
        if not github_app_configured():
            return jsonify({"error": "GitHub App is not configured on this deployment"}), 503

        assignment_id = request.args.get("assignment_id", "").strip()
        if not assignment_id:
            return jsonify({"error": "assignment_id is required"}), 400

        slug = github_app_slug()
        if not slug:
            return jsonify({"error": "GITHUB_APP_SLUG is not configured"}), 503

        state = build_oauth_state(
            connector="github",
            workspace_id=workspace_id,
            assignment_id=assignment_id,
        )
        install_url = (
            f"https://github.com/apps/{slug}/installations/new?{urlencode({'state': state})}"
        )
        if request.args.get("redirect", "true").lower() == "false":
            return jsonify({"install_url": install_url})
        return redirect(install_url)

    @app.route("/oauth/github/setup", methods=["GET"])
    @get_require_web_auth()
    def github_oauth_setup():
        if not github_app_connector_enabled():
            return jsonify({"error": "GitHub App connector OAuth is disabled"}), 403

        installation_id = request.args.get("installation_id", "").strip()
        state = request.args.get("state", "").strip()
        setup_action = request.args.get("setup_action", "").strip()
        if not installation_id:
            logger.warning(
                "GitHub setup hit without installation_id (setup_action=%s, has_state=%s, query=%s)",
                setup_action or "none",
                bool(state),
                request.query_string.decode("utf-8", errors="replace"),
            )
            message = (
                "GitHub did not return an installation ID. Do not open the Setup URL directly "
                "from GitHub settings — click Connect GitHub App in CTOLens, finish install on "
                "GitHub, and let GitHub redirect you back. If you installed before setting the "
                "Setup URL, uninstall the app and connect again from CTOLens."
            )
            return redirect(
                _oauth_return_redirect(
                    "default_workspace",
                    connector="github",
                    status="error",
                    message=message,
                )
            )

        try:
            ctx = parse_oauth_state(state, expected_connector="github")
            installation = get_installation(installation_id)
            account_login = installation_account_login(installation)
        except OAuthStateError as exc:
            return redirect(
                _oauth_return_redirect(
                    "default_workspace",
                    connector="github",
                    status="error",
                    message=str(exc),
                )
            )
        except Exception as exc:
            logger.exception("GitHub setup failed")
            return redirect(
                _oauth_return_redirect(
                    "default_workspace",
                    connector="github",
                    status="error",
                    message=f"GitHub setup failed: {exc}",
                )
            )

        workspace_id = ctx["workspace_id"]
        assignment_id = ctx["assignment_id"]
        return_to = ctx.get("return_to") or "dashboard"
        credentials = {
            "auth_method": "github_app",
            "github_installation_id": str(installation_id),
            "github_org": account_login,
            "github_account_type": (installation.get("account") or {}).get("type"),
        }

        existing = secure_db.get_assignment_credentials(workspace_id, assignment_id, "github") or {}
        if existing.get("github_repos"):
            credentials["github_repos"] = existing["github_repos"]

        result = get_workspace_service().update_assignment_auth(
            workspace_id, assignment_id, "github", credentials
        )
        if not result.get("success"):
            return redirect(
                _oauth_return_redirect(
                    workspace_id,
                    connector="github",
                    status="error",
                    message=result.get("error", "Failed to save GitHub installation"),
                    assignment_id=assignment_id,
                    return_to=return_to,
                )
            )

        validation = validate_installation_token(installation_id)
        if not validation.get("valid"):
            return redirect(
                _oauth_return_redirect(
                    workspace_id,
                    connector="github",
                    status="warning",
                    message=validation.get("error", "Installed but validation failed"),
                    assignment_id=assignment_id,
                    return_to=return_to,
                )
            )

        return redirect(
            _oauth_return_redirect(
                workspace_id,
                connector="github",
                status="success",
                message=f"GitHub connected for {account_login}. Add repositories to monitor.",
                assignment_id=assignment_id,
                return_to=return_to,
            )
        )

    @app.route("/api/workspaces/<workspace_id>/oauth/jira/start", methods=["GET"])
    @get_require_workspace_access()
    def api_jira_oauth_start(workspace_id):
        if not jira_oauth_connector_enabled() or not connector_oauth_ui_enabled():
            return jsonify({"error": "Jira OAuth connector is disabled"}), 403
        if not jira_oauth_configured():
            return jsonify({"error": "Jira OAuth is not configured on this deployment"}), 503

        assignment_id = request.args.get("assignment_id", "").strip()
        if not assignment_id:
            return jsonify({"error": "assignment_id is required"}), 400

        state = build_oauth_state(
            connector="jira",
            workspace_id=workspace_id,
            assignment_id=assignment_id,
        )
        redirect_uri = f"{_app_base_url()}/oauth/jira/callback"
        authorize_url = build_authorize_url(redirect_uri=redirect_uri, state=state)
        if request.args.get("redirect", "true").lower() == "false":
            return jsonify({"authorize_url": authorize_url})
        return redirect(authorize_url)

    @app.route("/oauth/jira/callback", methods=["GET"])
    @get_require_web_auth()
    def jira_oauth_callback():
        if not jira_oauth_connector_enabled():
            return jsonify({"error": "Jira OAuth connector is disabled"}), 403

        state = request.args.get("state", "").strip()
        ctx = {"workspace_id": "default_workspace", "assignment_id": "", "return_to": "dashboard"}
        try:
            if state:
                ctx = parse_oauth_state(state, expected_connector="jira")
        except OAuthStateError:
            pass

        workspace_id = ctx["workspace_id"]
        assignment_id = ctx["assignment_id"]
        return_to = ctx.get("return_to") or "dashboard"

        def jira_return(*, status: str, message: str = "") -> str:
            return _oauth_return_redirect(
                workspace_id,
                connector="jira",
                status=status,
                message=message,
                assignment_id=assignment_id,
                return_to=return_to,
            )

        error = request.args.get("error", "").strip()
        if error:
            return redirect(
                jira_return(status="error", message=f"Jira authorization denied: {error}")
            )

        code = request.args.get("code", "").strip()
        if not code:
            return redirect(
                jira_return(
                    status="error",
                    message="Jira did not return an authorization code. Start again from Connect Jira in CTOLens.",
                )
            )

        try:
            ctx = parse_oauth_state(state, expected_connector="jira")
            workspace_id = ctx["workspace_id"]
            assignment_id = ctx["assignment_id"]
            return_to = ctx.get("return_to") or "dashboard"
            redirect_uri = f"{_app_base_url()}/oauth/jira/callback"
            token_payload = exchange_code_for_tokens(code=code, redirect_uri=redirect_uri)
            access_token = token_payload.get("access_token")
            refresh_token = token_payload.get("refresh_token")
            if not access_token or not refresh_token:
                raise ValueError("Jira token response missing access or refresh token")

            resources = list_accessible_resources(access_token)
            resource = pick_jira_resource(resources)
            cloud_id = resource.get("id")
            site_url = resource.get("url")
            if not cloud_id or not site_url:
                raise ValueError("Jira accessible resource missing id or url")
        except OAuthStateError as exc:
            return redirect(
                _oauth_return_redirect(
                    workspace_id,
                    connector="jira",
                    status="error",
                    message=str(exc),
                    assignment_id=assignment_id,
                    return_to=return_to,
                )
            )
        except Exception as exc:
            logger.exception("Jira OAuth callback failed")
            return redirect(
                _oauth_return_redirect(
                    workspace_id,
                    connector="jira",
                    status="error",
                    message=f"Jira OAuth failed: {exc}",
                    assignment_id=assignment_id,
                    return_to=return_to,
                )
            )

        credentials = {
            "auth_method": "jira_oauth",
            "jira_refresh_token": refresh_token,
            "jira_access_token": access_token,
            "jira_token_expires_at": str(token_expiry_epoch(token_payload)),
            "jira_cloud_id": cloud_id,
            "jira_url": site_url,
        }

        existing = secure_db.get_assignment_credentials(workspace_id, assignment_id, "jira") or {}
        if existing.get("jira_projects"):
            credentials["jira_projects"] = existing["jira_projects"]

        result = get_workspace_service().update_assignment_auth(
            workspace_id, assignment_id, "jira", credentials
        )
        if not result.get("success"):
            return redirect(
                _oauth_return_redirect(
                    workspace_id,
                    connector="jira",
                    status="error",
                    message=result.get("error", "Failed to save Jira OAuth credentials"),
                    assignment_id=assignment_id,
                    return_to=return_to,
                )
            )

        validation = validate_oauth_connection(credentials)
        status = "success" if validation.get("valid") else "warning"
        message = (
            f"Jira connected to {site_url}. Add project keys to monitor."
            if validation.get("valid")
            else validation.get("error", "Connected but validation failed")
        )
        return redirect(
            _oauth_return_redirect(
                workspace_id,
                connector="jira",
                status=status,
                message=message,
                assignment_id=assignment_id,
                return_to=return_to,
            )
        )

    @app.route(
        "/api/workspaces/<workspace_id>/credentials/<connector_type>/oauth", methods=["DELETE"]
    )
    @get_require_workspace_access()
    def disconnect_connector_oauth(workspace_id, connector_type):
        """Clear OAuth connector credentials for an assignment."""
        if connector_type not in ("github", "jira"):
            return jsonify({"error": "OAuth disconnect supported for github and jira only"}), 400

        data = request.get_json() or {}
        assignment_id = (data.get("assignment_id") or "").strip()
        if not assignment_id:
            return jsonify({"error": "assignment_id is required"}), 400

        result = get_workspace_service().clear_assignment_auth(
            workspace_id, assignment_id, connector_type
        )
        if result.get("success"):
            return jsonify({"success": True, "message": f"{connector_type} OAuth disconnected"})
        return jsonify(result), 400
