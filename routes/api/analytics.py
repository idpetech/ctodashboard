"""Product analytics API routes."""

from flask import jsonify, request

from routes.api.deps import get_require_auth


def register_analytics_routes(app):
    """Register analytics routes."""
    # ===== PRODUCT ANALYTICS (MVP) =====

    @app.route("/api/analytics/events", methods=["POST"])
    @get_require_auth()
    def analytics_track_event():
        from flask import g
        from flask import session as flask_session

        from services.analytics.event_tracker import track_event
        from services.analytics.models import is_analytics_enabled

        if not is_analytics_enabled():
            return "", 204

        body = request.get_json(silent=True) or {}
        event_name = (body.get("event_name") or "").strip()
        if not event_name:
            return jsonify({"error": "event_name is required"}), 400

        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
        user = getattr(g, "current_user", None) or {}
        user_id = user.get("email") or flask_session.get("user_email")
        if not user_id:
            return jsonify({"error": "User not found"}), 401

        session_id = body.get("session_id") or flask_session.get("analytics_session_id")
        result = track_event(
            user_id,
            event_name,
            session_id=session_id,
            metadata=metadata,
        )
        if result and result.get("session_id"):
            flask_session["analytics_session_id"] = result["session_id"]
        return jsonify({"success": True, **(result or {})}), 200

    @app.route("/api/analytics/users/me/activity", methods=["GET"])
    @get_require_auth()
    def analytics_user_activity():
        from flask import g

        from services.analytics.event_tracker import get_user_activity_summary
        from services.analytics.models import is_analytics_enabled

        if not is_analytics_enabled():
            return jsonify({"error": "Product analytics is disabled"}), 403

        user = getattr(g, "current_user", None) or {}
        email = user.get("email") or user.get("user_email")
        if not email:
            return jsonify({"error": "User not found"}), 401
        return jsonify(get_user_activity_summary(email))

    @app.route("/api/analytics/summary", methods=["GET"])
    @get_require_auth()
    def analytics_platform_summary():
        from flask import g

        from services.analytics.models import is_analytics_enabled
        from services.analytics.queries import get_platform_summary, get_retention_snapshot

        if not is_analytics_enabled():
            return jsonify({"error": "Product analytics is disabled"}), 403

        user = getattr(g, "current_user", None) or {}
        if user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        days = request.args.get("days", 7, type=int)
        days = max(1, min(days, 90))
        summary = get_platform_summary(days=days)
        summary["retention"] = get_retention_snapshot()
        return jsonify(summary)

    @app.route("/api/analytics/page-view", methods=["POST"])
    def analytics_page_view():
        from services.analytics.event_tracker import track_anonymous_page_view
        from services.analytics.models import is_analytics_enabled

        if not is_analytics_enabled():
            return "", 204

        body = request.get_json(silent=True) or {}
        path = (body.get("path") or request.headers.get("Referer") or "/").strip()
        anonymous_id = (body.get("anonymous_id") or "").strip() or None
        track_anonymous_page_view(path, anonymous_id=anonymous_id)
        return jsonify({"success": True}), 200
