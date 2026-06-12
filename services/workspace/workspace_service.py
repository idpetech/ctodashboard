# Workspace API facade — Postgres only (postgres_backend → secure_db).
# config/connectors/*.json = connector field schemas only (not user/workspace data).
# See docs/POSTGRES-SINGLE-SOURCE-PLAN.md
"""
Workspace Service — CRUD and connector templates via Postgres.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .postgres_backend import PostgresWorkspaceBackend

logger = logging.getLogger(__name__)


class WorkspaceService:
    """Workspace and assignment operations backed by Postgres."""

    def __init__(self):
        self.feature_enabled = os.getenv("ENABLE_WORKSPACES", "true").lower() == "true"
        self._store = PostgresWorkspaceBackend()

    def is_workspace_enabled(self) -> bool:
        return self.feature_enabled

    def create_workspace(
        self, workspace_id: str, name: str, description: str = ""
    ) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled. Set ENABLE_WORKSPACES=true",
            }
        return self._store.create_workspace(workspace_id, name, description)

    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"error": "Workspace functionality is disabled"}
        return self._store.get_workspace(workspace_id)

    def list_workspaces(self) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"workspaces": [], "message": "Workspace functionality is disabled"}
        return self._store.list_workspaces()

    def add_assignment_to_workspace(
        self, workspace_id: str, assignment_id: str, assignment_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.add_assignment(workspace_id, assignment_id, assignment_config)

    def get_workspace_assignments(self, workspace_id: str) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"assignments": [], "error": "Workspace functionality is disabled"}
        return self._store.get_workspace_assignments(workspace_id)

    def delete_workspace(self, workspace_id: str) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.delete_workspace(workspace_id)

    # ===== PHASE 2: CONNECTOR TEMPLATE SYSTEM =====

    def create_connector_template(
        self,
        workspace_id: str,
        connector_type: str,
        template_name: str,
        template_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a connector template for a workspace.
        Phase 2: Template system for reusable connector configurations.
        """
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}

        # Get workspace
        workspace = self.get_workspace(workspace_id)
        if "error" in workspace:
            return {"success": False, "error": workspace["error"]}

        # Validate connector type
        supported_connectors = ["github", "jira", "aws", "railway", "openai"]
        if connector_type not in supported_connectors:
            return {
                "success": False,
                "error": f"Unsupported connector type: {connector_type}. Supported: {supported_connectors}",
            }

        # Load connector configuration from JSON file
        connector_config = self._load_connector_config(connector_type)
        if not connector_config:
            return {
                "success": False,
                "error": f"Connector configuration not found for {connector_type}",
            }

        # Create template structure (NO actual credentials, only requirements)
        template_data = {
            "name": template_name,
            "type": connector_type,
            "config": {
                **connector_config.get("default_config", {}),
                **template_config,  # Override defaults with provided config
            },
            "auth_requirements": {
                "required_fields": connector_config.get("credential_fields", {}),
                "setup_instructions": connector_config.get("auth_config", {}).get(
                    "setup_instructions", {}
                ),
                "auth_type": connector_config.get("auth_config", {}).get("auth_type", "unknown"),
                "documentation_url": connector_config.get("auth_config", {})
                .get("setup_instructions", {})
                .get("documentation_url", ""),
            },
            "config_schema": connector_config.get("config_schema", {}),
            "created_at": datetime.now().isoformat(),
            "workspace_id": workspace_id,
            "description": template_config.get(
                "description",
                connector_config.get("description", f"{connector_type.title()} connector template"),
            ),
        }

        # Add to workspace templates
        if "connector_templates" not in workspace:
            workspace["connector_templates"] = {}

        if connector_type not in workspace["connector_templates"]:
            workspace["connector_templates"][connector_type] = {}

        return self._store.create_connector_template(
            workspace_id, connector_type, template_name, template_data
        )

    def get_connector_templates(
        self, workspace_id: str, connector_type: str = None
    ) -> Dict[str, Any]:
        """Get connector templates for a workspace"""
        if not self.feature_enabled:
            return {"templates": {}, "error": "Workspace functionality is disabled"}

        workspace = self.get_workspace(workspace_id)
        if "error" in workspace:
            return {"error": workspace["error"]}

        templates = workspace.get("connector_templates", {})

        if connector_type:
            # Return templates for specific connector type
            return {
                "templates": templates.get(connector_type, {}),
                "connector_type": connector_type,
            }
        else:
            # Return all templates
            return {"templates": templates}

    def get_connector_template(
        self, workspace_id: str, connector_type: str, template_name: str
    ) -> Dict[str, Any]:
        """Get a specific connector template"""
        if not self.feature_enabled:
            return {"error": "Workspace functionality is disabled"}

        templates_result = self.get_connector_templates(workspace_id, connector_type)
        if "error" in templates_result:
            return templates_result

        templates = templates_result.get("templates", {})
        template = templates.get(template_name)

        if not template:
            return {
                "error": f"Template '{template_name}' not found for {connector_type} in workspace '{workspace_id}'"
            }

        return template

    def delete_connector_template(
        self, workspace_id: str, connector_type: str, template_name: str
    ) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.delete_connector_template(workspace_id, connector_type, template_name)

    def create_assignment_from_template(
        self,
        workspace_id: str,
        assignment_id: str,
        assignment_config: Dict[str, Any],
        templates: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Create assignment using connector templates.
        Phase 2: Template-based assignment creation.

        Args:
            workspace_id: Target workspace
            assignment_id: New assignment ID
            assignment_config: Basic assignment config (name, description, etc.)
            templates: Dict mapping connector_type -> template_name to use
        """
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}

        if not templates:
            # Fall back to regular assignment creation
            return self.add_assignment_to_workspace(workspace_id, assignment_id, assignment_config)

        # Get workspace templates
        workspace_templates_result = self.get_connector_templates(workspace_id)
        if "error" in workspace_templates_result:
            return {"success": False, "error": workspace_templates_result["error"]}

        workspace_templates = workspace_templates_result.get("templates", {})

        # Build metrics_config from templates
        metrics_config = {}

        for connector_type, template_name in templates.items():
            if connector_type not in workspace_templates:
                return {
                    "success": False,
                    "error": f"No templates found for connector type '{connector_type}' in workspace",
                }

            if template_name not in workspace_templates[connector_type]:
                return {
                    "success": False,
                    "error": f"Template '{template_name}' not found for {connector_type}",
                }

            # Get template config
            template = workspace_templates[connector_type][template_name]
            template_config = template.get("config", {})

            # Apply template config + add auth instance placeholder
            metrics_config[connector_type] = {
                **template_config,
                "enabled": True,  # Enable by default when using template
                "template_used": template_name,  # Track which template was used
                "auth_instance": {
                    # This is where actual credentials would go per assignment
                    "auth_type": template.get("auth_requirements", {}).get("auth_type", "unknown"),
                    "credentials": {},  # To be filled with actual tokens/keys
                    "auth_configured": False,  # Flag to indicate if auth is set up
                    "auth_reference": f"{workspace_id}_{assignment_id}_{connector_type}_auth",
                },
            }

        # Merge template-generated config with provided config
        final_config = {
            **assignment_config,
            "metrics_config": {**assignment_config.get("metrics_config", {}), **metrics_config},
            "created_from_templates": templates,  # Track template usage
        }

        # Create the assignment
        return self.add_assignment_to_workspace(workspace_id, assignment_id, final_config)

    def _load_connector_config(self, connector_type: str) -> Optional[Dict[str, Any]]:
        """Load connector configuration from JSON file"""
        config_file = Path("config/connectors") / f"{connector_type}.json"

        if not config_file.exists():
            return None

        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not load connector config for %s: %s", connector_type, e)
            return None

    def _generate_env_mapping(
        self, credential_fields: Dict[str, Any], workspace_id: str
    ) -> Dict[str, str]:
        """Generate environment variable mapping from credential field patterns"""
        env_mapping = {}

        for field_key, field_config in credential_fields.items():
            field_name = field_config.get("field_name")
            env_pattern = field_config.get("env_var_pattern")

            if field_name and env_pattern:
                # Replace {workspace_id} placeholder with actual workspace ID
                env_var = env_pattern.replace("{workspace_id}", workspace_id.upper())
                env_mapping[field_name] = env_var

        return env_mapping

    def update_assignment_auth(
        self,
        workspace_id: str,
        assignment_id: str,
        connector_type: str,
        credentials: Dict[str, str],
    ) -> Dict[str, Any]:
        """Store credentials in Postgres; metadata flags only in metrics_config."""
        from services.security.secure_database import secure_db

        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        if not credentials or not any(credentials.values()):
            return {"success": False, "error": "No credentials provided"}

        assignment = self._store.get_assignment(workspace_id, assignment_id)
        if not assignment:
            return {"success": False, "error": f"Assignment '{assignment_id}' not found"}

        metrics_config = assignment.get("metrics_config", {})
        if connector_type not in metrics_config:
            return {"success": False, "error": f"Connector '{connector_type}' not in assignment"}

        if not secure_db.store_assignment_credentials(
            workspace_id, assignment_id, connector_type, credentials
        ):
            return {"success": False, "error": "Failed to store credentials"}

        metrics_config[connector_type].setdefault("auth_instance", {}).update(
            {
                "auth_configured": True,
                "credentials": {},
                "last_updated": datetime.now().isoformat(),
            }
        )
        assignment["metrics_config"] = metrics_config
        return self._store.update_assignment(workspace_id, assignment_id, assignment)

    def update_workspace_settings(
        self, workspace_id: str, settings_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.update_workspace_settings(workspace_id, settings_data)

    def clear_assignment_auth(
        self, workspace_id: str, assignment_id: str, connector_type: str
    ) -> Dict[str, Any]:
        from services.security.secure_database import secure_db

        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}

        secure_db.delete_assignment_credentials(workspace_id, assignment_id, connector_type)
        assignment = self._store.get_assignment(workspace_id, assignment_id)
        if assignment:
            metrics_config = assignment.get("metrics_config", {})
            if connector_type in metrics_config:
                metrics_config[connector_type].setdefault("auth_instance", {}).update(
                    {
                        "credentials": {},
                        "auth_configured": False,
                        "cleared_at": datetime.now().isoformat(),
                    }
                )
                assignment["metrics_config"] = metrics_config
                self._store.update_assignment(workspace_id, assignment_id, assignment)
        return {
            "success": True,
            "message": f"Auth credentials cleared for {connector_type}",
            "auth_status": "not_configured",
        }

    # ===== WORKSPACE-ONLY CRUD METHODS (Phase 1) =====
    # These methods provide workspace store as single source of truth

    def get_assignment(self, workspace_id: str, assignment_id: str) -> Optional[Dict[str, Any]]:
        if not self.feature_enabled:
            return None
        return self._store.get_assignment(workspace_id, assignment_id)

    def find_assignment(
        self, assignment_id: str, workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"error": "Workspace functionality is disabled", "status": 500}
        return self._store.find_assignment(assignment_id, workspace_id)

    def update_assignment(
        self, workspace_id: str, assignment_id: str, assignment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.update_assignment(workspace_id, assignment_id, assignment_data)

    def archive_assignment(self, workspace_id: str, assignment_id: str) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.archive_assignment(workspace_id, assignment_id)

    def delete_assignment(self, workspace_id: str, assignment_id: str) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.delete_assignment(workspace_id, assignment_id)

    def list_workspace_portfolios(self, workspace_id: str) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"portfolios": [], "error": "Workspace functionality is disabled"}
        return self._store.list_workspace_portfolios(workspace_id)

    def create_workspace_portfolio(
        self,
        workspace_id: str,
        name: str,
        description: str = "",
        sort_order: Optional[int] = None,
        portfolio_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.create_workspace_portfolio(
            workspace_id, name, description, sort_order, portfolio_id
        )

    def update_workspace_portfolio(
        self,
        workspace_id: str,
        portfolio_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.update_workspace_portfolio(
            workspace_id, portfolio_id, name=name, description=description, sort_order=sort_order
        )

    def delete_workspace_portfolio(self, workspace_id: str, portfolio_id: str) -> Dict[str, Any]:
        if not self.feature_enabled:
            return {"success": False, "error": "Workspace functionality is disabled"}
        return self._store.delete_workspace_portfolio(workspace_id, portfolio_id)
