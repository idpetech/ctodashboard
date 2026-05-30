"""
Secure Credential Manager
Encrypts and stores sensitive credentials separately from git repository
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib


class SecureCredentialManager:
    """
    Secure credential storage with AES encryption.
    Credentials are never stored in plain text.
    Master key derived from environment variable.
    """
    
    def __init__(self):
        self.credentials_dir = Path("config/secrets")
        self.credentials_dir.mkdir(exist_ok=True)
        
        # Ensure secrets directory is never committed
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            with open(gitignore_path, 'a') as f:
                f.write(f"\n# Auto-added by credential manager\n{self.credentials_dir}/\n")
        
        self._fernet = self._get_encryption_key()
    
    def _get_encryption_key(self) -> Fernet:
        """Generate encryption key from environment variable"""
        master_key = os.getenv("CREDENTIAL_MASTER_KEY")
        
        if not master_key:
            # Development fallback - generate from machine-specific data
            # NEVER use this in production
            import platform
            machine_info = f"{platform.node()}{platform.machine()}{platform.processor()}"
            master_key = hashlib.sha256(machine_info.encode()).hexdigest()
            print("⚠️  WARNING: Using development credential key. Set CREDENTIAL_MASTER_KEY environment variable for production!")
        
        # Derive encryption key from master key
        salt = b"ctodashboard_salt_v1"  # Fixed salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def store_user_credentials(self, user_email: str, credentials: Dict[str, Any]) -> bool:
        """Store encrypted user credentials"""
        try:
            # Separate sensitive from non-sensitive data
            sensitive_data = {
                "password_hash": credentials.get("password_hash"),
                "salt": credentials.get("salt"),
            }
            
            non_sensitive_data = {
                "email": credentials.get("email"),
                "display_name": credentials.get("display_name"),
                "created_at": credentials.get("created_at"),
                "last_login": credentials.get("last_login"),
                "workspaces": credentials.get("workspaces", []),
                "role": credentials.get("role"),
                "status": credentials.get("status"),
                "preferences": credentials.get("preferences", {})
            }
            
            # Encrypt sensitive data
            if sensitive_data.get("password_hash"):
                encrypted_data = self._fernet.encrypt(json.dumps(sensitive_data).encode())
                
                # Store encrypted credentials
                cred_file = self.credentials_dir / f"user_{self._safe_filename(user_email)}.enc"
                with open(cred_file, 'wb') as f:
                    f.write(encrypted_data)
            
            # Store non-sensitive data in regular config
            config_file = Path(f"config/users/{user_email}.json")
            config_file.parent.mkdir(exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(non_sensitive_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error storing user credentials: {e}")
            return False
    
    def get_user_credentials(self, user_email: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt user credentials"""
        try:
            # Load non-sensitive data
            config_file = Path(f"config/users/{user_email}.json")
            if not config_file.exists():
                return None
            
            with open(config_file, 'r') as f:
                user_data = json.load(f)
            
            # Load and decrypt sensitive data
            cred_file = self.credentials_dir / f"user_{self._safe_filename(user_email)}.enc"
            if cred_file.exists():
                with open(cred_file, 'rb') as f:
                    encrypted_data = f.read()
                
                decrypted_data = self._fernet.decrypt(encrypted_data)
                sensitive_data = json.loads(decrypted_data.decode())
                
                # Merge data
                user_data.update(sensitive_data)
            
            return user_data
        except Exception as e:
            print(f"Error retrieving user credentials: {e}")
            return None
    
    def store_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str, credentials: Dict[str, Any]) -> bool:
        """Store encrypted assignment connector credentials"""
        try:
            # Encrypt the credentials
            encrypted_data = self._fernet.encrypt(json.dumps(credentials).encode())
            
            # Store in secure location
            cred_file = self.credentials_dir / f"assignment_{self._safe_filename(workspace_id)}_{self._safe_filename(assignment_id)}_{connector_type}.enc"
            with open(cred_file, 'wb') as f:
                f.write(encrypted_data)
            
            return True
        except Exception as e:
            print(f"Error storing assignment credentials: {e}")
            return False
    
    def get_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt assignment connector credentials"""
        try:
            cred_file = self.credentials_dir / f"assignment_{self._safe_filename(workspace_id)}_{self._safe_filename(assignment_id)}_{connector_type}.enc"
            
            if not cred_file.exists():
                return None
            
            with open(cred_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"Error retrieving assignment credentials: {e}")
            return None
    
    def delete_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str) -> bool:
        """Delete assignment connector credentials"""
        try:
            cred_file = self.credentials_dir / f"assignment_{self._safe_filename(workspace_id)}_{self._safe_filename(assignment_id)}_{connector_type}.enc"
            
            if cred_file.exists():
                cred_file.unlink()
            
            return True
        except Exception as e:
            print(f"Error deleting assignment credentials: {e}")
            return False
    
    def list_assignment_credentials(self, workspace_id: str, assignment_id: str) -> Dict[str, bool]:
        """List which connectors have stored credentials for an assignment"""
        connector_status = {}
        connector_types = ['github', 'jira', 'aws', 'openai']
        
        for connector_type in connector_types:
            cred_file = self.credentials_dir / f"assignment_{self._safe_filename(workspace_id)}_{self._safe_filename(assignment_id)}_{connector_type}.enc"
            connector_status[connector_type] = cred_file.exists()
        
        return connector_status
    
    def migrate_existing_credentials(self) -> Dict[str, Any]:
        """
        One-time migration from plain text JSON files to encrypted storage.
        Call this once to migrate existing data, then delete the old files.
        """
        migration_report = {
            "users_migrated": 0,
            "assignments_migrated": 0,
            "errors": []
        }
        
        try:
            # Migrate user credentials
            users_dir = Path("config/users")
            if users_dir.exists():
                for user_file in users_dir.glob("*.json"):
                    if user_file.name == "README.md":
                        continue
                    
                    try:
                        with open(user_file, 'r') as f:
                            user_data = json.load(f)
                        
                        user_email = user_data.get("email")
                        if user_email and self.store_user_credentials(user_email, user_data):
                            migration_report["users_migrated"] += 1
                    except Exception as e:
                        migration_report["errors"].append(f"User {user_file.name}: {str(e)}")
            
            # Migrate assignment credentials
            workspaces_dir = Path("config/workspaces")
            if workspaces_dir.exists():
                for workspace_dir in workspaces_dir.iterdir():
                    if workspace_dir.is_dir():
                        assignments_dir = workspace_dir / "assignments"
                        if assignments_dir.exists():
                            for assignment_file in assignments_dir.glob("*.json"):
                                try:
                                    with open(assignment_file, 'r') as f:
                                        assignment_data = json.load(f)
                                    
                                    workspace_id = assignment_data.get("workspace_id", workspace_dir.name)
                                    assignment_id = assignment_data.get("id")
                                    metrics_config = assignment_data.get("metrics_config", {})
                                    
                                    for connector_type, config in metrics_config.items():
                                        auth_instance = config.get("auth_instance", {})
                                        credentials = auth_instance.get("credentials", {})
                                        
                                        if credentials and any(credentials.values()):
                                            if self.store_assignment_credentials(workspace_id, assignment_id, connector_type, credentials):
                                                migration_report["assignments_migrated"] += 1
                                except Exception as e:
                                    migration_report["errors"].append(f"Assignment {assignment_file.name}: {str(e)}")
        
        except Exception as e:
            migration_report["errors"].append(f"Migration error: {str(e)}")
        
        return migration_report
    
    def _safe_filename(self, name: str) -> str:
        """Convert email/ID to safe filename"""
        return hashlib.md5(name.encode()).hexdigest()
    
    def health_check(self) -> Dict[str, Any]:
        """Check credential manager health"""
        return {
            "encryption_available": bool(self._fernet),
            "secrets_dir_exists": self.credentials_dir.exists(),
            "master_key_configured": bool(os.getenv("CREDENTIAL_MASTER_KEY")),
            "credentials_count": len(list(self.credentials_dir.glob("*.enc")))
        }


# Global instance
credential_manager = SecureCredentialManager()