"""CTO Report Generator API — post-processing on analysis_result JSON only."""

from __future__ import annotations

from flask import jsonify, request


def register_reporting_routes(app):
    """Register CTO report routes (no pipeline / analysis / GitHub)."""

    @app.route("/report/generate", methods=["POST"])
    def report_generate():
        from reporting.agent import CTOReportAgent, ReportAgentError
        from reporting.config import is_reporting_enabled

        if not is_reporting_enabled():
            return jsonify({"error": "Reporting layer is disabled"}), 403

        body = request.get_json(silent=True) or {}
        analysis_result = body.get("analysis_result")
        if not isinstance(analysis_result, dict):
            return jsonify({"error": "analysis_result is required and must be an object"}), 400

        try:
            report = CTOReportAgent().run(analysis_result)
        except ReportAgentError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(report), 200
