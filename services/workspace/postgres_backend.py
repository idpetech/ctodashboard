"""
Postgres-backed workspace operations — delegates to secure_db only.

See docs/POSTGRES-SINGLE-SOURCE-PLAN.md
"""

from datetime import datetime
from typing import Any, Dict, Optional

from services.security.secure_database import secure_db


class PostgresWorkspaceBackend:
    """Thin facade over SecureDatabaseManager for workspace/assignment CRUD."""

    def __init__(self):
        self.db = secure_db

    def create_workspace(
        self, workspace_id: str, name: str, description: str = ""
    ) -> Dict[str, Any]:
        if self.db.get_workspace(workspace_id):
            return {
                "success": False,
                "error": f"Workspace '{workspace_id}' already exists",
            }
        settings = {"connector_templates": {}, "status": "active"}
        if not self.db.store_workspace(workspace_id, name, description, settings=settings):
            return {"success": False, "error": "Failed to create workspace in database"}
        workspace = self.db.get_workspace_api_dict(workspace_id)
        return {
            "success": True,
            "workspace": workspace,
            "message": f"Workspace '{workspace_id}' created successfully",
        }

    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        workspace = self.db.get_workspace_api_dict(workspace_id)
        if not workspace:
            return {"error": f"Workspace '{workspace_id}' not found"}
        return workspace

    def list_workspaces(self) -> Dict[str, Any]:
        return {"workspaces": self.db.list_workspaces()}

    def delete_workspace(self, workspace_id: str) -> Dict[str, Any]:
        if not self.db.get_workspace(workspace_id):
            return {"success": False, "error": f"Workspace '{workspace_id}' not found"}
        count = len(self.db.get_workspace_assignments(workspace_id))
        if not self.db.delete_workspace(workspace_id):
            return {"success": False, "error": "Failed to delete workspace"}
        return {
            "success": True,
            "message": f"Workspace '{workspace_id}' deleted with {count} assignments",
        }

    def add_assignment(
        self, workspace_id: str, assignment_id: str, assignment_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.db.get_workspace(workspace_id):
            return {"success": False, "error": f"Workspace '{workspace_id}' not found"}
        if self.db.get_assignment(workspace_id, assignment_id):
            return {
                "success": False,
                "error": f"Assignment '{assignment_id}' already exists in workspace '{workspace_id}'",
            }
        assignment_data = {
            "assignment_id": assignment_id,
            "id": assignment_id,
            "workspace_id": workspace_id,
            "created_at": datetime.now().isoformat(),
            **assignment_config,
        }
        if not self.db.store_assignment(assignment_data):
            return {"success": False, "error": "Failed to store assignment"}
        return {
            "success": True,
            "assignment": assignment_data,
            "message": f"Assignment '{assignment_id}' added to workspace '{workspace_id}'",
        }

    def get_workspace_assignments(self, workspace_id: str) -> Dict[str, Any]:
        if not self.db.get_workspace(workspace_id):
            return {"error": f"Workspace '{workspace_id}' not found"}
        return {"assignments": self.db.get_workspace_assignments(workspace_id)}

    def get_assignment(self, workspace_id: str, assignment_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_assignment(workspace_id, assignment_id)

    def find_assignment(
        self, assignment_id: str, workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        matches = self.db.find_assignment(assignment_id, workspace_id)
        if workspace_id:
            if matches:
                return {
                    "workspace_id": workspace_id,
                    "assignment": matches[0]["assignment"],
                    "status": 200,
                }
            return {
                "error": f"Assignment '{assignment_id}' not found in workspace '{workspace_id}'",
                "status": 404,
            }
        if not matches:
            return {
                "error": f"Assignment '{assignment_id}' not found in any workspace",
                "status": 404,
            }
        if len(matches) > 1:
            ids = [m["workspace_id"] for m in matches]
            return {
                "error": f"Assignment '{assignment_id}' found in multiple workspaces: {ids}. Please specify workspace_id parameter.",
                "ambiguous_workspaces": ids,
                "status": 409,
            }
        return {
            "workspace_id": matches[0]["workspace_id"],
            "assignment": matches[0]["assignment"],
            "status": 200,
        }

    def update_assignment(
        self, workspace_id: str, assignment_id: str, assignment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        existing = self.db.get_assignment(workspace_id, assignment_id)
        if not existing:
            return {
                "success": False,
                "error": f"Assignment '{assignment_id}' not found in workspace '{workspace_id}'",
            }
        updated = {**existing, **assignment_data}
        updated["workspace_id"] = workspace_id
        updated["assignment_id"] = assignment_id
        updated["id"] = assignment_id
        updated["updated_at"] = datetime.now().isoformat()
        if not self.db.store_assignment(updated):
            return {"success": False, "error": "Failed to update assignment"}
        return {
            "success": True,
            "assignment": updated,
            "message": f"Assignment '{assignment_id}' updated successfully",
        }

    def archive_assignment(self, workspace_id: str, assignment_id: str) -> Dict[str, Any]:
        return self.update_assignment(workspace_id, assignment_id, {"status": "archived"})

    def delete_assignment(self, workspace_id: str, assignment_id: str) -> Dict[str, Any]:
        existing = self.db.get_assignment(workspace_id, assignment_id)
        if not existing:
            return {
                "success": False,
                "error": f"Assignment '{assignment_id}' not found in workspace '{workspace_id}'",
            }
        if not self.db.delete_assignment(workspace_id, assignment_id):
            return {"success": False, "error": "Failed to delete assignment"}
        return {
            "success": True,
            "message": f"Assignment '{assignment_id}' deleted permanently",
        }

    def update_workspace_settings(
        self, workspace_id: str, settings_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        workspace = self.db.get_workspace(workspace_id)
        if not workspace:
            return {"success": False, "error": f"Workspace '{workspace_id}' not found"}
        settings = workspace.get("settings") or {}
        if "status" in settings_data:
            settings["status"] = settings_data["status"]
        name = settings_data.get("name", workspace["name"])
        description = settings_data.get("description", workspace.get("description") or "")
        if "connector_templates" in settings_data:
            settings["connector_templates"] = settings_data["connector_templates"]
        if "ctolens_schedule" in settings_data:
            from services.ctolens_run_metadata import normalize_schedule, validate_schedule

            merged = normalize_schedule(
                {**(settings.get("ctolens_schedule") or {}), **settings_data["ctolens_schedule"]}
            )
            validate_schedule(merged)
            settings["ctolens_schedule"] = merged
        settings["updated_at"] = datetime.now().isoformat()
        self.db.store_workspace(workspace_id, name, description, settings=settings)
        api_ws = self.db.get_workspace_api_dict(workspace_id)
        return {
            "success": True,
            "workspace": api_ws,
            "message": "Workspace settings updated successfully",
        }

    def _load_settings(self, workspace_id: str) -> Dict[str, Any]:
        ws = self.db.get_workspace(workspace_id)
        if not ws:
            return {}
        return ws.get("settings") or {}

    def _save_settings(
        self, workspace_id: str, settings: Dict[str, Any], name: str = None, description: str = None
    ) -> bool:
        ws = self.db.get_workspace(workspace_id)
        if not ws:
            return False
        return self.db.store_workspace(
            workspace_id,
            name or ws["name"],
            description if description is not None else ws.get("description") or "",
            settings=settings,
        )

    def create_connector_template(
        self,
        workspace_id: str,
        connector_type: str,
        template_name: str,
        template_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        settings = self._load_settings(workspace_id)
        templates = settings.setdefault("connector_templates", {})
        templates.setdefault(connector_type, {})[template_name] = template_data
        if not self._save_settings(workspace_id, settings):
            return {"success": False, "error": "Failed to save template"}
        return {
            "success": True,
            "template": template_data,
            "message": f"Connector template '{template_name}' created for {connector_type}",
        }

    def get_connector_templates(
        self, workspace_id: str, connector_type: str = None
    ) -> Dict[str, Any]:
        settings = self._load_settings(workspace_id)
        all_templates = settings.get("connector_templates", {})
        if connector_type:
            return {"templates": {connector_type: all_templates.get(connector_type, {})}}
        return {"templates": all_templates}

    def get_connector_template(
        self, workspace_id: str, connector_type: str, template_name: str
    ) -> Dict[str, Any]:
        templates = self.get_connector_templates(workspace_id, connector_type).get("templates", {})
        ct = templates.get(connector_type, {})
        if template_name not in ct:
            return {"error": f"Template '{template_name}' not found"}
        return {"template": ct[template_name]}

    def delete_connector_template(
        self, workspace_id: str, connector_type: str, template_name: str
    ) -> Dict[str, Any]:
        settings = self._load_settings(workspace_id)
        templates = settings.get("connector_templates", {})
        if connector_type in templates and template_name in templates[connector_type]:
            del templates[connector_type][template_name]
            self._save_settings(workspace_id, settings)
            return {"success": True, "message": "Template deleted"}
        return {"success": False, "error": "Template not found"}
