"""Portfolio entity API routes (Act 1 — ENABLE_PORTFOLIOS)."""

import os

from flask import jsonify, request

from routes.api.deps import get_require_workspace_access, get_workspace_service, logger
from services.portfolio_scope_service import (
    filter_assignments_by_id,
    filter_assignments_by_portfolio,
    get_portfolio,
    is_portfolios_enabled,
    load_scoped_briefing,
    persist_scoped_briefing,
)


def _portfolios_disabled_response():
    return jsonify({"error": "Portfolios are disabled"}), 403


def register_portfolios_routes(app):
    """Register portfolio CRUD and scoped briefing routes."""

    @app.route("/api/workspaces/<workspace_id>/portfolios", methods=["GET", "POST"])
    @get_require_workspace_access()
    def workspace_portfolios(workspace_id):
        if not is_portfolios_enabled():
            return _portfolios_disabled_response()

        if request.method == "GET":
            result = get_workspace_service().list_workspace_portfolios(workspace_id)
            if result.get("error"):
                return jsonify(result), 404
            return jsonify(
                {"workspace_id": workspace_id, "portfolios": result.get("portfolios", [])}
            )

        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "Portfolio name is required"}), 400

        result = get_workspace_service().create_workspace_portfolio(
            workspace_id,
            name,
            description=data.get("description", ""),
            sort_order=data.get("sort_order"),
            portfolio_id=data.get("id"),
        )
        if result.get("success"):
            return jsonify(result), 201
        return jsonify(result), 400

    @app.route(
        "/api/workspaces/<workspace_id>/portfolios/<portfolio_id>", methods=["GET", "PUT", "DELETE"]
    )
    @get_require_workspace_access()
    def workspace_portfolio_detail(workspace_id, portfolio_id):
        if not is_portfolios_enabled():
            return _portfolios_disabled_response()

        if request.method == "GET":
            settings = get_workspace_service().get_workspace(workspace_id)
            if settings.get("error"):
                return jsonify(settings), 404
            portfolio = get_portfolio(settings.get("settings") or {}, portfolio_id)
            if not portfolio:
                return jsonify({"error": f"Portfolio '{portfolio_id}' not found"}), 404
            assignments = (
                get_workspace_service()
                .get_workspace_assignments(workspace_id)
                .get("assignments", [])
            )
            scoped = filter_assignments_by_portfolio(assignments, portfolio_id)
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "portfolio": portfolio,
                    "assignment_count": len(scoped),
                    "assignment_ids": [a.get("id") or a.get("assignment_id") for a in scoped],
                }
            )

        if request.method == "PUT":
            data = request.get_json() or {}
            result = get_workspace_service().update_workspace_portfolio(
                workspace_id,
                portfolio_id,
                name=data.get("name"),
                description=data.get("description"),
                sort_order=data.get("sort_order"),
            )
            if result.get("success"):
                return jsonify(result)
            return jsonify(result), 400

        result = get_workspace_service().delete_workspace_portfolio(workspace_id, portfolio_id)
        if result.get("success"):
            return jsonify(result)
        return jsonify(result), 400

    @app.route(
        "/api/workspaces/<workspace_id>/portfolios/<portfolio_id>/attention/briefing",
        methods=["GET"],
    )
    @get_require_workspace_access()
    def get_portfolio_attention_briefing(workspace_id, portfolio_id):
        if not is_portfolios_enabled():
            return _portfolios_disabled_response()
        if os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() != "true":
            return jsonify({"error": "Attention engine is disabled"}), 403

        ws = get_workspace_service().get_workspace(workspace_id)
        if ws.get("error"):
            return jsonify(ws), 404
        if not get_portfolio(ws.get("settings") or {}, portfolio_id):
            return jsonify({"error": f"Portfolio '{portfolio_id}' not found"}), 404

        try:
            from services.security.secure_database import secure_db

            briefing = load_scoped_briefing(
                secure_db,
                workspace_id,
                scope="portfolio",
                scope_id=portfolio_id,
                engine="attention",
            )
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "portfolio_id": portfolio_id,
                    "briefing": briefing,
                    "message": None if briefing else "No portfolio briefing generated yet.",
                }
            )
        except Exception as exc:
            logger.exception("Failed to load portfolio attention briefing")
            return jsonify({"error": f"Failed to load briefing: {exc}"}), 500

    @app.route(
        "/api/workspaces/<workspace_id>/portfolios/<portfolio_id>/attention/refresh",
        methods=["POST"],
    )
    @get_require_workspace_access()
    def refresh_portfolio_attention_briefing(workspace_id, portfolio_id):
        if not is_portfolios_enabled():
            return _portfolios_disabled_response()
        if os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() != "true":
            return jsonify({"error": "Attention engine is disabled"}), 403

        ws = get_workspace_service().get_workspace(workspace_id)
        if ws.get("error"):
            return jsonify(ws), 404
        if not get_portfolio(ws.get("settings") or {}, portfolio_id):
            return jsonify({"error": f"Portfolio '{portfolio_id}' not found"}), 404

        try:
            from services.attention_engine import build_attention_briefing
            from services.security.secure_database import secure_db

            assignments = (
                get_workspace_service()
                .get_workspace_assignments(workspace_id)
                .get("assignments", [])
            )
            scoped = filter_assignments_by_portfolio(assignments, portfolio_id)
            previous = load_scoped_briefing(
                secure_db,
                workspace_id,
                scope="portfolio",
                scope_id=portfolio_id,
                engine="attention",
            )
            last_import = (ws.get("settings") or {}).get("last_import")
            briefing = build_attention_briefing(
                scoped,
                previous_briefing=previous,
                import_metadata=last_import,
            )
            briefing["scope"] = "portfolio"
            briefing["portfolio_id"] = portfolio_id
            persist_scoped_briefing(
                secure_db,
                workspace_id,
                scope="portfolio",
                scope_id=portfolio_id,
                briefing=briefing,
                engine="attention",
            )
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "portfolio_id": portfolio_id,
                    "briefing": briefing,
                    "refreshed_at": briefing.get("generated_at"),
                }
            )
        except Exception as exc:
            logger.exception("Portfolio attention briefing refresh failed")
            return jsonify({"error": f"Refresh failed: {exc}"}), 500

    @app.route(
        "/api/workspaces/<workspace_id>/assignments/<assignment_id>/attention/briefing",
        methods=["GET"],
    )
    @get_require_workspace_access()
    def get_assignment_attention_briefing(workspace_id, assignment_id):
        if not is_portfolios_enabled():
            return _portfolios_disabled_response()
        if os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() != "true":
            return jsonify({"error": "Attention engine is disabled"}), 403

        if not get_workspace_service().get_assignment(workspace_id, assignment_id):
            return jsonify({"error": f"Assignment '{assignment_id}' not found"}), 404

        try:
            from services.security.secure_database import secure_db

            briefing = load_scoped_briefing(
                secure_db,
                workspace_id,
                scope="assignment",
                scope_id=assignment_id,
                engine="attention",
            )
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "assignment_id": assignment_id,
                    "briefing": briefing,
                    "message": None if briefing else "No assignment briefing generated yet.",
                }
            )
        except Exception as exc:
            logger.exception("Failed to load assignment attention briefing")
            return jsonify({"error": f"Failed to load briefing: {exc}"}), 500

    @app.route(
        "/api/workspaces/<workspace_id>/assignments/<assignment_id>/attention/refresh",
        methods=["POST"],
    )
    @get_require_workspace_access()
    def refresh_assignment_attention_briefing(workspace_id, assignment_id):
        if not is_portfolios_enabled():
            return _portfolios_disabled_response()
        if os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() != "true":
            return jsonify({"error": "Attention engine is disabled"}), 403

        assignment = get_workspace_service().get_assignment(workspace_id, assignment_id)
        if not assignment:
            return jsonify({"error": f"Assignment '{assignment_id}' not found"}), 404

        try:
            from services.attention_engine import build_attention_briefing
            from services.security.secure_database import secure_db

            ws = get_workspace_service().get_workspace(workspace_id)
            previous = load_scoped_briefing(
                secure_db,
                workspace_id,
                scope="assignment",
                scope_id=assignment_id,
                engine="attention",
            )
            last_import = (ws.get("settings") or {}).get("last_import")
            scoped = filter_assignments_by_id([assignment], assignment_id)
            briefing = build_attention_briefing(
                scoped,
                previous_briefing=previous,
                import_metadata=last_import,
            )
            briefing["scope"] = "assignment"
            briefing["assignment_id"] = assignment_id
            persist_scoped_briefing(
                secure_db,
                workspace_id,
                scope="assignment",
                scope_id=assignment_id,
                briefing=briefing,
                engine="attention",
            )
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "assignment_id": assignment_id,
                    "briefing": briefing,
                    "refreshed_at": briefing.get("generated_at"),
                }
            )
        except Exception as exc:
            logger.exception("Assignment attention briefing refresh failed")
            return jsonify({"error": f"Refresh failed: {exc}"}), 500

    @app.route(
        "/api/workspaces/<workspace_id>/portfolios/<portfolio_id>/ctolens/briefing",
        methods=["GET"],
    )
    @get_require_workspace_access()
    def get_portfolio_ctolens_briefing(workspace_id, portfolio_id):
        if not is_portfolios_enabled():
            return _portfolios_disabled_response()
        if os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() != "true":
            return jsonify({"error": "CTOLens briefing is disabled"}), 403

        ws = get_workspace_service().get_workspace(workspace_id)
        if ws.get("error"):
            return jsonify(ws), 404
        if not get_portfolio(ws.get("settings") or {}, portfolio_id):
            return jsonify({"error": f"Portfolio '{portfolio_id}' not found"}), 404

        from services.security.secure_database import secure_db

        briefing = load_scoped_briefing(
            secure_db,
            workspace_id,
            scope="portfolio",
            scope_id=portfolio_id,
            engine="ctolens",
        )
        return jsonify(
            {
                "workspace_id": workspace_id,
                "portfolio_id": portfolio_id,
                "briefing": briefing,
            }
        )

    @app.route(
        "/api/workspaces/<workspace_id>/portfolios/<portfolio_id>/ctolens/refresh",
        methods=["POST"],
    )
    @get_require_workspace_access()
    def refresh_portfolio_ctolens_briefing(workspace_id, portfolio_id):
        if not is_portfolios_enabled():
            return _portfolios_disabled_response()
        if os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() != "true":
            return jsonify({"error": "CTOLens briefing is disabled"}), 403

        ws = get_workspace_service().get_workspace(workspace_id)
        if ws.get("error"):
            return jsonify(ws), 404
        if not get_portfolio(ws.get("settings") or {}, portfolio_id):
            return jsonify({"error": f"Portfolio '{portfolio_id}' not found"}), 404

        try:
            from services.briefing_pipeline import refresh_workspace_ctolens_briefing
            from services.security.secure_database import secure_db

            assignments = (
                get_workspace_service()
                .get_workspace_assignments(workspace_id)
                .get("assignments", [])
            )
            scoped = filter_assignments_by_portfolio(assignments, portfolio_id)
            briefing = refresh_workspace_ctolens_briefing(
                workspace_id,
                scoped,
                secure_db,
                fetch_metrics=request.args.get("fetch_metrics", "").lower() == "true",
                run_source="portfolio_manual",
            )
            briefing["scope"] = "portfolio"
            briefing["portfolio_id"] = portfolio_id
            persist_scoped_briefing(
                secure_db,
                workspace_id,
                scope="portfolio",
                scope_id=portfolio_id,
                briefing=briefing,
                engine="ctolens",
            )
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "portfolio_id": portfolio_id,
                    "briefing": briefing,
                }
            )
        except Exception as exc:
            logger.exception("Portfolio CTOLens refresh failed")
            return jsonify({"error": f"Refresh failed: {exc}"}), 500
