"""
Workspace Service - Phase 0 Foundation
Pure addition, zero impact on existing functionality

This service starts in legacy mode, providing foundation for workspace
functionality without touching existing working code.
"""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

class WorkspaceService:
    """
    Foundation workspace service that starts in legacy compatibility mode.
    
    Phase 0: Read-only analysis and foundation setup
    Future phases will add creation, modification, and migration capabilities.
    """
    
    def __init__(self):
        self.workspace_dir = Path("config/workspaces")
        self.assignments_dir = Path("config/assignments") 
        self.feature_enabled = os.getenv("ENABLE_WORKSPACES", "false").lower() == "true"
        
    def is_workspace_enabled(self) -> bool:
        """Check if workspace functionality is enabled via feature flag"""
        return self.feature_enabled
    
    def get_legacy_assignments(self) -> Dict[str, Any]:
        """
        Read current assignment structure for analysis.
        Pure read-only operation, no modifications.
        """
        assignments = {}
        
        if not self.assignments_dir.exists():
            return assignments
            
        for assignment_file in self.assignments_dir.glob("*.json"):
            try:
                with open(assignment_file, 'r') as f:
                    assignment_data = json.load(f)
                    assignments[assignment_file.stem] = assignment_data
            except Exception as e:
                # Log but don't break - defensive programming
                print(f"Warning: Could not read assignment {assignment_file}: {e}")
                
        return assignments
    
    def analyze_current_structure(self) -> Dict[str, Any]:
        """
        Analyze current assignment structure to understand workspace migration needs.
        Pure analysis, no modifications.
        """
        assignments = self.get_legacy_assignments()
        
        analysis = {
            "total_assignments": len(assignments),
            "connector_types_used": set(),
            "unique_orgs": set(),
            "assignments_by_status": {},
            "metrics_config_patterns": {}
        }
        
        for assignment_id, assignment in assignments.items():
            # Track status distribution
            status = assignment.get("status", "unknown")
            analysis["assignments_by_status"][status] = analysis["assignments_by_status"].get(status, 0) + 1
            
            # Track connector types
            metrics_config = assignment.get("metrics_config", {})
            for connector_type, config in metrics_config.items():
                if config.get("enabled", False):
                    analysis["connector_types_used"].add(connector_type)
                    
                    # Track unique organizations/projects
                    if connector_type == "github" and "org" in config:
                        analysis["unique_orgs"].add(config["org"])
                    
                    # Track configuration patterns
                    if connector_type not in analysis["metrics_config_patterns"]:
                        analysis["metrics_config_patterns"][connector_type] = []
                    analysis["metrics_config_patterns"][connector_type].append({
                        "assignment_id": assignment_id,
                        "config_keys": list(config.keys())
                    })
        
        # Convert sets to lists for JSON serialization
        analysis["connector_types_used"] = list(analysis["connector_types_used"])
        analysis["unique_orgs"] = list(analysis["unique_orgs"])
        
        return analysis
    
    def get_workspace_readiness(self) -> Dict[str, Any]:
        """
        Assess readiness for workspace migration.
        Pure assessment, no changes.
        """
        analysis = self.analyze_current_structure()
        
        readiness = {
            "ready_for_migration": True,
            "warnings": [],
            "recommendations": [],
            "migration_complexity": "low"
        }
        
        # Check for potential issues
        if analysis["total_assignments"] == 0:
            readiness["warnings"].append("No assignments found - nothing to migrate")
            
        if len(analysis["connector_types_used"]) > 3:
            readiness["migration_complexity"] = "medium"
            readiness["recommendations"].append("Consider phased connector migration due to high connector diversity")
            
        if analysis["total_assignments"] > 10:
            readiness["migration_complexity"] = "high" 
            readiness["recommendations"].append("Large number of assignments - recommend batch migration approach")
            
        # Check for missing configurations
        for assignment_id, assignment in self.get_legacy_assignments().items():
            if not assignment.get("metrics_config"):
                readiness["warnings"].append(f"Assignment '{assignment_id}' has no metrics configuration")
                
        return readiness
    
    def preview_workspace_structure(self) -> Dict[str, Any]:
        """
        Preview what workspace structure would look like after migration.
        Pure preview, no actual changes.
        """
        assignments = self.get_legacy_assignments()
        analysis = self.analyze_current_structure()
        
        # Group assignments by organization/company for workspace suggestion
        workspace_suggestions = {}
        
        for assignment_id, assignment in assignments.items():
            # Use company name or fallback to assignment name
            company_name = assignment.get("name", assignment_id)
            workspace_name = company_name.lower().replace(" ", "_").replace("consulting", "").strip("_")
            
            if workspace_name not in workspace_suggestions:
                workspace_suggestions[workspace_name] = {
                    "workspace_id": workspace_name,
                    "name": company_name,
                    "assignments": [],
                    "connector_templates": set()
                }
                
            workspace_suggestions[workspace_name]["assignments"].append(assignment_id)
            
            # Track connector types for templates
            metrics_config = assignment.get("metrics_config", {})
            for connector_type, config in metrics_config.items():
                if config.get("enabled", False):
                    workspace_suggestions[workspace_name]["connector_templates"].add(connector_type)
        
        # Convert sets to lists
        for workspace in workspace_suggestions.values():
            workspace["connector_templates"] = list(workspace["connector_templates"])
            
        return {
            "suggested_workspaces": workspace_suggestions,
            "total_workspaces": len(workspace_suggestions),
            "migration_summary": {
                "assignments_to_migrate": analysis["total_assignments"],
                "connector_types_to_template": len(analysis["connector_types_used"]),
                "estimated_templates_needed": len(analysis["connector_types_used"])
            }
        }
    
    def validate_legacy_compatibility(self) -> Dict[str, Any]:
        """
        Validate that current assignment loading still works perfectly.
        This ensures workspace service doesn't break existing functionality.
        """
        validation = {
            "legacy_loading_works": True,
            "assignments_readable": 0,
            "assignments_with_errors": 0,
            "errors": []
        }
        
        try:
            assignments = self.get_legacy_assignments()
            validation["assignments_readable"] = len(assignments)
            
            # Validate each assignment has required fields
            for assignment_id, assignment in assignments.items():
                required_fields = ["id", "name", "status"]
                missing_fields = [field for field in required_fields if field not in assignment]
                
                if missing_fields:
                    validation["assignments_with_errors"] += 1
                    validation["errors"].append(f"Assignment '{assignment_id}' missing fields: {missing_fields}")
                    
        except Exception as e:
            validation["legacy_loading_works"] = False
            validation["errors"].append(f"Critical error reading assignments: {str(e)}")
            
        return validation
    
    # ===== PHASE 1: WORKSPACE CREATION AND MANAGEMENT =====
    
    def create_workspace(self, workspace_id: str, name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new workspace.
        Phase 1: Basic workspace creation with JSON file storage.
        """
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled. Set ENABLE_WORKSPACES=true"
            }
        
        # Ensure workspace directory exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        workspace_file = self.workspace_dir / f"{workspace_id}.json"
        
        if workspace_file.exists():
            return {
                "success": False,
                "error": f"Workspace '{workspace_id}' already exists"
            }
        
        # Create workspace structure
        workspace_data = {
            "id": workspace_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "assignments": [],
            "connector_templates": {},
            "status": "active"
        }
        
        try:
            with open(workspace_file, 'w') as f:
                json.dump(workspace_data, f, indent=2)
            
            return {
                "success": True,
                "workspace": workspace_data,
                "message": f"Workspace '{workspace_id}' created successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create workspace: {str(e)}"
            }
    
    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace by ID"""
        if not self.feature_enabled:
            return {"error": "Workspace functionality is disabled"}
        
        workspace_file = self.workspace_dir / f"{workspace_id}.json"
        
        if not workspace_file.exists():
            return {"error": f"Workspace '{workspace_id}' not found"}
        
        try:
            with open(workspace_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to read workspace: {str(e)}"}
    
    def list_workspaces(self) -> Dict[str, Any]:
        """List all workspaces"""
        if not self.feature_enabled:
            return {
                "workspaces": [],
                "message": "Workspace functionality is disabled"
            }
        
        if not self.workspace_dir.exists():
            return {"workspaces": []}
        
        workspaces = []
        for workspace_file in self.workspace_dir.glob("*.json"):
            try:
                with open(workspace_file, 'r') as f:
                    workspace_data = json.load(f)
                    # Return summary info for listing
                    workspaces.append({
                        "id": workspace_data.get("id"),
                        "name": workspace_data.get("name"),
                        "description": workspace_data.get("description", ""),
                        "assignment_count": len(workspace_data.get("assignments", [])),
                        "status": workspace_data.get("status", "active"),
                        "created_at": workspace_data.get("created_at")
                    })
            except Exception as e:
                # Log error but continue with other workspaces
                print(f"Warning: Could not read workspace {workspace_file}: {e}")
        
        return {"workspaces": workspaces}
    
    def add_assignment_to_workspace(self, workspace_id: str, assignment_id: str, assignment_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add an assignment to a workspace.
        Phase 1: Basic assignment creation within workspace.
        """
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled"
            }
        
        # Get workspace
        workspace = self.get_workspace(workspace_id)
        if "error" in workspace:
            return {
                "success": False,
                "error": workspace["error"]
            }
        
        # Check if assignment already exists in workspace
        existing_assignments = workspace.get("assignments", [])
        if assignment_id in existing_assignments:
            return {
                "success": False,
                "error": f"Assignment '{assignment_id}' already exists in workspace '{workspace_id}'"
            }
        
        # Create assignment file in workspace-specific directory
        workspace_assignments_dir = self.workspace_dir / workspace_id / "assignments"
        workspace_assignments_dir.mkdir(parents=True, exist_ok=True)
        
        assignment_file = workspace_assignments_dir / f"{assignment_id}.json"
        
        # Prepare assignment data
        assignment_data = {
            "id": assignment_id,
            "workspace_id": workspace_id,
            "created_at": datetime.now().isoformat(),
            **assignment_config
        }
        
        try:
            # Save assignment file
            with open(assignment_file, 'w') as f:
                json.dump(assignment_data, f, indent=2)
            
            # Update workspace to include assignment
            workspace["assignments"].append(assignment_id)
            
            # Save updated workspace
            workspace_file = self.workspace_dir / f"{workspace_id}.json"
            with open(workspace_file, 'w') as f:
                json.dump(workspace, f, indent=2)
            
            return {
                "success": True,
                "assignment": assignment_data,
                "message": f"Assignment '{assignment_id}' added to workspace '{workspace_id}'"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add assignment: {str(e)}"
            }
    
    def get_workspace_assignments(self, workspace_id: str) -> Dict[str, Any]:
        """Get all assignments for a workspace"""
        if not self.feature_enabled:
            return {
                "assignments": [],
                "error": "Workspace functionality is disabled"
            }
        
        workspace = self.get_workspace(workspace_id)
        if "error" in workspace:
            return {"error": workspace["error"]}
        
        assignments = []
        workspace_assignments_dir = self.workspace_dir / workspace_id / "assignments"
        
        if workspace_assignments_dir.exists():
            for assignment_file in workspace_assignments_dir.glob("*.json"):
                try:
                    with open(assignment_file, 'r') as f:
                        assignment_data = json.load(f)
                        assignments.append(assignment_data)
                except Exception as e:
                    print(f"Warning: Could not read assignment {assignment_file}: {e}")
        
        return {"assignments": assignments}
    
    def delete_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """
        Delete a workspace and all its assignments.
        Phase 1: Basic deletion with safety checks.
        """
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled"
            }
        
        workspace_file = self.workspace_dir / f"{workspace_id}.json"
        
        if not workspace_file.exists():
            return {
                "success": False,
                "error": f"Workspace '{workspace_id}' not found"
            }
        
        try:
            # Get assignment count for confirmation
            workspace = self.get_workspace(workspace_id)
            assignment_count = len(workspace.get("assignments", []))
            
            # Delete workspace assignments directory
            import shutil
            workspace_assignments_dir = self.workspace_dir / workspace_id
            if workspace_assignments_dir.exists():
                shutil.rmtree(workspace_assignments_dir)
            
            # Delete workspace file
            workspace_file.unlink()
            
            return {
                "success": True,
                "message": f"Workspace '{workspace_id}' deleted with {assignment_count} assignments"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to delete workspace: {str(e)}"
            }
    
    # ===== PHASE 2: CONNECTOR TEMPLATE SYSTEM =====
    
    def create_connector_template(self, workspace_id: str, connector_type: str, template_name: str, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a connector template for a workspace.
        Phase 2: Template system for reusable connector configurations.
        """
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled"
            }
        
        # Get workspace
        workspace = self.get_workspace(workspace_id)
        if "error" in workspace:
            return {
                "success": False,
                "error": workspace["error"]
            }
        
        # Validate connector type
        supported_connectors = ["github", "jira", "aws", "railway", "openai"]
        if connector_type not in supported_connectors:
            return {
                "success": False,
                "error": f"Unsupported connector type: {connector_type}. Supported: {supported_connectors}"
            }
        
        # Load connector configuration from JSON file
        connector_config = self._load_connector_config(connector_type)
        if not connector_config:
            return {
                "success": False,
                "error": f"Connector configuration not found for {connector_type}"
            }
        
        # Create template structure (NO actual credentials, only requirements)
        template_data = {
            "name": template_name,
            "type": connector_type,
            "config": {
                **connector_config.get("default_config", {}),
                **template_config  # Override defaults with provided config
            },
            "auth_requirements": {
                "required_fields": connector_config.get("credential_fields", {}),
                "setup_instructions": connector_config.get("auth_config", {}).get("setup_instructions", {}),
                "auth_type": connector_config.get("auth_config", {}).get("auth_type", "unknown"),
                "documentation_url": connector_config.get("auth_config", {}).get("setup_instructions", {}).get("documentation_url", "")
            },
            "config_schema": connector_config.get("config_schema", {}),
            "created_at": datetime.now().isoformat(),
            "workspace_id": workspace_id,
            "description": template_config.get("description", connector_config.get("description", f"{connector_type.title()} connector template"))
        }
        
        # Add to workspace templates
        if "connector_templates" not in workspace:
            workspace["connector_templates"] = {}
        
        if connector_type not in workspace["connector_templates"]:
            workspace["connector_templates"][connector_type] = {}
        
        workspace["connector_templates"][connector_type][template_name] = template_data
        
        try:
            # Save updated workspace
            workspace_file = self.workspace_dir / f"{workspace_id}.json"
            with open(workspace_file, 'w') as f:
                json.dump(workspace, f, indent=2)
            
            return {
                "success": True,
                "template": template_data,
                "message": f"Connector template '{template_name}' created for {connector_type}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create template: {str(e)}"
            }
    
    def get_connector_templates(self, workspace_id: str, connector_type: str = None) -> Dict[str, Any]:
        """Get connector templates for a workspace"""
        if not self.feature_enabled:
            return {
                "templates": {},
                "error": "Workspace functionality is disabled"
            }
        
        workspace = self.get_workspace(workspace_id)
        if "error" in workspace:
            return {"error": workspace["error"]}
        
        templates = workspace.get("connector_templates", {})
        
        if connector_type:
            # Return templates for specific connector type
            return {
                "templates": templates.get(connector_type, {}),
                "connector_type": connector_type
            }
        else:
            # Return all templates
            return {"templates": templates}
    
    def get_connector_template(self, workspace_id: str, connector_type: str, template_name: str) -> Dict[str, Any]:
        """Get a specific connector template"""
        if not self.feature_enabled:
            return {"error": "Workspace functionality is disabled"}
        
        templates_result = self.get_connector_templates(workspace_id, connector_type)
        if "error" in templates_result:
            return templates_result
        
        templates = templates_result.get("templates", {})
        template = templates.get(template_name)
        
        if not template:
            return {"error": f"Template '{template_name}' not found for {connector_type} in workspace '{workspace_id}'"}
        
        return template
    
    def delete_connector_template(self, workspace_id: str, connector_type: str, template_name: str) -> Dict[str, Any]:
        """Delete a connector template"""
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled"
            }
        
        workspace = self.get_workspace(workspace_id)
        if "error" in workspace:
            return {
                "success": False,
                "error": workspace["error"]
            }
        
        templates = workspace.get("connector_templates", {})
        
        if connector_type not in templates or template_name not in templates[connector_type]:
            return {
                "success": False,
                "error": f"Template '{template_name}' not found for {connector_type}"
            }
        
        try:
            # Remove template
            del templates[connector_type][template_name]
            
            # Clean up empty connector type
            if not templates[connector_type]:
                del templates[connector_type]
            
            # Save updated workspace
            workspace_file = self.workspace_dir / f"{workspace_id}.json"
            with open(workspace_file, 'w') as f:
                json.dump(workspace, f, indent=2)
            
            return {
                "success": True,
                "message": f"Template '{template_name}' deleted from {connector_type}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to delete template: {str(e)}"
            }
    
    def create_assignment_from_template(self, workspace_id: str, assignment_id: str, assignment_config: Dict[str, Any], templates: Dict[str, str] = None) -> Dict[str, Any]:
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
            return {
                "success": False,
                "error": "Workspace functionality is disabled"
            }
        
        if not templates:
            # Fall back to regular assignment creation
            return self.add_assignment_to_workspace(workspace_id, assignment_id, assignment_config)
        
        # Get workspace templates
        workspace_templates_result = self.get_connector_templates(workspace_id)
        if "error" in workspace_templates_result:
            return {
                "success": False,
                "error": workspace_templates_result["error"]
            }
        
        workspace_templates = workspace_templates_result.get("templates", {})
        
        # Build metrics_config from templates
        metrics_config = {}
        
        for connector_type, template_name in templates.items():
            if connector_type not in workspace_templates:
                return {
                    "success": False,
                    "error": f"No templates found for connector type '{connector_type}' in workspace"
                }
            
            if template_name not in workspace_templates[connector_type]:
                return {
                    "success": False,
                    "error": f"Template '{template_name}' not found for {connector_type}"
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
                    "auth_reference": f"{workspace_id}_{assignment_id}_{connector_type}_auth"
                }
            }
        
        # Merge template-generated config with provided config
        final_config = {
            **assignment_config,
            "metrics_config": {
                **assignment_config.get("metrics_config", {}),
                **metrics_config
            },
            "created_from_templates": templates  # Track template usage
        }
        
        # Create the assignment
        return self.add_assignment_to_workspace(workspace_id, assignment_id, final_config)
    
    def _load_connector_config(self, connector_type: str) -> Optional[Dict[str, Any]]:
        """Load connector configuration from JSON file"""
        config_file = Path("config/connectors") / f"{connector_type}.json"
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load connector config for {connector_type}: {e}")
            return None
    
    def _generate_env_mapping(self, credential_fields: Dict[str, Any], workspace_id: str) -> Dict[str, str]:
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
    
    def update_assignment_auth(self, workspace_id: str, assignment_id: str, connector_type: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Update authentication credentials for a specific assignment's connector.
        This is where actual tokens/keys are stored per assignment.
        """
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled"
            }
        
        # Get assignment
        assignments_result = self.get_workspace_assignments(workspace_id)
        if "error" in assignments_result:
            return {
                "success": False,
                "error": assignments_result["error"]
            }
        
        assignments = assignments_result.get("assignments", [])
        assignment = next((a for a in assignments if a.get("id") == assignment_id), None)
        
        if not assignment:
            return {
                "success": False,
                "error": f"Assignment '{assignment_id}' not found in workspace '{workspace_id}'"
            }
        
        # Check if connector exists in assignment
        metrics_config = assignment.get("metrics_config", {})
        if connector_type not in metrics_config:
            return {
                "success": False,
                "error": f"Connector '{connector_type}' not found in assignment '{assignment_id}'"
            }
        
        try:
            # Update auth instance with actual credentials
            if "auth_instance" not in metrics_config[connector_type]:
                metrics_config[connector_type]["auth_instance"] = {}
            
            metrics_config[connector_type]["auth_instance"].update({
                "credentials": credentials,
                "auth_configured": True,
                "last_updated": datetime.now().isoformat()
            })
            
            # Save updated assignment
            assignment_file = self.workspace_dir / workspace_id / "assignments" / f"{assignment_id}.json"
            with open(assignment_file, 'w') as f:
                json.dump(assignment, f, indent=2)
            
            return {
                "success": True,
                "message": f"Auth credentials updated for {connector_type} in assignment '{assignment_id}'",
                "auth_status": "configured"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to update auth credentials: {str(e)}"
            }
    
