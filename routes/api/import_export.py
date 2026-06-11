"""API route module — see routes.api.register_routes."""

from flask import jsonify, request, send_from_directory

from routes.api.deps import (
    get_import_service,
)


def register_import_export_routes(app):
    """Register import export routes."""
    # IMPORT API ROUTES - Phase 2 Implementation
    # Enhanced import functionality with validation and templates
    # ============================================================================

    @app.route("/api/import/validate", methods=["POST"])
    def validate_import_data():
        """Validate import data structure without importing"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided for validation"}), 400

            validation = get_import_service().validate_import_data(data)
            return jsonify(validation)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/import/templates")
    def get_import_templates():
        """Get available assignment templates for quick setup"""
        try:
            templates = get_import_service().get_import_templates()
            return jsonify({"templates": templates})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/export/download/<filename>")
    def download_export_file(filename):
        """Download export file - secure file serving for legacy compatibility"""
        try:
            # Security: only allow files from exports directory
            if not filename or ".." in filename or "/" in filename:
                return jsonify({"error": "Invalid filename"}), 400

            export_dir = "exports"
            return send_from_directory(export_dir, filename, as_attachment=True)

        except FileNotFoundError:
            return jsonify({"error": "Export file not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/static/<path:filename>")
    def serve_static(filename):
        """Serve static files"""
        return send_from_directory("static", filename)
