"""
Data Import Service - Phase 2 Implementation
Augments existing CTO Dashboard functionality with enhanced import capabilities
Compatible with Phase 1 Export Service format
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from services.import_parser import file_content_hash, parse_spreadsheet
from services.portfolio_scope_service import DEFAULT_PORTFOLIO_ID, merge_imported_portfolios
from services.security.secure_database import secure_db
from services.workspace.workspace_service import WorkspaceService

logger = get_logger(__name__)


class DataImportService:
    """
    Import service that works with both legacy and new export formats.
    Augments existing import functionality with validation and compatibility.
    """

    def __init__(self):
        self.workspace_service = WorkspaceService()
        self.secure_db = secure_db  # Use singleton instance

        logger.info(
            "DataImportService initialized with singleton database instance",
            extra={"operation": "service_init", "service": "data_import", "singleton_used": True},
        )

    def validate_import_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate imported data structure and normalize format.
        Handles both legacy and new export formats.
        """
        try:
            validation_result = {
                "valid": True,
                "format_version": "unknown",
                "normalized_data": data,
                "warnings": [],
                "errors": [],
            }

            # Check for new format (from our Phase 1 export)
            if "export_metadata" in data and "export_version" in data["export_metadata"]:
                # New format from our export service
                validation_result["format_version"] = data["export_metadata"]["export_version"]

                # Normalize to legacy format for compatibility
                normalized = {
                    "export_version": data["export_metadata"]["export_version"],
                    "workspace_id": data["export_metadata"].get("workspace_id"),
                    "assignments": data.get("assignments", []),
                    "workspace_info": data.get("workspace_info", {}),
                    "metadata": data["export_metadata"],
                }
                validation_result["normalized_data"] = normalized

            # Check for legacy format
            elif "export_version" in data:
                validation_result["format_version"] = data["export_version"]
                validation_result["normalized_data"] = data

            else:
                # Try to handle data without version (legacy)
                if "assignments" in data:
                    validation_result["warnings"].append(
                        "No version info found, assuming legacy format"
                    )
                    validation_result["format_version"] = "1.0"
                    validation_result["normalized_data"] = {
                        "export_version": "1.0",
                        "assignments": data.get("assignments", []),
                        "workspace_info": data.get("workspace_info", {}),
                        "metadata": {"legacy_import": True},
                    }
                else:
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        "Invalid import format - no recognizable structure"
                    )
                    return validation_result

            # Validate version compatibility
            supported_versions = ["1.0"]
            if validation_result["format_version"] not in supported_versions:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Unsupported export version: {validation_result['format_version']}. "
                    f"Supported versions: {', '.join(supported_versions)}"
                )
                return validation_result

            # Validate assignments structure
            assignments = validation_result["normalized_data"].get("assignments", [])
            for i, assignment in enumerate(assignments):
                if not assignment.get("assignment_id") and not assignment.get("id"):
                    validation_result["errors"].append(f"Assignment {i + 1} missing ID field")

                # Normalize ID field
                if "assignment_id" in assignment and "id" not in assignment:
                    assignment["id"] = assignment["assignment_id"]
                elif "id" in assignment and "assignment_id" not in assignment:
                    assignment["assignment_id"] = assignment["id"]

            if validation_result["errors"]:
                validation_result["valid"] = False

            return validation_result

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                "valid": False,
                "format_version": "unknown",
                "normalized_data": {},
                "warnings": [],
                "errors": [f"Validation failed: {str(e)}"],
            }

    def import_workspace_data(
        self, workspace_id: str, data: Dict[str, Any], import_mode: str = "create_new"
    ) -> Dict[str, Any]:
        """
        Import workspace data with enhanced validation and conflict resolution.
        Compatible with existing import functionality.
        """
        try:
            # First validate the data
            validation = self.validate_import_data(data)
            if not validation["valid"]:
                return {
                    "success": False,
                    "errors": validation["errors"],
                    "warnings": validation["warnings"],
                }

            normalized_data = validation["normalized_data"]
            import_assignments = normalized_data.get("assignments", [])

            results = {
                "success": True,
                "imported_assignments": 0,
                "skipped_assignments": 0,
                "updated_assignments": 0,
                "errors": validation["errors"].copy(),
                "warnings": validation["warnings"].copy(),
                "details": [],
                "import_mode": import_mode,
                "format_version": validation["format_version"],
            }

            # Import workspace info if available
            workspace_info = normalized_data.get("workspace_info", {})
            if workspace_info and import_mode in ["overwrite", "merge"]:
                try:
                    self._import_workspace_info(workspace_id, workspace_info)
                    results["details"].append("Workspace info imported successfully")
                except Exception as e:
                    results["warnings"].append(f"Failed to import workspace info: {str(e)}")

            # Import assignments
            for assignment_data in import_assignments:
                assignment_id = assignment_data.get("assignment_id") or assignment_data.get("id")
                if not assignment_id:
                    results["errors"].append("Assignment missing ID - skipped")
                    results["skipped_assignments"] += 1
                    continue

                try:
                    import_result = self._import_single_assignment(
                        workspace_id, assignment_id, assignment_data, import_mode
                    )

                    if import_result["success"]:
                        if import_result["action"] == "created":
                            results["imported_assignments"] += 1
                        elif import_result["action"] == "updated":
                            results["updated_assignments"] += 1
                        elif import_result["action"] == "skipped":
                            results["skipped_assignments"] += 1
                        results["details"].append(import_result["message"])
                    else:
                        results["errors"].append(import_result["message"])
                        results["skipped_assignments"] += 1

                except Exception as e:
                    error_msg = f"Error importing {assignment_id}: {str(e)}"
                    results["errors"].append(error_msg)
                    results["skipped_assignments"] += 1
                    logger.error(error_msg)

            # Update overall success status
            total_processed = (
                results["imported_assignments"]
                + results["updated_assignments"]
                + results["skipped_assignments"]
            )
            if total_processed == 0:
                results["success"] = len(results["errors"]) == 0
            else:
                # Success if more than 50% of assignments were processed successfully
                success_count = results["imported_assignments"] + results["updated_assignments"]
                results["success"] = success_count >= (total_processed / 2)

            # Log import action
            self._log_import_action(workspace_id, results, normalized_data.get("metadata", {}))

            return results

        except Exception as e:
            error_msg = f"Import failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "imported_assignments": 0,
                "skipped_assignments": 0,
                "updated_assignments": 0,
                "errors": [error_msg],
                "warnings": [],
                "details": [],
                "import_mode": import_mode,
            }

    def _import_single_assignment(
        self,
        workspace_id: str,
        assignment_id: str,
        assignment_data: Dict[str, Any],
        import_mode: str,
    ) -> Dict[str, Any]:
        """Import a single assignment with conflict resolution"""
        try:
            # Check if assignment already exists
            existing = self._get_assignment_from_db(workspace_id, assignment_id)

            if existing and import_mode == "create_new":
                # Do not duplicate — skip rows that already exist in this workspace
                return {
                    "success": True,
                    "action": "skipped",
                    "message": f"Skipped existing assignment: {assignment_id}",
                    "assignment_id": assignment_id,
                }

            # Prepare assignment data for database
            db_data = {
                "assignment_id": assignment_id,
                "workspace_id": workspace_id,
                "name": assignment_data.get("name", assignment_id),
                "description": assignment_data.get("description", ""),
                "team_size": assignment_data.get("team_size"),
                "monthly_burn_rate": assignment_data.get("monthly_burn_rate"),
                "target_monthly_burn": assignment_data.get("target_monthly_burn"),
                "status": assignment_data.get("status", "active"),
                "portfolio_id": assignment_data.get("portfolio_id") or DEFAULT_PORTFOLIO_ID,
                "metrics_config": json.dumps(assignment_data.get("metrics_config", {}))
                if assignment_data.get("metrics_config")
                else None,
            }

            if existing:
                if import_mode == "merge":
                    # Merge with existing data, keeping existing values where new ones are None
                    for key, value in db_data.items():
                        if value is None and key in existing:
                            db_data[key] = existing[key]

                # Update existing assignment
                success = self._update_assignment_in_db(workspace_id, assignment_id, db_data)
                action = "updated"
                message = f"Updated assignment: {db_data['name']}"

            else:
                # Create new assignment
                success = self._create_assignment_in_db(db_data)
                action = "created"
                message = f"Created assignment: {db_data['name']}"

            return {
                "success": success,
                "action": action,
                "message": message,
                "assignment_id": assignment_id,
            }

        except Exception as e:
            return {
                "success": False,
                "action": "error",
                "message": f"Failed to import {assignment_id}: {str(e)}",
                "assignment_id": assignment_id,
            }

    def _create_assignment_in_db(self, assignment_data: Dict[str, Any]) -> bool:
        """Create assignment via canonical postgres_store (no raw SQL)."""
        payload = dict(assignment_data)
        if isinstance(payload.get("metrics_config"), str):
            try:
                payload["metrics_config"] = json.loads(payload["metrics_config"])
            except json.JSONDecodeError:
                payload["metrics_config"] = {}
        return self.secure_db.store_assignment(payload)

    def _update_assignment_in_db(
        self, workspace_id: str, assignment_id: str, assignment_data: Dict[str, Any]
    ) -> bool:
        """Update assignment via canonical postgres_store."""
        payload = dict(assignment_data)
        payload["workspace_id"] = workspace_id
        payload["assignment_id"] = assignment_id
        if isinstance(payload.get("metrics_config"), str):
            try:
                payload["metrics_config"] = json.loads(payload["metrics_config"])
            except json.JSONDecodeError:
                payload["metrics_config"] = {}
        return self.secure_db.store_assignment(payload)

    def _get_assignment_from_db(
        self, workspace_id: str, assignment_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get assignment from canonical postgres_store."""
        return self.secure_db.get_assignment(workspace_id, assignment_id)

    def _import_workspace_info(self, workspace_id: str, workspace_info: Dict[str, Any]):
        """Import workspace metadata via canonical postgres_store."""
        incoming_settings = dict(workspace_info.get("settings") or {})
        if workspace_info.get("connector_templates"):
            incoming_settings["connector_templates"] = workspace_info["connector_templates"]
        if workspace_info.get("portfolios"):
            incoming_settings = merge_imported_portfolios(
                incoming_settings, workspace_info.get("portfolios") or []
            )

        existing = self.secure_db.get_workspace(workspace_id)
        if existing:
            merged = dict(existing.get("settings") or {})
            if workspace_info.get("portfolios"):
                merged = merge_imported_portfolios(merged, workspace_info.get("portfolios") or [])
            if incoming_settings.get("connector_templates"):
                merged["connector_templates"] = incoming_settings["connector_templates"]
            self.secure_db.store_workspace(
                workspace_id,
                existing.get("name", workspace_id),
                existing.get("description") or "",
                settings=merged,
            )
            return

        self.secure_db.store_workspace(
            workspace_id,
            workspace_info.get("name", workspace_id),
            workspace_info.get("description", ""),
            settings=incoming_settings,
        )

    def _log_import_action(
        self, workspace_id: str, results: Dict[str, Any], metadata: Dict[str, Any]
    ):
        """Log import action via canonical audit_logs table."""
        try:
            self.secure_db.record_audit_event(
                "import",
                "workspace",
                f"imported_{results.get('imported_assignments', 0)}_assignments",
                workspace_id=workspace_id,
                success=bool(results.get("success")),
                audit_info={"user_email": metadata.get("imported_by", "system")},
            )

        except Exception as e:
            logger.error(f"Failed to log import action: {str(e)}")

    def import_from_spreadsheet(
        self,
        workspace_id: str,
        file_content: bytes,
        filename: str,
        import_mode: str = "create_new",
        force: bool = False,
        run_attention: bool = True,
    ) -> Dict[str, Any]:
        """
        Import assignments from a CSV or Excel file.

        Idempotent: identical file content (SHA-256) is skipped in create_new
        mode unless force=true.
        """
        content_hash = file_content_hash(file_content)
        parse_result = parse_spreadsheet(file_content, filename)

        response: Dict[str, Any] = {
            "success": False,
            "format": parse_result.get("format"),
            "filename": filename,
            "file_hash": content_hash,
            "rows_total": parse_result.get("rows_total", 0),
            "rows_parsed": parse_result.get("rows_parsed", 0),
            "rows_skipped": parse_result.get("rows_skipped", 0),
            "detected_columns": parse_result.get("detected_columns", []),
            "imported_assignments": 0,
            "updated_assignments": 0,
            "skipped_assignments": 0,
            "errors": list(parse_result.get("errors", [])),
            "warnings": list(parse_result.get("warnings", [])),
            "details": [],
            "import_mode": import_mode,
            "duplicate_file": False,
            "attention_briefing": None,
        }

        if not parse_result.get("assignments"):
            if not response["errors"]:
                response["errors"].append("No valid assignment rows found in file")
            logger.warning("Spreadsheet import failed parsing: %s", filename)
            return response

        # Idempotency check via workspace settings
        if not force and import_mode == "create_new":
            if self._is_duplicate_import(workspace_id, content_hash):
                response["duplicate_file"] = True
                response["warnings"].append(
                    "This exact file was already imported. "
                    "Use force=true or a different import mode to re-import."
                )
                response["success"] = True
                response["details"].append("Skipped duplicate file upload")
                logger.info("Duplicate spreadsheet import skipped: %s", content_hash[:12])
                return response

        # Strip parser-internal fields before persistence
        assignments = []
        for row in parse_result["assignments"]:
            clean = {k: v for k, v in row.items() if not str(k).startswith("_")}
            assignments.append(clean)

        import_payload = {
            "export_version": "1.0",
            "assignments": assignments,
            "workspace_info": {},
            "metadata": {
                "import_source": "spreadsheet",
                "filename": filename,
                "file_hash": content_hash,
                "imported_at": datetime.utcnow().isoformat(),
            },
        }

        import_results = self.import_workspace_data(workspace_id, import_payload, import_mode)

        response.update(
            {
                "success": import_results.get("success", False),
                "imported_assignments": import_results.get("imported_assignments", 0),
                "updated_assignments": import_results.get("updated_assignments", 0),
                "skipped_assignments": import_results.get("skipped_assignments", 0),
                "errors": response["errors"] + import_results.get("errors", []),
                "warnings": response["warnings"] + import_results.get("warnings", []),
                "details": import_results.get("details", []),
                "format_version": import_results.get("format_version"),
            }
        )

        self._record_import_metadata(
            workspace_id,
            content_hash,
            filename,
            response,
            parse_result.get("assignments", []),
        )

        if run_attention and os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true":
            response["ctolens_briefing"] = self._run_ctolens_after_import(workspace_id)
        elif run_attention and os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() == "true":
            response["attention_briefing"] = self._run_attention_after_import(
                workspace_id,
                content_hash,
                filename,
            )

        logger.info(
            "Spreadsheet import complete: ws=%s file=%s imported=%d updated=%d",
            workspace_id,
            filename,
            response["imported_assignments"],
            response["updated_assignments"],
        )
        return response

    def _is_duplicate_import(self, workspace_id: str, content_hash: str) -> bool:
        ws = self.secure_db.get_workspace(workspace_id)
        if not ws:
            return False
        history = (ws.get("settings") or {}).get("import_history") or {}
        return content_hash in history

    def _record_import_metadata(
        self,
        workspace_id: str,
        content_hash: str,
        filename: str,
        results: Dict[str, Any],
        parsed_rows: List[Dict[str, Any]],
    ) -> None:
        try:
            ws = self.secure_db.get_workspace(workspace_id)
            if not ws:
                return
            settings = ws.get("settings") or {}
            history = settings.get("import_history") or {}
            history[content_hash] = {
                "filename": filename,
                "imported_at": datetime.utcnow().isoformat(),
                "rows_parsed": results.get("rows_parsed", 0),
                "imported_assignments": results.get("imported_assignments", 0),
                "updated_assignments": results.get("updated_assignments", 0),
                "import_mode": results.get("import_mode"),
            }
            settings["import_history"] = history
            settings["last_import"] = {
                "filename": filename,
                "file_hash": content_hash,
                "imported_at": datetime.utcnow().isoformat(),
                "rows_parsed": results.get("rows_parsed", 0),
                "parsed_rows_cache": [
                    {k: v for k, v in r.items() if not str(k).startswith("_")}
                    for r in parsed_rows[:200]
                ],
            }
            self.secure_db.store_workspace(
                workspace_id,
                ws.get("name", workspace_id),
                ws.get("description", ""),
                settings=settings,
            )
        except Exception as e:
            logger.error("Failed to record import metadata: %s", e)

    def _run_ctolens_after_import(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        try:
            from services.briefing_pipeline import refresh_workspace_ctolens_briefing

            assignments = self.secure_db.get_workspace_assignments(workspace_id) or []
            return refresh_workspace_ctolens_briefing(
                workspace_id,
                assignments,
                self.secure_db,
                fetch_metrics=False,
            )
        except Exception as e:
            logger.error("CTOLens briefing after import failed: %s", e)
            return None

    def _run_attention_after_import(
        self,
        workspace_id: str,
        content_hash: str,
        filename: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            from services.attention_engine import (
                build_attention_briefing,
                get_stored_briefing,
                store_briefing_in_workspace,
            )

            assignments = self.secure_db.get_workspace_assignments(workspace_id)
            previous = get_stored_briefing(self.secure_db, workspace_id)
            briefing = build_attention_briefing(
                assignments,
                previous_briefing=previous,
                import_metadata={
                    "filename": filename,
                    "file_hash": content_hash,
                    "trigger": "spreadsheet_import",
                },
            )
            store_briefing_in_workspace(self.secure_db, workspace_id, briefing)
            return briefing
        except Exception as e:
            logger.error("Attention engine after import failed: %s", e)
            return None

    def get_import_templates(self) -> List[Dict[str, Any]]:
        """Get available import templates for quick assignment setup"""
        templates = [
            {
                "id": "basic_web_app",
                "name": "Basic Web Application",
                "description": "Standard web app with frontend, backend, and database",
                "template": {
                    "name": "New Web Application",
                    "description": "Basic web application project",
                    "team_size": 3,
                    "monthly_burn_rate": 15000,
                    "status": "active",
                    "metrics_config": {"github": {"enabled": True}, "jira": {"enabled": True}},
                },
            },
            {
                "id": "mobile_app",
                "name": "Mobile Application",
                "description": "Mobile app with backend services",
                "template": {
                    "name": "New Mobile App",
                    "description": "Mobile application project",
                    "team_size": 4,
                    "monthly_burn_rate": 20000,
                    "status": "active",
                    "metrics_config": {
                        "github": {"enabled": True},
                        "jira": {"enabled": True},
                        "aws": {"enabled": True},
                    },
                },
            },
            {
                "id": "data_pipeline",
                "name": "Data Pipeline",
                "description": "Data processing and analytics pipeline",
                "template": {
                    "name": "New Data Pipeline",
                    "description": "Data pipeline and analytics project",
                    "team_size": 2,
                    "monthly_burn_rate": 12000,
                    "status": "active",
                    "metrics_config": {"github": {"enabled": True}, "aws": {"enabled": True}},
                },
            },
        ]
        return templates
