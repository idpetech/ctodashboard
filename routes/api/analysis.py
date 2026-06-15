"""Analysis Layer v1 API — post-processing on pipeline JSON (load from body or DB)."""

from __future__ import annotations

from flask import jsonify, request


def register_analysis_routes(app):
    """Register analysis routes. Engine is JSON-only; optional DB load via snapshot_id."""

    @app.route("/analysis/run", methods=["POST"])
    def analysis_run():
        from analysis.config import is_analysis_enabled
        from analysis.engine import AnalysisEngine, AnalysisEngineError
        from analysis.pipeline_loader import PipelineLoadError, load_pipeline_result_from_db

        if not is_analysis_enabled():
            return jsonify({"error": "Analysis layer is disabled"}), 403

        body = request.get_json(silent=True) or {}
        snapshot_id = (body.get("snapshot_id") or "").strip()
        workspace_id = (body.get("workspace_id") or "").strip() or None

        try:
            if snapshot_id:
                pipeline_result = load_pipeline_result_from_db(
                    snapshot_id,
                    workspace_id=workspace_id,
                )
            else:
                pipeline_result = body.get("pipeline_result")
                if not isinstance(pipeline_result, dict):
                    return jsonify(
                        {
                            "error": (
                                "Provide pipeline_result (object) or snapshot_id "
                                "(loads persisted snapshot + index + metrics from DB)"
                            )
                        }
                    ), 400

            output = AnalysisEngine().run(pipeline_result)
        except PipelineLoadError as exc:
            return jsonify({"error": str(exc)}), 404
        except AnalysisEngineError as exc:
            return jsonify({"error": str(exc)}), 400

        response = dict(output)
        if snapshot_id:
            response["snapshot_id"] = snapshot_id
        return jsonify(response), 200
