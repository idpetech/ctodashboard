"""
Secure User Service
Integrates with encrypted database storage for user authentication
"""

import jwt
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request

from ..security.secure_database import secure_db
from .user_service import UserService


class SecureUserService(UserService):
    """
    Enhanced user service with secure credential storage.
    Inherits authentication logic but stores data securely.
    """
    
    def __init__(self):
        # Initialize parent class
        super().__init__()
        self.secure_db = secure_db
    
    def _get_audit_info(self) -> Dict[str, Any]:
        """Get audit information from current request"""
        return {
            "ip_address": request.environ.get('REMOTE_ADDR') if request else None,
            "user_agent": request.environ.get('HTTP_USER_AGENT') if request else None
        }
    
    def register_user(self, email: str, password: str, display_name: str = None) -> Dict[str, Any]:
        """
        Register new user with secure credential storage.
        """
        # Validate input
        if not email or not password:
            return {"success": False, "error": "Email and password are required"}
        
        if len(password) < 8:
            return {"success": False, "error": "Password must be at least 8 characters"}
        
        # Check if user already exists
        if self._load_user_from_secure_db(email):
            return {"success": False, "error": "User already exists"}
        
        # Generate secure password hash
        salt = secrets.token_urlsafe(32)
        password_hash = self._hash_password(password, salt)
        
        # Create user data
        user_data = {
            "email": email,
            "display_name": display_name or email.split("@")[0],
            "password_hash": password_hash,
            "salt": salt,
            "workspaces": [f"{email.split('@')[0]}_workspace"],  # Default workspace
            "role": "user",
            "status": "active",
            "preferences": {
                "theme": "light",
                "timezone": "UTC"
            },
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None
        }
        
        # Store in secure database
        audit_info = self._get_audit_info()
        audit_info["user_email"] = email
        
        if self.secure_db.store_user_credentials(email, user_data, audit_info):
            return {
                "success": True,
                "message": "User registered successfully",
                "user": {
                    "email": email,
                    "display_name": user_data["display_name"],
                    "workspaces": user_data["workspaces"]
                }
            }
        else:
            return {"success": False, "error": "Failed to create user"}
    
    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user against secure database.
        """
        # Load user from secure database
        user_data = self._load_user_from_secure_db(email)
        if not user_data:
            return {"valid": False, "error": "Invalid credentials"}
        
        # Check account status
        if user_data.get("status") != "active":
            return {"valid": False, "error": "Account is disabled"}
        
        # Verify password
        stored_hash = user_data.get("password_hash")
        salt = user_data.get("salt")
        
        if not stored_hash or not salt:
            return {"valid": False, "error": "Invalid account configuration"}
        
        if not self._verify_password(password, stored_hash, salt):
            return {"valid": False, "error": "Invalid credentials"}
        
        # Update last login
        user_data["last_login"] = datetime.utcnow().isoformat()
        audit_info = self._get_audit_info()
        audit_info["user_email"] = email
        
        self.secure_db.store_user_credentials(email, user_data, audit_info)
        
        # Generate JWT token
        token = self.generate_token(user_data)
        
        return {
            "valid": True,
            "token": token,
            "user": {
                "email": user_data["email"],
                "display_name": user_data["display_name"],
                "workspaces": user_data["workspaces"],
                "role": user_data["role"],
                "preferences": user_data["preferences"]
            }
        }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token and return user data from secure storage.
        """
        try:
            # Decode token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check expiration
            if datetime.utcnow().timestamp() > payload.get('exp', 0):
                return {"valid": False, "error": "Token expired"}
            
            email = payload.get('email')
            if not email:
                return {"valid": False, "error": "Invalid token"}
            
            # Load fresh user data from secure database
            user_data = self._load_user_from_secure_db(email)
            if not user_data:
                return {"valid": False, "error": "User not found"}
            
            # Check if account is still active
            if user_data.get("status") != "active":
                return {"valid": False, "error": "Account is disabled"}
            
            return {
                "valid": True,
                "user": {
                    "email": user_data["email"],
                    "display_name": user_data["display_name"],
                    "workspaces": user_data["workspaces"],
                    "role": user_data["role"],
                    "preferences": user_data["preferences"]
                }
            }
        
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "error": "Invalid token"}
        except Exception as e:
            return {"valid": False, "error": f"Token verification failed: {str(e)}"}
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by email from secure storage.
        """
        user_data = self._load_user_from_secure_db(email)
        if not user_data:
            return None
        
        # Return user data without sensitive fields
        return {
            "email": user_data["email"],
            "display_name": user_data["display_name"],
            "workspaces": user_data["workspaces"],
            "role": user_data["role"],
            "status": user_data["status"],
            "preferences": user_data["preferences"],
            "created_at": user_data["created_at"],
            "last_login": user_data["last_login"]
        }
    
    def check_workspace_access(self, user_email: str, workspace_id: str) -> bool:
        """
        Check if user has access to workspace.
        """
        user_data = self._load_user_from_secure_db(user_email)
        if not user_data:
            return False
        
        user_workspaces = user_data.get("workspaces", [])
        return workspace_id in user_workspaces
    
    def grant_workspace_access(self, user_email: str, workspace_id: str) -> bool:
        """
        Grant user access to workspace.
        """
        user_data = self._load_user_from_secure_db(user_email)
        if not user_data:
            return False
        
        user_workspaces = user_data.get("workspaces", [])
        if workspace_id not in user_workspaces:
            user_workspaces.append(workspace_id)
            user_data["workspaces"] = user_workspaces
            
            audit_info = self._get_audit_info()
            audit_info["user_email"] = user_email
            audit_info["workspace_id"] = workspace_id
            
            return self.secure_db.store_user_credentials(user_email, user_data, audit_info)
        
        return True  # Already has access
    
    def revoke_workspace_access(self, user_email: str, workspace_id: str) -> bool:
        """
        Revoke user access to workspace.
        """
        user_data = self._load_user_from_secure_db(user_email)
        if not user_data:
            return False
        
        user_workspaces = user_data.get("workspaces", [])
        if workspace_id in user_workspaces:
            user_workspaces.remove(workspace_id)
            user_data["workspaces"] = user_workspaces
            
            audit_info = self._get_audit_info()
            audit_info["user_email"] = user_email
            audit_info["workspace_id"] = workspace_id
            
            return self.secure_db.store_user_credentials(user_email, user_data, audit_info)
        
        return True  # Already doesn't have access
    
    def list_users(self) -> List[Dict[str, Any]]:
        """
        List all users (admin function).
        Returns user data without sensitive information.
        """
        # This would need to be implemented in the secure database
        # For now, return empty list as we don't have a list_all_users method
        return []
    
    def _load_user_from_secure_db(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Load user data from secure database with audit logging.
        """
        audit_info = self._get_audit_info()
        audit_info["user_email"] = email
        
        return self.secure_db.get_user_credentials(email, audit_info)
    
    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """
        Verify password against stored hash.
        """
        computed_hash = self._hash_password(password, salt)
        return computed_hash == stored_hash
    
    def _hash_password(self, password: str, salt: str) -> str:
        """
        Hash password with salt.
        """
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Extended health check including secure storage status.
        """
        base_health = super().health_check()
        
        # Check secure database health
        db_health = self.secure_db.health_check()
        
        return {
            **base_health,
            "secure_storage": db_health,
            "security_enabled": True
        }


# Create singleton instance for use throughout application
secure_user_service = SecureUserService()