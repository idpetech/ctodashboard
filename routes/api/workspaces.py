"""API route module — see routes.api.register_routes."""

import json
import os

from flask import jsonify, request

from routes.api.credentials import (
    basic_validate_credentials,
    get_workspace_credential_status,
    validate_connector_credentials,
)
from routes.api.deps import (
    _refresh_workspace_attention_briefing,
    _track_product_event,
    aws_metrics,
    get_current_user,
    get_export_service,
    get_import_service,
    get_optional_auth,
    get_require_auth,
    get_require_workspace_access,
    get_user_service,
    get_workspace_connectors,
    get_workspace_service,
    github_metrics,
    jira_metrics,
    logger,
)
from services.embedded.jira_metrics import normalize_jira_base_url
from services.trial_guard import require_trial_write_access


def register_workspaces_routes(app):
    """Register workspaces routes."""
    # ===== WORKSPACE MANAGEMENT ENDPOINTS (Phase 1 + 3 Auth) =====

    @app.route("/api/workspaces", methods=["GET", "POST"])
    @get_optional_auth()
    def workspace_management():
        """Workspace management endpoint"""
        if request.method == "GET":
            # Authenticated users get their own workspaces; anonymous falls back to default
            try:
                current_user = get_current_user()
                if current_user:
                    user_workspace_ids = (
                        get_user_service()
                        .get_user_workspaces(current_user.get("email"))
                        .get("workspaces", [])
                    )
                    user_workspaces = []
                    for ws_id in user_workspace_ids:
                        workspace_data = get_workspace_service().get_workspace(ws_id)
                        if workspace_data and not workspace_data.get("error"):
                            user_workspaces.append(
                                {
                                    "id": workspace_data.get("id"),
                                    "name": workspace_data.get("name"),
                                    "description": workspace_data.get("description", ""),
                                    "assignment_count": len(workspace_data.get("assignments", [])),
                                    "status": workspace_data.get("status", "active"),
                                    "created_at": workspace_data.get("created_at"),
                                }
                            )
                    if user_workspaces:
                        return jsonify(user_workspaces)

                # Return default workspace for unauthenticated access
                workspace_data = get_workspace_service().get_workspace("default_workspace")
                if workspace_data and not workspace_data.get("error"):
                    workspace_info = {
                        "id": workspace_data.get("id"),
                        "name": workspace_data.get("name"),
                        "description": workspace_data.get("description", ""),
                        "assignment_count": len(workspace_data.get("assignments", [])),
                        "status": workspace_data.get("status", "active"),
                        "created_at": workspace_data.get("created_at"),
                    }
                    return jsonify([workspace_info])
                else:
                    return jsonify([])
            except Exception:
                return jsonify([])

        elif request.method == "POST":
            # Create new workspace (requires authentication)
            current_user = get_current_user()
            if not current_user:
                return jsonify({"error": "Authentication required"}), 401

            data = request.get_json()
            if not data:
                return jsonify({"error": "No workspace data provided"}), 400

            workspace_id = data.get("id")
            name = data.get("name")
            description = data.get("description", "")

            if not workspace_id or not name:
                return jsonify({"error": "Workspace ID and name are required"}), 400

            try:
                result = get_workspace_service().create_workspace(workspace_id, name, description)
                if result.get("success"):
                    # Link the new workspace to the creating user
                    get_user_service().add_user_to_workspace(
                        current_user.get("email"), workspace_id, "owner"
                    )
                    return jsonify(result), 201
                else:
                    return jsonify(result), 400
            except Exception as e:
                return jsonify({"error": f"Failed to create workspace: {str(e)}"}), 500

    @app.route("/api/workspaces/<workspace_id>", methods=["GET", "DELETE"])
    @get_require_workspace_access()
    def workspace_detail(workspace_id):
        """Workspace detail operations"""
        if request.method == "GET":
            # Get workspace details
            workspace = get_workspace_service().get_workspace(workspace_id)
            if "error" in workspace:
                return jsonify(workspace), 404
            return jsonify(workspace)

        elif request.method == "DELETE":
            # Delete workspace
            result = get_workspace_service().delete_workspace(workspace_id)
            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400

    @app.route("/api/workspaces/<workspace_id>/assignments", methods=["GET", "POST"])
    @get_require_workspace_access()
    def workspace_assignments(workspace_id):
        """Workspace assignment management"""
        if request.method == "GET":
            # Get assignments for workspace
            result = get_workspace_service().get_workspace_assignments(workspace_id)
            if "error" in result:
                return jsonify(result), 404
            return jsonify(result)

        elif request.method == "POST":
            denied = require_trial_write_access()
            if denied:
                return denied
            # Add assignment to workspace
            data = request.get_json()
            if not data:
                return jsonify({"error": "No assignment data provided"}), 400

            assignment_id = data.get("id")
            if not assignment_id:
                return jsonify({"error": "Assignment ID is required"}), 400

            # Remove 'id' from data since it's passed separately
            assignment_config = {k: v for k, v in data.items() if k != "id"}

            result = get_workspace_service().add_assignment_to_workspace(
                workspace_id, assignment_id, assignment_config
            )

            if result.get("success"):
                return jsonify(result), 201
            else:
                return jsonify(result), 400

    @app.route(
        "/api/workspaces/<workspace_id>/assignments/<assignment_id>",
        methods=["GET", "PUT", "DELETE"],
    )
    @get_require_workspace_access()
    def workspace_assignment_detail(workspace_id, assignment_id):
        """Get, update, or archive a specific assignment in one workspace."""
        if request.method == "GET":
            assignment = get_workspace_service().get_assignment(workspace_id, assignment_id)
            if not assignment:
                return jsonify(
                    {
                        "error": f"Assignment '{assignment_id}' not found in workspace '{workspace_id}'"
                    }
                ), 404
            return jsonify(assignment)

        elif request.method == "PUT":
            data = request.get_json()
            if not data:
                return jsonify({"error": "No assignment data provided"}), 400

            result = get_workspace_service().update_assignment(workspace_id, assignment_id, data)
            if not result.get("success"):
                return jsonify({"error": result.get("error", "Update failed")}), 400

            _refresh_workspace_attention_briefing(workspace_id)
            return jsonify(result)

        elif request.method == "DELETE":
            result = get_workspace_service().delete_assignment(workspace_id, assignment_id)
            if result.get("success"):
                return jsonify(
                    {
                        "success": True,
                        "message": result.get("message", f"Assignment '{assignment_id}' deleted"),
                    }
                )
            return jsonify({"error": result.get("error", "Delete failed")}), 404

    # ===== PHASE 3 WORKSPACE CREDENTIALS TEST ENDPOINT =====

    @app.route(
        "/api/workspaces/<workspace_id>/assignments/<assignment_id>/test-credentials",
        methods=["GET"],
    )
    @get_require_workspace_access()
    def test_workspace_credentials(workspace_id, assignment_id):
        """
        Test endpoint to verify Phase 3 workspace credentials are working.
        Returns credential sources and connector initialization status.
        """
        try:
            # Test workspace connectors
            connectors = get_workspace_connectors(workspace_id, assignment_id)

            results = {
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "test_results": {},
                "credential_sources": {},
            }

            # Test GitHub credentials
            github_connector = connectors["github"]
            results["credential_sources"]["github"] = {
                "token_source": "workspace"
                if github_connector.token != github_metrics.token
                else "environment",
                "token_present": bool(github_connector.token),
                "org_source": "workspace"
                if hasattr(github_connector, "org")
                and github_connector.org != getattr(github_metrics, "org", None)
                else "environment",
                "org_present": bool(getattr(github_connector, "org", None)),
            }

            # Test Jira credentials
            jira_connector = connectors["jira"]
            results["credential_sources"]["jira"] = {
                "token_source": "workspace"
                if jira_connector.token != jira_metrics.token
                else "environment",
                "token_present": bool(jira_connector.token),
                "url_source": "workspace"
                if jira_connector.base_url != jira_metrics.base_url
                else "environment",
                "url_present": bool(jira_connector.base_url),
                "email_present": bool(jira_connector.email),
            }

            # Test AWS credentials
            aws_connector = connectors["aws"]
            results["credential_sources"]["aws"] = {
                "access_key_source": "workspace"
                if aws_connector.access_key != aws_metrics.access_key
                else "environment",
                "access_key_present": bool(aws_connector.access_key),
                "secret_key_source": "workspace"
                if aws_connector.secret_key != aws_metrics.secret_key
                else "environment",
                "secret_key_present": bool(aws_connector.secret_key),
                "region_source": "workspace"
                if aws_connector.region != aws_metrics.region
                else "environment",
                "region": aws_connector.region,
            }

            # Test credential service directly
            from services.auth.credential_service import CredentialService

            credential_service = CredentialService()

            results["direct_credential_test"] = {
                "github": credential_service.get_github_credentials(workspace_id, assignment_id),
                "jira": credential_service.get_jira_credentials(workspace_id, assignment_id),
                "aws": credential_service.get_aws_credentials(workspace_id, assignment_id),
            }

            results["test_results"]["phase_3_status"] = (
                "✅ WORKING"
                if any(
                    src.get("token_source") == "workspace"
                    or src.get("access_key_source") == "workspace"
                    for src in results["credential_sources"].values()
                )
                else "❌ FALLBACK_TO_ENV_VARS"
            )

            return jsonify(results)

        except Exception as e:
            return jsonify(
                {
                    "error": "Failed to test workspace credentials",
                    "details": str(e),
                    "workspace_id": workspace_id,
                    "assignment_id": assignment_id,
                }
            ), 500

    # ===== CONNECTOR TEMPLATE ENDPOINTS (Phase 2) =====

    @app.route("/api/workspaces/<workspace_id>/connector-templates", methods=["GET"])
    @get_require_workspace_access()
    def get_workspace_templates(workspace_id):
        """Get all connector templates for workspace"""
        connector_type = request.args.get("type")  # Optional filter by connector type
        result = get_workspace_service().get_connector_templates(workspace_id, connector_type)

        if "error" in result:
            return jsonify(result), 404

        return jsonify(result)

    @app.route(
        "/api/workspaces/<workspace_id>/connector-templates/<connector_type>", methods=["POST"]
    )
    def create_connector_template(workspace_id, connector_type):
        """Create a connector template"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No template data provided"}), 400

        template_name = data.get("name")
        template_config = data.get("config", {})

        if not template_name:
            return jsonify({"error": "Template name is required"}), 400

        result = get_workspace_service().create_connector_template(
            workspace_id, connector_type, template_name, template_config
        )

        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    @app.route(
        "/api/workspaces/<workspace_id>/connector-templates/<connector_type>/<template_name>",
        methods=["GET", "DELETE"],
    )
    def connector_template_detail(workspace_id, connector_type, template_name):
        """Get or delete specific connector template"""
        if request.method == "GET":
            # Get template details
            result = get_workspace_service().get_connector_template(
                workspace_id, connector_type, template_name
            )
            if "error" in result:
                return jsonify(result), 404
            return jsonify(result)

        elif request.method == "DELETE":
            # Delete template
            result = get_workspace_service().delete_connector_template(
                workspace_id, connector_type, template_name
            )
            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400

    @app.route("/api/workspaces/<workspace_id>/assignments/from-template", methods=["POST"])
    def create_assignment_from_template(workspace_id):
        denied = require_trial_write_access()
        if denied:
            return denied
        """Create assignment using connector templates"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No assignment data provided"}), 400

        assignment_id = data.get("id")
        if not assignment_id:
            return jsonify({"error": "Assignment ID is required"}), 400

        # Extract templates mapping
        templates = data.get("templates", {})  # {connector_type: template_name}

        # Remove 'id' and 'templates' from assignment config
        assignment_config = {k: v for k, v in data.items() if k not in ["id", "templates"]}

        result = get_workspace_service().create_assignment_from_template(
            workspace_id, assignment_id, assignment_config, templates
        )

        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    @app.route(
        "/api/workspaces/<workspace_id>/assignments/<assignment_id>/auth/<connector_type>",
        methods=["GET", "PUT"],
    )
    @get_require_auth()
    def assignment_auth(workspace_id, assignment_id, connector_type):
        if request.method == "GET":
            from services.auth.credential_service import CredentialService

            creds = CredentialService().get_workspace_credentials(
                workspace_id, assignment_id, connector_type
            )
            if not creds:
                return jsonify({"credentials": {}, "auth_configured": False}), 200
            return jsonify({"credentials": creds, "auth_configured": True}), 200

        data = request.get_json()
        if not data:
            return jsonify({"error": "No credentials provided"}), 400
        credentials = data.get("credentials", {})
        if not credentials:
            return jsonify({"error": "Credentials object is required"}), 400
        result = get_workspace_service().update_assignment_auth(
            workspace_id, assignment_id, connector_type, credentials
        )
        if result.get("success"):
            return jsonify(result), 200
        return jsonify(result), 400

    # ===== WORKSPACE SETTINGS & CREDENTIAL MANAGEMENT =====

    @app.route("/api/workspaces/<workspace_id>/settings", methods=["GET", "PUT"])
    def workspace_settings(workspace_id):
        """Get or update workspace settings"""
        if request.method == "GET":
            # Get workspace settings including connector configurations
            workspace = get_workspace_service().get_workspace(workspace_id)
            if "error" in workspace:
                return jsonify(workspace), 404

            # Get assignments for credential status
            assignments = get_workspace_service().get_workspace_assignments(workspace_id)

            # Return workspace info with credential status
            return jsonify(
                {
                    "workspace": workspace,
                    "assignments": assignments.get("assignments", []),
                    "connector_templates": workspace.get("connector_templates", {}),
                    "credential_status": get_workspace_credential_status(workspace_id),
                }
            )

        elif request.method == "PUT":
            # Update workspace settings
            data = request.get_json()
            if not data:
                return jsonify({"error": "No settings data provided"}), 400

            result = get_workspace_service().update_workspace_settings(workspace_id, data)
            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400

    @app.route("/api/workspaces/<workspace_id>/credentials", methods=["GET"])
    def get_workspace_credentials(workspace_id):
        """Get credential status for all connectors in workspace"""
        try:
            status = get_workspace_credential_status(workspace_id)
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": f"Failed to get credential status: {str(e)}"}), 500

    @app.route(
        "/api/workspaces/<workspace_id>/credentials/<connector_type>", methods=["PUT", "DELETE"]
    )
    @get_require_auth()
    def manage_connector_credentials(workspace_id, connector_type):
        """Set or delete credentials for a specific connector type"""
        if request.method == "PUT":
            data = request.get_json()
            if not data:
                return jsonify({"error": "No credential data provided"}), 400

            credentials = data.get("credentials", {})
            assignment_id = data.get("assignment_id")

            if not credentials:
                return jsonify({"error": "Credentials are required"}), 400

            if not assignment_id:
                return jsonify({"error": "Assignment ID is required"}), 400

            if connector_type == "jira":
                credentials = dict(credentials)
                if credentials.get("jira_url"):
                    credentials["jira_url"] = normalize_jira_base_url(credentials["jira_url"])
                if credentials.get("jira_email"):
                    credentials["jira_email"] = credentials["jira_email"].strip()
                if credentials.get("jira_token"):
                    credentials["jira_token"] = credentials["jira_token"].strip()

            # Basic validation - just check required fields are present
            validation_result = basic_validate_credentials(connector_type, credentials)
            if not validation_result.get("valid"):
                return jsonify(
                    {
                        "error": "Missing required credential fields",
                        "details": validation_result.get("error", "Required fields missing"),
                    }
                ), 400

            # Update assignment auth
            result = get_workspace_service().update_assignment_auth(
                workspace_id, assignment_id, connector_type, credentials
            )

            if result.get("success"):
                _track_product_event(
                    "integration_connected",
                    metadata={
                        "workspace_id": workspace_id,
                        "assignment_id": assignment_id,
                        "connector": connector_type,
                    },
                )
                return jsonify(
                    {
                        "success": True,
                        "message": f"{connector_type.title()} credentials updated successfully",
                        "validation": validation_result,
                    }
                )
            else:
                return jsonify(result), 400

        elif request.method == "DELETE":
            # Clear credentials for connector type
            data = request.get_json()
            assignment_id = data.get("assignment_id") if data else None

            if not assignment_id:
                return jsonify({"error": "Assignment ID is required"}), 400

            result = get_workspace_service().clear_assignment_auth(
                workspace_id, assignment_id, connector_type
            )

            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400

    @app.route("/api/workspaces/<workspace_id>/credentials/<connector_type>/test", methods=["POST"])
    def test_connector_credentials(workspace_id, connector_type):
        """Test connector credentials without saving them"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No credential data provided"}), 400

        credentials = data.get("credentials", {})
        if not credentials:
            return jsonify({"error": "Credentials are required"}), 400

        result = validate_connector_credentials(connector_type, credentials)
        return jsonify(result)

    # ===== PHASE 5C: IMPORT/EXPORT ENDPOINTS =====

    @app.route("/api/workspaces/<workspace_id>/export", methods=["GET"])
    @get_require_auth()
    def export_workspace_data(workspace_id):
        """Export all workspace data - Enhanced with Phase 2 export service"""
        try:
            format_type = request.args.get("format", "json").lower()
            include_assignments = request.args.get("include_assignments", "true").lower() == "true"

            result = get_export_service().export_workspace_data(
                workspace_id=workspace_id,
                format=format_type,
                include_assignments=include_assignments,
            )

            if result["success"]:
                # For the legacy endpoint, return the export data directly instead of file info
                export_file_path = result["file_path"]
                try:
                    if format_type == "json":
                        with open(export_file_path, "r") as f:
                            export_data = json.load(f)
                        return jsonify(export_data)
                    else:
                        # For CSV, return file info since we can't return CSV as JSON
                        return jsonify(
                            {
                                "message": "Export completed",
                                "filename": result["filename"],
                                "download_url": f"/api/export/download/{result['filename']}",
                                "format": format_type,
                                "size_bytes": result["size_bytes"],
                            }
                        )
                except Exception as e:
                    return jsonify({"error": f"Failed to read export file: {str(e)}"}), 500
            else:
                return jsonify({"error": result.get("error", "Export failed")}), 500

        except Exception as e:
            return jsonify({"error": f"Export failed: {str(e)}"}), 500

    @app.route("/api/workspaces/<workspace_id>/import", methods=["POST"])
    @get_require_workspace_access()
    def import_workspace_data(workspace_id):
        """Enhanced import workspace data - Phase 2 Implementation with backward compatibility"""
        denied = require_trial_write_access()
        if denied:
            return denied
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No import data provided"}), 400

            import_mode = request.args.get("mode", "create_new")  # create_new, overwrite, merge

            # Use enhanced import service with validation and compatibility
            results = get_import_service().import_workspace_data(workspace_id, data, import_mode)

            # Determine appropriate status code
            if results["success"]:
                status_code = 200
            elif (
                results.get("imported_assignments", 0) > 0
                or results.get("updated_assignments", 0) > 0
            ):
                status_code = 207  # Partial success
            else:
                status_code = 400  # Failed

            return jsonify(results), status_code

        except Exception as e:
            return jsonify({"error": f"Import failed: {str(e)}"}), 500

    @app.route("/api/workspaces/<workspace_id>/import/file", methods=["POST"])
    @get_require_workspace_access()
    def import_workspace_file(workspace_id):
        """Import assignments from CSV or Excel (.xlsx) upload.

        Feature-flagged via ENABLE_CSV_IMPORT (default off).
        """
        denied = require_trial_write_access()
        if denied:
            return denied
        if not os.getenv("ENABLE_CSV_IMPORT", "false").lower() == "true":
            return jsonify({"error": "CSV/Excel import is disabled"}), 403

        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            return jsonify({"error": "No file uploaded (field name: file)"}), 400

        filename = uploaded.filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ("csv", "xlsx", "xlsm"):
            return jsonify({"error": f"Unsupported file type .{ext}. Upload .csv or .xlsx"}), 400

        import_mode = request.args.get("mode", "create_new")
        force = request.args.get("force", "false").lower() == "true"

        try:
            content = uploaded.read()
            if not content:
                return jsonify({"error": "Uploaded file is empty"}), 400

            results = get_import_service().import_from_spreadsheet(
                workspace_id,
                content,
                filename,
                import_mode=import_mode,
                force=force,
                run_attention=True,
            )

            if results.get("duplicate_file"):
                return jsonify(results), 200
            if results.get("success"):
                status_code = 200
            elif (
                results.get("imported_assignments", 0) > 0
                or results.get("updated_assignments", 0) > 0
            ):
                status_code = 207
            else:
                status_code = 400
            return jsonify(results), status_code
        except Exception as e:
            logger.exception("File import failed")
            return jsonify({"error": f"File import failed: {str(e)}"}), 500
