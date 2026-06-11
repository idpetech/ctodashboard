"""API route module — see routes.api.register_routes."""

import json

from flask import jsonify, request

from routes.api.deps import (
    get_export_service,
    get_require_auth,
)


def register_audit_routes(app):
    """Register audit routes."""

    @app.route("/api/assignments/export", methods=["GET"])
    @get_require_auth()
    def export_assignments():
        """Export all assignments across workspaces - Enhanced with Phase 2 export service"""
        try:
            # Use the enhanced export service for better functionality
            # For now, export the default workspace - this is a simple approach
            workspace_id = request.args.get("workspace_id", "default_workspace")
            format_type = request.args.get("format", "json").lower()

            result = get_export_service().export_workspace_data(
                workspace_id=workspace_id, format=format_type, include_assignments=True
            )

            if result["success"]:
                # For the legacy endpoint, return the export data directly instead of file info
                export_file_path = result["file_path"]
                try:
                    with open(export_file_path, "r") as f:
                        export_data = json.load(f)
                    return jsonify(export_data)
                except Exception as e:
                    return jsonify({"error": f"Failed to read export file: {str(e)}"}), 500
            else:
                return jsonify({"error": result.get("error", "Export failed")}), 500

        except Exception as e:
            return jsonify({"error": f"Assignment export failed: {str(e)}"}), 500

    # ===== PHASE 5C: ASSIGNMENT HISTORY/AUDIT LOG ENDPOINTS =====

    @app.route("/api/assignments/<assignment_id>/history", methods=["GET"])
    @get_require_auth()
    def get_assignment_history(assignment_id):
        """Get change history for a specific assignment - Phase 5C"""
        try:
            # Import audit service
            from services.audit_service import audit_service

            history = audit_service.get_assignment_history(assignment_id)

            return jsonify(
                {"assignment_id": assignment_id, "history": history, "total_changes": len(history)}
            )

        except Exception as e:
            return jsonify({"error": f"Failed to get assignment history: {str(e)}"}), 500

    @app.route("/api/audit/recent", methods=["GET"])
    @get_require_auth()
    def get_recent_changes():
        """Get recent changes across all assignments - Phase 5C"""
        try:
            # Import audit service
            from services.audit_service import audit_service

            limit = request.args.get("limit", 50, type=int)
            changes = audit_service.get_recent_changes(limit)

            return jsonify({"recent_changes": changes, "total_returned": len(changes)})

        except Exception as e:
            return jsonify({"error": f"Failed to get recent changes: {str(e)}"}), 500
