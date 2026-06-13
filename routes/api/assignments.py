"""API route module — see routes.api.register_routes."""

import os

from flask import jsonify, request

from routes.api.deps import (
    aws_metrics,
    collect_assignment_metrics,
    deny_unless_workspace_access,
    get_current_user,
    get_require_auth,
    get_user_service,
    get_workspace_service,
    github_metrics,
    logger,
)
from services.assignment_metrics_config import (
    github_metrics_config as build_github_metrics_config,
)
from services.assignment_metrics_config import (
    jira_metrics_config as build_jira_metrics_config,
)
from services.embedded.jira_metrics import EmbeddedJiraMetrics
from services.portfolio_service import build_portfolio_overview


def register_assignments_routes(app):
    """Register assignments routes."""

    @app.route("/api/assignments")
    @get_require_auth()
    def get_assignments():
        """Get assignments for the authenticated user's workspaces only."""
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Authentication required"}), 401

        workspace_id = request.args.get("workspace_id")
        user_workspace_ids = (
            get_user_service().get_user_workspaces(current_user.get("email")).get("workspaces", [])
        )

        if workspace_id:
            if workspace_id not in user_workspace_ids:
                return jsonify({"error": "Access denied to this workspace"}), 403
            user_workspace_ids = [workspace_id]

        all_assignments = []
        try:
            for ws_id in user_workspace_ids:
                result = get_workspace_service().get_workspace_assignments(ws_id)
                if "assignments" in result:
                    for a in result["assignments"]:
                        a["workspace_id"] = ws_id
                    all_assignments.extend(result["assignments"])
        except Exception as e:
            return jsonify({"error": f"Failed to load assignments: {str(e)}"}), 500

        return jsonify(all_assignments)

    @app.route("/api/portfolio/summary")
    @get_require_auth()
    def get_portfolio_summary():
        """Portfolio Dashboard MVP — on-demand portfolio intelligence.

        Feature-flagged via ENABLE_PORTFOLIO_DASHBOARD (default off). Scoped to
        the authenticated user's workspace(s); pass ?workspace_id= to narrow.
        """
        if not os.getenv("ENABLE_PORTFOLIO_DASHBOARD", "false").lower() == "true":
            return jsonify({"error": "Portfolio dashboard is disabled"}), 403

        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Authentication required"}), 401

        workspace_id = request.args.get("workspace_id")
        user_workspace_ids = (
            get_user_service().get_user_workspaces(current_user.get("email")).get("workspaces", [])
        )

        if workspace_id:
            if workspace_id not in user_workspace_ids:
                return jsonify({"error": "Access denied to this workspace"}), 403
            scope_ids = [workspace_id]
        else:
            scope_ids = user_workspace_ids

        all_assignments = []
        try:
            for ws_id in scope_ids:
                result = get_workspace_service().get_workspace_assignments(ws_id)
                if "assignments" in result:
                    all_assignments.extend(result["assignments"])
        except Exception as e:
            return jsonify({"error": f"Failed to load assignments: {str(e)}"}), 500

        portfolio_id = (request.args.get("portfolio_id") or "").strip()
        if portfolio_id:
            from services.portfolio_scope_service import (
                filter_assignments_by_portfolio,
                is_portfolios_enabled,
            )

            if not is_portfolios_enabled():
                return jsonify({"error": "Portfolios are disabled"}), 403
            if len(scope_ids) != 1:
                return jsonify({"error": "portfolio_id requires a single workspace_id"}), 400
            all_assignments = filter_assignments_by_portfolio(all_assignments, portfolio_id)

        try:
            overview = build_portfolio_overview(all_assignments)
            if len(scope_ids) == 1:
                from services.attention_engine import compute_score_trends
                from services.security.secure_database import secure_db

                ws = secure_db.get_workspace(scope_ids[0])
                history = (ws.get("settings") or {}).get("health_score_history") or []
                health = overview.get("health_score") or {}
                comps = health.get("components") or {}
                entry = {
                    "health": health.get("overall_score"),
                    "financial": comps.get("financial"),
                    "connector": comps.get("connector"),
                    "delivery": comps.get("delivery"),
                }
                overview["score_trends"] = compute_score_trends(history, entry)
                if history:
                    overview["score_trends_since"] = history[-1].get("generated_at")
            return jsonify(overview)
        except Exception as e:
            logger.exception("Portfolio overview computation failed")
            return jsonify({"error": f"Failed to build portfolio overview: {str(e)}"}), 500

    @app.route("/api/assignments/<assignment_id>")
    @get_require_auth()
    def get_assignment(assignment_id):
        """Get a specific assignment configuration"""
        workspace_id = request.args.get("workspace_id")

        # If no workspace_id provided, search within user's accessible workspaces
        if not workspace_id:
            current_user = get_current_user()
            if current_user and current_user.get("workspaces"):
                user_workspaces = current_user["workspaces"]

                # Search for assignment in user's workspaces
                found_assignments = []
                for ws_id in user_workspaces:
                    assignment = get_workspace_service().get_assignment(ws_id, assignment_id)
                    if assignment:
                        found_assignments.append({"workspace_id": ws_id, "assignment": assignment})

                if len(found_assignments) == 1:
                    # Found exactly one - return it
                    return jsonify(found_assignments[0]["assignment"])
                elif len(found_assignments) > 1:
                    # Multiple matches within user's workspaces - still ambiguous
                    workspace_ids = [fa["workspace_id"] for fa in found_assignments]
                    return jsonify(
                        {
                            "error": f"Assignment '{assignment_id}' found in multiple of your workspaces: {workspace_ids}. Please specify workspace_id parameter.",
                            "ambiguous_workspaces": workspace_ids,
                        }
                    ), 409
                else:
                    # No matches in user's workspaces
                    return jsonify(
                        {
                            "error": f"Assignment '{assignment_id}' not found in your accessible workspaces"
                        }
                    ), 404

        # Use defensive resolver for workspace context (when workspace_id is provided)
        denied = deny_unless_workspace_access(workspace_id)
        if denied:
            return denied

        result = get_workspace_service().find_assignment(assignment_id, workspace_id)

        if result.get("status") == 200:
            return jsonify(result["assignment"])
        elif result.get("status") == 409:
            return jsonify(
                {
                    "error": result["error"],
                    "ambiguous_workspaces": result.get("ambiguous_workspaces", []),
                }
            ), 409
        else:
            return jsonify(
                {"error": result.get("error", f"Assignment {assignment_id} not found")}
            ), 404

    @app.route("/api/assignments/<assignment_id>", methods=["PUT"])
    @get_require_auth()
    def update_assignment(assignment_id):
        """Update assignment configuration — requires workspace_id query param."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No update data provided"}), 400

        workspace_id = request.args.get("workspace_id")
        if not workspace_id:
            return jsonify(
                {
                    "error": "workspace_id query parameter is required. "
                    "Use PUT /api/workspaces/<workspace_id>/assignments/<assignment_id> instead.",
                }
            ), 400

        current_user = get_current_user()
        user_workspaces = (
            get_user_service().get_user_workspaces(current_user.get("email")).get("workspaces", [])
        )
        if workspace_id not in user_workspaces:
            return jsonify({"error": "Access denied to this workspace"}), 403

        try:
            result = get_workspace_service().update_assignment(workspace_id, assignment_id, data)
            if result.get("success"):
                return jsonify(
                    {
                        "success": True,
                        "message": "Assignment updated successfully",
                        "assignment": result.get("assignment"),
                    }
                )
            else:
                return jsonify({"error": result.get("error", "Update failed")}), 400
        except Exception as e:
            return jsonify({"error": f"Failed to update assignment: {str(e)}"}), 500

    @app.route("/api/assignments/<assignment_id>", methods=["DELETE"])
    @get_require_auth()
    def delete_assignment(assignment_id):
        """Archive assignment — requires workspace_id query param."""
        workspace_id = request.args.get("workspace_id")
        if not workspace_id:
            return jsonify(
                {
                    "error": "workspace_id query parameter is required. "
                    "Use DELETE /api/workspaces/<workspace_id>/assignments/<assignment_id> instead.",
                }
            ), 400

        current_user = get_current_user()
        user_workspaces = (
            get_user_service().get_user_workspaces(current_user.get("email")).get("workspaces", [])
        )
        if workspace_id not in user_workspaces:
            return jsonify({"error": "Access denied to this workspace"}), 403

        try:
            result = get_workspace_service().delete_assignment(workspace_id, assignment_id)
            if result.get("success"):
                return jsonify(
                    {
                        "success": True,
                        "message": result.get("message", f"Assignment '{assignment_id}' deleted"),
                    }
                )
            else:
                return jsonify(
                    {"error": result.get("error", f"Assignment '{assignment_id}' not found")}
                ), 404
        except Exception as e:
            return jsonify({"error": f"Failed to delete assignment: {str(e)}"}), 500

    @app.route("/api/aws-metrics")
    @get_require_auth()
    def get_aws_metrics():
        """Get AWS metrics"""
        try:
            metrics = aws_metrics.get_metrics()
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/github-metrics/<assignment_id>")
    @get_require_auth()
    def get_github_metrics(assignment_id):
        """Get GitHub metrics for specific assignment"""
        try:
            workspace_id = request.args.get("workspace_id")
            if workspace_id:
                denied = deny_unless_workspace_access(workspace_id)
                if denied:
                    return denied
                assignment = get_workspace_service().get_assignment(workspace_id, assignment_id)
            else:
                current_user = get_current_user()
                user_workspace_ids = (
                    get_user_service()
                    .get_user_workspaces(current_user.get("email"))
                    .get("workspaces", [])
                )
                found = None
                for ws_id in user_workspace_ids:
                    assignment = get_workspace_service().get_assignment(ws_id, assignment_id)
                    if assignment:
                        found = {"workspace_id": ws_id, "assignment": assignment}
                        break
                if not found:
                    return jsonify({"error": "Assignment not found"}), 404
                workspace_id = found["workspace_id"]
                assignment = found["assignment"]

            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404

            github_config = assignment.get("metrics_config", {}).get("github", {})
            if not github_config.get("enabled", False):
                return jsonify({"error": "GitHub not enabled for this assignment"}), 400

            gh_cfg = build_github_metrics_config(workspace_id, assignment_id, github_config)
            metrics = github_metrics.get_metrics(gh_cfg)
            return jsonify(metrics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/github-token-status")
    @get_require_auth()
    def check_github_token_status():
        """Check GitHub token validation status"""
        try:
            status = github_metrics.validate_token()
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": str(e), "valid": False}), 500

    @app.route("/api/jira-metrics/<assignment_id>")
    @get_require_auth()
    def get_jira_metrics(assignment_id):
        """Get Jira metrics for specific assignment (Postgres credentials)."""
        try:
            workspace_id = request.args.get("workspace_id")
            if workspace_id:
                assignment = get_workspace_service().get_assignment(workspace_id, assignment_id)
            else:
                result = get_workspace_service().find_assignment(assignment_id)
                if result.get("status") != 200:
                    return jsonify({"error": "Assignment not found"}), 404
                workspace_id = result["workspace_id"]
                assignment = result["assignment"]

            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404

            jira_config = assignment.get("metrics_config", {}).get("jira", {})
            if not jira_config.get("enabled", False):
                return jsonify({"error": "Jira not enabled for this assignment"}), 400

            jira_merged = build_jira_metrics_config(workspace_id, assignment_id, jira_config)
            connector = EmbeddedJiraMetrics(workspace_id=workspace_id, assignment_id=assignment_id)
            return jsonify(connector.get_metrics(jira_merged))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/all-metrics/<assignment_id>")
    @get_require_auth()
    def get_all_metrics(assignment_id):
        """Get all metrics for specific assignment - workspace-only"""
        workspace_id = request.args.get("workspace_id")

        # If no workspace_id provided, search within user's accessible workspaces
        if not workspace_id:
            current_user = get_current_user()
            if current_user and current_user.get("workspaces"):
                user_workspaces = current_user["workspaces"]

                # Search for assignment in user's workspaces
                found_assignments = []
                for ws_id in user_workspaces:
                    assignment = get_workspace_service().get_assignment(ws_id, assignment_id)
                    if assignment:
                        found_assignments.append({"workspace_id": ws_id, "assignment": assignment})

                if len(found_assignments) == 1:
                    # Found exactly one - use its workspace
                    workspace_id = found_assignments[0]["workspace_id"]
                elif len(found_assignments) > 1:
                    # Multiple matches within user's workspaces - still ambiguous
                    workspace_ids = [fa["workspace_id"] for fa in found_assignments]
                    return jsonify(
                        {
                            "error": f"Assignment '{assignment_id}' found in multiple of your workspaces: {workspace_ids}. Please specify workspace_id parameter.",
                            "ambiguous_workspaces": workspace_ids,
                        }
                    ), 409
                else:
                    # No matches in user's workspaces
                    return jsonify(
                        {
                            "error": f"Assignment '{assignment_id}' not found in your accessible workspaces"
                        }
                    ), 404

        try:
            # Use defensive resolver for workspace context
            result = get_workspace_service().find_assignment(assignment_id, workspace_id)

            if result.get("status") != 200:
                if result.get("status") == 409:
                    return jsonify(
                        {
                            "error": result["error"],
                            "ambiguous_workspaces": result.get("ambiguous_workspaces", []),
                        }
                    ), 409
                else:
                    return jsonify(
                        {"error": result.get("error", f"Assignment '{assignment_id}' not found")}
                    ), 404

            workspace_id = result["workspace_id"]
            assignment = result["assignment"]
            return jsonify(collect_assignment_metrics(workspace_id, assignment_id, assignment))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/workspaces/<workspace_id>/assignments/<assignment_id>/metrics")
    @get_require_auth()
    def get_workspace_assignment_metrics(workspace_id, assignment_id):
        """Get metrics for assignment in workspace (Postgres)."""
        try:
            assignment = get_workspace_service().get_assignment(workspace_id, assignment_id)
            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404
            return jsonify(collect_assignment_metrics(workspace_id, assignment_id, assignment))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/assignments/<assignment_id>/cto-insights")
    def get_cto_insights(assignment_id):
        """Get comprehensive CTO insights for specific assignment"""
        try:
            workspace_id = request.args.get("workspace_id")
            result = get_workspace_service().find_assignment(assignment_id, workspace_id)
            if result.get("status") != 200:
                body = {"error": result.get("error", "Assignment not found")}
                if result.get("ambiguous_workspaces"):
                    body["ambiguous_workspaces"] = result["ambiguous_workspaces"]
                return jsonify(body), result.get("status", 404)
            assignment = result["assignment"]

            # Check if AWS metrics are enabled
            if not assignment.get("aws", {}).get("enabled", False):
                return jsonify({"error": "AWS metrics not enabled for this assignment"}), 400

            # Get comprehensive AWS report
            aws_report = aws_metrics.get_comprehensive_aws_report()

            # Merge with assignment info
            response = {
                "assignment_info": {
                    "id": assignment.get("id"),
                    "name": assignment.get("name"),
                    "monthly_burn_rate": assignment.get("monthly_burn_rate"),
                    "team_size": assignment.get("team_size"),
                }
            }

            # Add AWS comprehensive report data
            response.update(aws_report)

            return jsonify(response)

        except Exception as e:
            return jsonify({"error": str(e)}), 500
