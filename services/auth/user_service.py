"""
User Service - Phase 3 Authentication System
Handles user accounts, authentication, and workspace access control
"""

import os
import json
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
import jwt

class UserService:
    """
    User authentication and management service.
    Phase 3: Replace env-var auth with user-based workspace access.
    """
    
    def __init__(self):
        self.users_dir = Path("config/users")
        self.sessions_dir = Path("config/sessions")
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # JWT secret (in production, this should be from env var)
        self.jwt_secret = os.getenv("JWT_SECRET", self._generate_default_secret())
        self.token_expiry_hours = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))
        
        # Ensure default admin user exists for Railway deployment
        self._ensure_default_admin()
    
    def _generate_default_secret(self) -> str:
        """Generate a default JWT secret (for development only)"""
        secret_file = Path("config/.jwt_secret")
        if secret_file.exists():
            return secret_file.read_text().strip()
        
        # Generate new secret
        secret = secrets.token_urlsafe(32)
        secret_file.write_text(secret)
        return secret
    
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_urlsafe(32)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        
        return password_hash.hex(), salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == password_hash
    
    def register_user(self, email: str, password: str, display_name: str = None) -> Dict[str, Any]:
        """
        Register a new user account.
        Phase 3: Users own workspaces instead of global access.
        """
        # Validate email format
        if "@" not in email or "." not in email.split("@")[1]:
            return {
                "success": False,
                "error": "Invalid email format"
            }
        
        # Check if user already exists
        user_file = self.users_dir / f"{email}.json"
        if user_file.exists():
            return {
                "success": False,
                "error": "User already exists"
            }
        
        # Hash password
        password_hash, salt = self._hash_password(password)
        
        # Create user record
        user_data = {
            "email": email,
            "display_name": display_name or email.split("@")[0],
            "password_hash": password_hash,
            "salt": salt,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "workspaces": [],  # List of workspace IDs user has access to
            "role": "user",  # user, admin
            "status": "active",  # active, disabled
            "preferences": {
                "default_workspace": None,
                "theme": "light",
                "timezone": "UTC"
            }
        }
        
        try:
            with open(user_file, 'w') as f:
                json.dump(user_data, f, indent=2)
            
            return {
                "success": True,
                "user": {
                    "email": email,
                    "display_name": user_data["display_name"],
                    "created_at": user_data["created_at"]
                },
                "message": "User registered successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create user: {str(e)}"
            }
    
    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and return session token.
        Phase 3: Replace env-var auth with user sessions.
        """
        user_file = self.users_dir / f"{email}.json"
        
        if not user_file.exists():
            return {
                "success": False,
                "error": "Invalid credentials"
            }
        
        try:
            with open(user_file, 'r') as f:
                user_data = json.load(f)
            
            # Check if user is active
            if user_data.get("status") != "active":
                return {
                    "success": False,
                    "error": "Account is disabled"
                }
            
            # Verify password
            if not self._verify_password(password, user_data["password_hash"], user_data["salt"]):
                return {
                    "success": False,
                    "error": "Invalid credentials"
                }
            
            # Update last login
            user_data["last_login"] = datetime.now().isoformat()
            with open(user_file, 'w') as f:
                json.dump(user_data, f, indent=2)
            
            # Generate JWT token  
            import time
            now = int(time.time())
            
            token_payload = {
                "email": email,
                "display_name": user_data["display_name"],
                "workspaces": user_data["workspaces"],
                "role": user_data["role"],
                "exp": now + (self.token_expiry_hours * 3600),
                "iat": now
            }
            
            token = jwt.encode(token_payload, self.jwt_secret, algorithm='HS256')
            
            return {
                "success": True,
                "token": token,
                "user": {
                    "email": email,
                    "display_name": user_data["display_name"],
                    "workspaces": user_data["workspaces"],
                    "role": user_data["role"],
                    "preferences": user_data["preferences"]
                },
                "expires_in": self.token_expiry_hours * 3600  # seconds
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user info"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return {
                "valid": True,
                "user": {
                    "email": payload["email"],
                    "display_name": payload["display_name"],
                    "workspaces": payload["workspaces"],
                    "role": payload["role"]
                }
            }
        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "error": "Token expired"
            }
        except jwt.InvalidTokenError:
            return {
                "valid": False,
                "error": "Invalid token"
            }
    
    def add_user_to_workspace(self, user_email: str, workspace_id: str, role: str = "member") -> Dict[str, Any]:
        """
        Grant user access to a workspace.
        Phase 3: Workspace-scoped access control.
        """
        user_file = self.users_dir / f"{user_email}.json"
        
        if not user_file.exists():
            return {
                "success": False,
                "error": "User not found"
            }
        
        try:
            with open(user_file, 'r') as f:
                user_data = json.load(f)
            
            # Add workspace if not already present
            if workspace_id not in user_data["workspaces"]:
                user_data["workspaces"].append(workspace_id)
            
            # Store workspace role (for future use)
            if "workspace_roles" not in user_data:
                user_data["workspace_roles"] = {}
            user_data["workspace_roles"][workspace_id] = role
            
            with open(user_file, 'w') as f:
                json.dump(user_data, f, indent=2)
            
            return {
                "success": True,
                "message": f"User {user_email} added to workspace {workspace_id} as {role}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add user to workspace: {str(e)}"
            }
    
    def get_user_workspaces(self, user_email: str) -> Dict[str, Any]:
        """Get all workspaces a user has access to"""
        user_file = self.users_dir / f"{user_email}.json"
        
        if not user_file.exists():
            return {
                "workspaces": [],
                "error": "User not found"
            }
        
        try:
            with open(user_file, 'r') as f:
                user_data = json.load(f)
            
            return {
                "workspaces": user_data.get("workspaces", []),
                "workspace_roles": user_data.get("workspace_roles", {})
            }
            
        except Exception as e:
            return {
                "workspaces": [],
                "error": f"Failed to get user workspaces: {str(e)}"
            }
    
    def check_workspace_access(self, user_email: str, workspace_id: str) -> bool:
        """Check if user has access to a workspace"""
        workspaces_result = self.get_user_workspaces(user_email)
        
        if "error" in workspaces_result:
            return False
        
        return workspace_id in workspaces_result.get("workspaces", [])
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users (admin only)"""
        users = []
        
        for user_file in self.users_dir.glob("*.json"):
            try:
                with open(user_file, 'r') as f:
                    user_data = json.load(f)
                
                # Return safe user info (no password data)
                users.append({
                    "email": user_data["email"],
                    "display_name": user_data["display_name"],
                    "role": user_data["role"],
                    "status": user_data["status"],
                    "created_at": user_data["created_at"],
                    "last_login": user_data["last_login"],
                    "workspace_count": len(user_data.get("workspaces", []))
                })
            except Exception as e:
                print(f"Warning: Could not read user file {user_file}: {e}")
        
        return users
    
    def _ensure_default_admin(self):
        """Ensure a default admin user exists for Railway deployment"""
        admin_email = "admin@railway.app"
        admin_file = self.users_dir / f"{admin_email}.json"
        
        # Only create if no users exist at all
        if not any(self.users_dir.glob("*.json")):
            try:
                password_hash, salt = self._hash_password("admin123")
                
                admin_user = {
                    "email": admin_email,
                    "display_name": "Railway Admin",
                    "password_hash": password_hash,
                    "salt": salt,
                    "created_at": datetime.utcnow().isoformat(),
                    "last_login": None,
                    "workspaces": ["default_workspace"],
                    "role": "admin", 
                    "status": "active",
                    "preferences": {
                        "default_workspace": "default_workspace",
                        "theme": "light",
                        "timezone": "UTC"
                    },
                    "workspace_roles": {
                        "default_workspace": "admin"
                    }
                }
                
                with open(admin_file, 'w') as f:
                    json.dump(admin_user, f, indent=2)
                    
                print(f"Created default admin user: {admin_email} / admin123")
                
            except Exception as e:
                print(f"Warning: Could not create default admin user: {e}")