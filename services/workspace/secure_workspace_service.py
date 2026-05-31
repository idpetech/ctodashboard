"""
Secure Workspace Service Integration
Extends workspace service with secure credential management
"""

import json
import copy
from typing import Dict, Any, Optional
from pathlib import Path

from .workspace_service import WorkspaceService
from ..security.credential_manager import credential_manager


class SecureWorkspaceService(WorkspaceService):
    """
    Enhanced workspace service with secure credential management.
    Inherits all workspace functionality but secures credential storage.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credential_manager = credential_manager
    
    def update_assignment_auth(self, workspace_id: str, assignment_id: str, connector_type: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Update authentication credentials for a specific assignment's connector.
        NOW SECURE: Credentials stored encrypted, never in plain text files.
        """
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled"
            }
        
        # Validate credentials are provided
        if not credentials or not any(credentials.values()):
            return {
                "success": False,
                "error": "No credentials provided"
            }
        
        # Store credentials securely (encrypted)
        if not self.credential_manager.store_assignment_credentials(workspace_id, assignment_id, connector_type, credentials):
            return {
                "success": False,
                "error": "Failed to store credentials securely"
            }
        
        # Update assignment metadata (without credentials)
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
                "error": f"Assignment {assignment_id} not found in workspace {workspace_id}"
            }
        
        # Update assignment metadata (auth status but NOT credentials)
        metrics_config = assignment.get("metrics_config", {})
        if connector_type not in metrics_config:
            metrics_config[connector_type] = {
                "enabled": True
            }
        
        # Update auth status metadata
        auth_instance = metrics_config[connector_type].get("auth_instance", {})
        auth_instance.update({
            "auth_configured": True,
            "last_updated": self._get_current_timestamp(),
            "credentials": {}  # Always empty - actual credentials stored securely
        })
        metrics_config[connector_type]["auth_instance"] = auth_instance
        assignment["metrics_config"] = metrics_config
        
        # Save updated assignment (without credentials)
        update_result = self.update_assignment(workspace_id, assignment_id, assignment)
        if "error" in update_result:
            # Rollback credential storage on failure
            self.credential_manager.delete_assignment_credentials(workspace_id, assignment_id, connector_type)
            return {
                "success": False,
                "error": f"Failed to update assignment metadata: {update_result['error']}"
            }
        
        return {
            "success": True,
            "message": f"Credentials securely stored for {connector_type}",
            "auth_configured": True
        }
    
    def get_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str) -> Optional[Dict[str, str]]:
        """
        Retrieve decrypted credentials for assignment connector.
        SECURE: Returns decrypted credentials from secure storage.
        """
        return self.credential_manager.get_assignment_credentials(workspace_id, assignment_id, connector_type)
    
    def clear_assignment_auth(self, workspace_id: str, assignment_id: str, connector_type: str) -> Dict[str, Any]:
        """
        Clear authentication credentials for a specific assignment's connector.
        SECURE: Removes encrypted credentials and updates metadata.
        """
        if not self.feature_enabled:
            return {
                "success": False,
                "error": "Workspace functionality is disabled"
            }
        
        # Delete secure credentials
        if not self.credential_manager.delete_assignment_credentials(workspace_id, assignment_id, connector_type):
            return {
                "success": False,
                "error": "Failed to delete secure credentials"
            }
        
        # Update assignment metadata
        assignments_result = self.get_workspace_assignments(workspace_id)
        if "error" in assignments_result:
            return {
                "success": False,
                "error": assignments_result["error"]
            }
        
        assignments = assignments_result.get("assignments", [])
        assignment = next((a for a in assignments if a.get("id") == assignment_id), None)
        
        if assignment:
            metrics_config = assignment.get("metrics_config", {})
            if connector_type in metrics_config:
                auth_instance = metrics_config[connector_type].get("auth_instance", {})
                auth_instance.update({
                    "auth_configured": False,
                    "last_updated": self._get_current_timestamp(),
                    "credentials": {}  # Always empty
                })
                metrics_config[connector_type]["auth_instance"] = auth_instance
                assignment["metrics_config"] = metrics_config
                
                # Save updated assignment
                self.update_assignment(workspace_id, assignment_id, assignment)
        
        return {
            "success": True,
            "message": f"Credentials cleared for {connector_type}"
        }
    
    def get_workspace_credentials_status(self, workspace_id: str) -> Dict[str, Any]:
        """
        Get status of all credentials in workspace (which connectors are configured).
        SECURE: Returns status only, never actual credentials.
        """
        try:
            assignments_result = self.get_workspace_assignments(workspace_id)
            if "error" in assignments_result:
                return {"error": assignments_result["error"]}
            
            assignments = assignments_result.get("assignments", [])
            credentials_status = {}
            
            for assignment in assignments:
                assignment_id = assignment.get("id")
                credentials_status[assignment_id] = self.credential_manager.list_assignment_credentials(workspace_id, assignment_id)
            
            return {
                "workspace_id": workspace_id,
                "assignments": credentials_status
            }
        except Exception as e:
            return {"error": f"Failed to get credentials status: {str(e)}"}
    
    def validate_connector_credentials(self, connector_type: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate credentials without storing them.
        SECURE: Credentials never written to disk during validation.
        """
        # Import the validation logic from routes
        # This should be moved to a separate service module
        from routes.api_routes import _validate_connector_credentials
        return _validate_connector_credentials(connector_type, credentials)
    
    def get_workspace_assignments(self, workspace_id: str) -> Dict[str, Any]:
        """
        Override parent method to ensure credentials are never included in responses.
        SECURE: All credentials fields are cleaned before returning.
        """
        result = super().get_workspace_assignments(workspace_id)
        
        if "assignments" in result:
            # Clean all credentials from assignments before returning
            cleaned_assignments = []
            for assignment in result["assignments"]:
                cleaned_assignment = self._clean_credentials_from_assignment(assignment)
                cleaned_assignments.append(cleaned_assignment)
            result["assignments"] = cleaned_assignments
        
        return result
    
    def _clean_credentials_from_assignment(self, assignment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove any credential data from assignment object.
        SECURE: Ensures no credentials are leaked in API responses.
        """
        cleaned = copy.deepcopy(assignment)
        
        metrics_config = cleaned.get("metrics_config", {})
        for connector_type, config in metrics_config.items():
            if "auth_instance" in config:
                # Keep auth status but remove any actual credentials
                auth_instance = config["auth_instance"]
                if "credentials" in auth_instance:
                    auth_instance["credentials"] = {}
        
        return cleaned
    
    def migrate_to_secure_storage(self) -> Dict[str, Any]:
        """
        One-time migration from file-based credentials to secure encrypted storage.
        Call this once to migrate existing data.
        """
        migration_report = self.credential_manager.migrate_existing_credentials()
        
        # Clean existing credential files after successful migration
        if migration_report["users_migrated"] > 0 or migration_report["assignments_migrated"] > 0:
            self._clean_legacy_credential_files()
        
        return migration_report
    
    def _clean_legacy_credential_files(self):
        """
        Clean credentials from existing JSON files after migration.
        SECURE: Removes plain text credentials but preserves file structure.
        """
        try:
            # Clean user files
            users_dir = Path("config/users")
            if users_dir.exists():
                for user_file in users_dir.glob("*.json"):
                    if user_file.name != "README.md":
                        with open(user_file, 'r') as f:
                            user_data = json.load(f)
                        
                        # Remove sensitive fields
                        if "password_hash" in user_data:
                            del user_data["password_hash"]
                        if "salt" in user_data:
                            del user_data["salt"]
                        
                        # Write cleaned data back
                        with open(user_file, 'w') as f:
                            json.dump(user_data, f, indent=2)
            
            # Clean assignment files
            workspaces_dir = Path("config/workspaces")
            if workspaces_dir.exists():
                for workspace_dir in workspaces_dir.iterdir():
                    if workspace_dir.is_dir():
                        assignments_dir = workspace_dir / "assignments"
                        if assignments_dir.exists():
                            for assignment_file in assignments_dir.glob("*.json"):
                                with open(assignment_file, 'r') as f:
                                    assignment_data = json.load(f)
                                
                                # Clean all credentials from metrics_config
                                cleaned_assignment = self._clean_credentials_from_assignment(assignment_data)
                                
                                # Write cleaned data back
                                with open(assignment_file, 'w') as f:
                                    json.dump(cleaned_assignment, f, indent=2)
        
        except Exception as e:
            print(f"Error cleaning legacy credential files: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Extended health check including credential security status.
        """
        base_health = super().health_check() if hasattr(super(), 'health_check') else {}
        
        credential_health = self.credential_manager.health_check()
        
        return {
            **base_health,
            "credential_security": credential_health,
            "secure_storage_enabled": True
        }


# Create singleton instance for use throughout application
secure_workspace_service = SecureWorkspaceService()