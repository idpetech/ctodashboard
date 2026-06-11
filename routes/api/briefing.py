"""API route module — see routes.api.register_routes."""

import os
from datetime import datetime

from flask import Response, jsonify, request

from routes.api.deps import (
    _track_report_generated,
    get_require_workspace_access,
    get_workspace_service,
    logger,
)
from services.portfolio_service import build_portfolio_overview


def register_briefing_routes(app):
    """Register briefing routes."""

    @app.route("/api/workspaces/<workspace_id>/attention/briefing", methods=["GET"])
    @get_require_workspace_access()
    def get_attention_briefing(workspace_id):
        """Retrieve stored CTO attention briefing for a workspace."""
        if not os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() == "true":
            return jsonify({"error": "Attention engine is disabled"}), 403

        try:
            from services.attention_engine import get_stored_briefing
            from services.security.secure_database import secure_db

            briefing = get_stored_briefing(secure_db, workspace_id)
            if not briefing:
                return jsonify(
                    {
                        "workspace_id": workspace_id,
                        "briefing": None,
                        "message": "No briefing generated yet. Import data or refresh.",
                    }
                )
            return jsonify({"workspace_id": workspace_id, "briefing": briefing})
        except Exception as e:
            logger.exception("Failed to load attention briefing")
            return jsonify({"error": f"Failed to load briefing: {str(e)}"}), 500

    @app.route("/api/workspaces/<workspace_id>/attention/briefing/share", methods=["POST"])
    @get_require_workspace_access()
    def create_attention_briefing_share(workspace_id):
        """Create a shareable read-only report link."""
        from services.briefing_resolver import briefing_features_enabled

        if not briefing_features_enabled():
            return jsonify({"error": "Briefing is disabled"}), 403

        try:
            from services.report_share_service import create_share_link, list_share_links
            from services.security.secure_database import secure_db

            body = request.get_json(silent=True) or {}
            expires_in_days = body.get("expires_in_days", 30)
            base = request.host_url.rstrip("/")

            result = create_share_link(
                secure_db,
                workspace_id,
                expires_in_days=expires_in_days,
                request_base_url=base,
            )
            result["existing_links"] = list_share_links(secure_db, workspace_id)
            _track_report_generated("share_link", workspace_id)
            return jsonify(result)
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            logger.exception("Share link creation failed")
            return jsonify({"error": f"Share link failed: {str(e)}"}), 500

    @app.route("/api/workspaces/<workspace_id>/attention/briefing/shares", methods=["GET"])
    @get_require_workspace_access()
    def list_attention_briefing_shares(workspace_id):
        """List share links and view counts for a workspace."""
        from services.briefing_resolver import briefing_features_enabled

        if not briefing_features_enabled():
            return jsonify({"error": "Briefing is disabled"}), 403

        try:
            from services.report_share_service import list_share_links
            from services.security.secure_database import secure_db

            return jsonify({"shares": list_share_links(secure_db, workspace_id)})
        except Exception as e:
            logger.exception("List share links failed")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/workspaces/<workspace_id>/attention/briefing/export", methods=["GET"])
    @get_require_workspace_access()
    def export_attention_briefing_pdf(workspace_id):
        """Export stored CTO briefing as a PDF (reuses briefing + portfolio data)."""
        from services.briefing_resolver import (
            briefing_features_enabled,
            ensure_stored_briefing,
            get_stored_briefing_raw,
            normalize_briefing_for_export,
        )

        if not briefing_features_enabled():
            return jsonify({"error": "Briefing is disabled"}), 403

        try:
            from services.briefing_pdf_service import generate_briefing_pdf
            from services.security.secure_database import secure_db

            assignments = secure_db.get_workspace_assignments(workspace_id) or []
            briefing = get_stored_briefing_raw(secure_db, workspace_id)
            if not briefing:
                briefing = ensure_stored_briefing(secure_db, workspace_id, assignments)
            if not briefing:
                return jsonify(
                    {
                        "error": "No briefing available",
                        "message": "Generate a briefing first (import data or refresh).",
                    }
                ), 404

            briefing = normalize_briefing_for_export(briefing)
            portfolio = build_portfolio_overview(assignments)
            ws = secure_db.get_workspace(workspace_id) or {}
            portfolio_name = ws.get("name") or workspace_id

            pdf_bytes = generate_briefing_pdf(portfolio_name, briefing, portfolio)

            safe_slug = (
                "".join(
                    c if c.isalnum() or c in "-_" else "-" for c in portfolio_name.replace(" ", "-")
                ).strip("-")
                or "portfolio"
            )
            date_part = datetime.utcnow().strftime("%Y-%m-%d")
            filename = f"CTO-Briefing-{safe_slug}-{date_part}.pdf"

            _track_report_generated("pdf_export", workspace_id, format="pdf")
            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "no-store",
                },
            )
        except Exception as e:
            logger.exception("Briefing PDF export failed")
            return jsonify({"error": f"PDF export failed: {str(e)}"}), 500

    @app.route("/api/workspaces/<workspace_id>/attention/refresh", methods=["POST"])
    @get_require_workspace_access()
    def refresh_attention_briefing(workspace_id):
        """Regenerate CTO attention briefing from current workspace data."""
        if not os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() == "true":
            return jsonify({"error": "Attention engine is disabled"}), 403

        try:
            from services.attention_engine import (
                build_attention_briefing,
                get_stored_briefing,
                store_briefing_in_workspace,
            )
            from services.security.secure_database import secure_db

            ws_result = get_workspace_service().get_workspace_assignments(workspace_id)
            assignments = ws_result.get("assignments") or []
            previous = get_stored_briefing(secure_db, workspace_id)
            last_import = (
                (secure_db.get_workspace(workspace_id) or {}).get("settings", {}).get("last_import")
            )
            briefing = build_attention_briefing(
                assignments,
                previous_briefing=previous,
                import_metadata=last_import,
            )
            store_briefing_in_workspace(secure_db, workspace_id, briefing)
            _track_report_generated("attention_refresh", workspace_id)
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "briefing": briefing,
                    "refreshed_at": briefing.get("generated_at"),
                }
            )
        except Exception as e:
            logger.exception("Attention briefing refresh failed")
            return jsonify({"error": f"Refresh failed: {str(e)}"}), 500

    def _ctolens_disabled():
        if os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true":
            return None
        return jsonify({"error": "CTOLens briefing is disabled"}), 403

    def _load_workspace_assignments(workspace_id: str):
        ws_result = get_workspace_service().get_workspace_assignments(workspace_id)
        return ws_result.get("assignments") or []

    def _ctolens_workspace_context(secure_db, workspace_id, assignments, briefing):
        from services.ctolens_run_metadata import (
            assess_extended_staleness,
            build_diagnostics_payload,
            get_run_log,
            get_run_status,
            get_workspace_schedule,
            header_summary,
        )

        ws = secure_db.get_workspace(workspace_id) or {}
        settings = ws.get("settings") or {}
        run_status = get_run_status(settings)
        schedule = get_workspace_schedule(settings)
        run_log = get_run_log(settings)
        staleness = assess_extended_staleness(briefing, assignments, run_status)
        return {
            "staleness": staleness,
            "run_status": run_status,
            "schedule": schedule,
            "run_log": run_log,
            "header_summary": header_summary(briefing, run_status, schedule),
            "diagnostics": build_diagnostics_payload(briefing or {}, run_status, run_log)
            if briefing
            else None,
        }

    @app.route("/api/workspaces/<workspace_id>/ctolens/briefing", methods=["GET"])
    @get_require_workspace_access()
    def get_ctolens_briefing(workspace_id):
        """Retrieve stored CTOLens executive briefing (auto-generates fast if missing)."""
        disabled = _ctolens_disabled()
        if disabled:
            return disabled
        try:
            from services.briefing_pipeline import get_ctolens_briefing_with_feedback
            from services.briefing_resolver import ensure_stored_briefing
            from services.executive_briefing.feedback import feedback_summary
            from services.security.secure_database import secure_db

            assignments = _load_workspace_assignments(workspace_id)
            briefing = get_ctolens_briefing_with_feedback(secure_db, workspace_id)
            if not briefing and assignments:
                briefing = ensure_stored_briefing(
                    secure_db,
                    workspace_id,
                    assignments,
                    fetch_metrics=False,
                    use_ai=False,
                )
                briefing = dict(briefing)
                briefing["feedback_summary"] = feedback_summary(secure_db, workspace_id)
            if not briefing:
                ctx = _ctolens_workspace_context(secure_db, workspace_id, assignments, None)
                return jsonify(
                    {
                        "workspace_id": workspace_id,
                        "briefing": None,
                        **ctx,
                        "message": "Add assignments to generate a CTOLens briefing.",
                    }
                )
            ctx = _ctolens_workspace_context(secure_db, workspace_id, assignments, briefing)
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "briefing": briefing,
                    **ctx,
                }
            )
        except Exception as e:
            logger.exception("Failed to load CTOLens briefing")
            return jsonify({"error": f"Failed to load briefing: {str(e)}"}), 500

    @app.route("/api/workspaces/<workspace_id>/ctolens/briefing/generate", methods=["POST"])
    @get_require_workspace_access()
    def generate_ctolens_briefing(workspace_id):
        """Generate and store CTOLens briefing from current workspace data."""
        disabled = _ctolens_disabled()
        if disabled:
            return disabled
        try:
            from services.briefing_pipeline import refresh_workspace_ctolens_briefing
            from services.security.secure_database import secure_db

            body = request.get_json(silent=True) or {}
            fetch_metrics = bool(body.get("fetch_metrics", False))
            use_ai = body.get("use_ai")
            if use_ai is not None:
                use_ai = bool(use_ai)

            assignments = _load_workspace_assignments(workspace_id)
            briefing = refresh_workspace_ctolens_briefing(
                workspace_id,
                assignments,
                secure_db,
                fetch_metrics=fetch_metrics,
                use_ai=use_ai,
                run_source="manual",
            )
            ctx = _ctolens_workspace_context(secure_db, workspace_id, assignments, briefing)
            _track_report_generated(
                "ctolens_generate",
                workspace_id,
                fetch_metrics=fetch_metrics,
            )
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "briefing": briefing,
                    **ctx,
                    "refreshed_at": briefing.get("generated_at"),
                }
            )
        except Exception as e:
            logger.exception("CTOLens briefing generation failed")
            return jsonify({"error": f"Generation failed: {str(e)}"}), 500

    @app.route("/api/workspaces/<workspace_id>/ctolens/schedule", methods=["GET", "PUT"])
    @get_require_workspace_access()
    def ctolens_schedule(workspace_id):
        from services.ctolens_run_metadata import (
            get_workspace_schedule,
            is_scheduled_enrichment_enabled,
            normalize_schedule,
            validate_schedule,
        )
        from services.security.secure_database import secure_db

        ws = secure_db.get_workspace(workspace_id)
        if not ws:
            return jsonify({"error": "Workspace not found"}), 404
        settings = ws.get("settings") or {}

        if request.method == "GET":
            from services.ctolens_run_metadata import get_run_log, get_run_status

            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "schedule": get_workspace_schedule(settings),
                    "run_status": get_run_status(settings),
                    "run_log": get_run_log(settings),
                    "scheduled_enrichment_enabled": is_scheduled_enrichment_enabled(),
                }
            )

        if not is_scheduled_enrichment_enabled():
            return jsonify({"error": "Scheduled enrichment is disabled"}), 403

        body = request.get_json(silent=True) or {}
        merged = normalize_schedule({**get_workspace_schedule(settings), **body})
        try:
            validate_schedule(merged)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        result = get_workspace_service().update_workspace_settings(
            workspace_id, {"ctolens_schedule": merged}
        )
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(
            {
                "workspace_id": workspace_id,
                "schedule": merged,
                "scheduled_enrichment_enabled": True,
            }
        )

    @app.route("/api/internal/ctolens/scheduled-refresh", methods=["POST"])
    def ctolens_scheduled_refresh():
        from services.briefing_pipeline import refresh_workspace_ctolens_briefing
        from services.ctolens_run_metadata import (
            cron_secret,
            get_workspace_schedule,
            is_scheduled_enrichment_enabled,
        )
        from services.security.secure_database import secure_db

        if not is_scheduled_enrichment_enabled():
            return jsonify({"error": "Scheduled enrichment is disabled"}), 403

        secret = cron_secret()
        provided = request.headers.get("X-CTOLens-Cron-Secret", "")
        if not secret or provided != secret:
            return jsonify({"error": "Unauthorized"}), 401

        body = request.get_json(silent=True) or {}
        target_workspace = (body.get("workspace_id") or "").strip()
        results = []

        workspaces = secure_db.list_workspaces() or []
        for ws_row in workspaces:
            ws_id = ws_row.get("workspace_id") or ws_row.get("id")
            if not ws_id:
                continue
            if target_workspace and ws_id != target_workspace:
                continue
            ws = secure_db.get_workspace(ws_id) or {}
            schedule = get_workspace_schedule(ws.get("settings") or {})
            if not schedule.get("enabled"):
                continue
            assignments = _load_workspace_assignments(ws_id)
            if not assignments:
                continue
            try:
                refresh_workspace_ctolens_briefing(
                    ws_id,
                    assignments,
                    secure_db,
                    fetch_metrics=True,
                    use_ai=False,
                    run_source="scheduled",
                )
                results.append({"workspace_id": ws_id, "status": "success"})
            except Exception as exc:
                logger.exception("Scheduled CTOLens refresh failed for %s", ws_id)
                results.append({"workspace_id": ws_id, "status": "failed", "error": str(exc)})

        return jsonify({"processed": len(results), "results": results})

    @app.route("/api/workspaces/<workspace_id>/ctolens/signals", methods=["GET"])
    @get_require_workspace_access()
    def get_ctolens_signals(workspace_id):
        """Evaluate and return current signal list."""
        if not (
            os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true"
            or os.getenv("ENABLE_SIGNAL_ENGINE", "false").lower() == "true"
        ):
            return jsonify({"error": "Signal engine is disabled"}), 403
        try:
            from services.briefing_pipeline import build_metrics_overlays
            from services.ctolens_run_metadata import filter_signals_for_run_mode
            from services.signals.engine import SignalEngine

            fetch_metrics = request.args.get("fetch_metrics", "false").lower() == "true"
            assignments = _load_workspace_assignments(workspace_id)
            delivery, connector, _runs = build_metrics_overlays(
                workspace_id, assignments, fetch_metrics=fetch_metrics
            )
            raw_signals = SignalEngine().evaluate_assignments(
                assignments,
                delivery_metrics=delivery,
                connector_metrics=connector,
            )
            signals = filter_signals_for_run_mode(raw_signals, fetch_metrics)
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "signals": [s.to_dict() for s in signals],
                    "count": len(signals),
                }
            )
        except Exception as e:
            logger.exception("CTOLens signals failed")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/workspaces/<workspace_id>/ctolens/recommendations", methods=["GET"])
    @get_require_workspace_access()
    def get_ctolens_recommendations(workspace_id):
        """Evaluate signals and return ranked recommendations."""
        if not (
            os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true"
            or os.getenv("ENABLE_RECOMMENDATION_ENGINE", "false").lower() == "true"
        ):
            return jsonify({"error": "Recommendation engine is disabled"}), 403
        try:
            from services.briefing_pipeline import build_metrics_overlays
            from services.ctolens_run_metadata import filter_signals_for_run_mode
            from services.recommendations.engine import RecommendationEngine
            from services.signals.engine import SignalEngine

            fetch_metrics = request.args.get("fetch_metrics", "false").lower() == "true"
            assignments = _load_workspace_assignments(workspace_id)
            delivery, connector, _runs = build_metrics_overlays(
                workspace_id, assignments, fetch_metrics=fetch_metrics
            )
            raw_signals = SignalEngine().evaluate_assignments(
                assignments,
                delivery_metrics=delivery,
                connector_metrics=connector,
            )
            signals = filter_signals_for_run_mode(raw_signals, fetch_metrics)
            recs = RecommendationEngine().recommend(signals)
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "recommendations": [r.to_dict() for r in recs],
                    "count": len(recs),
                }
            )
        except Exception as e:
            logger.exception("CTOLens recommendations failed")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/workspaces/<workspace_id>/ctolens/recommendations/feedback", methods=["POST"])
    @get_require_workspace_access()
    def post_ctolens_recommendation_feedback(workspace_id):
        """Record accept/dismiss feedback on a recommendation."""
        disabled = _ctolens_disabled()
        if disabled:
            return disabled
        try:
            from services.executive_briefing.feedback import (
                feedback_summary,
                record_recommendation_feedback,
            )
            from services.security.secure_database import secure_db

            body = request.get_json(silent=True) or {}
            recommendation_id = (body.get("recommendation_id") or "").strip()
            title = (body.get("title") or "").strip()
            status = (body.get("status") or "").strip()
            reason = body.get("reason")

            if not recommendation_id or not title:
                return jsonify({"error": "recommendation_id and title are required"}), 400

            record = record_recommendation_feedback(
                secure_db,
                workspace_id,
                recommendation_id=recommendation_id,
                title=title,
                status=status,
                reason=reason,
            )
            return jsonify(
                {
                    "workspace_id": workspace_id,
                    "feedback": record,
                    "summary": feedback_summary(secure_db, workspace_id),
                }
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("Recommendation feedback failed")
            return jsonify({"error": str(e)}), 500
