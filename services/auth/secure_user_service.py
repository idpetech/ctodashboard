"""
User authentication — Postgres only (secure_db / ctodashboard.users).

See docs/POSTGRES-SINGLE-SOURCE-PLAN.md
"""

import os
import jwt
import hashlib
import secrets
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from flask import request

from ..security.secure_database import secure_db

logger = logging.getLogger(__name__)


class SecureUserService:
    """User accounts and JWT auth backed by Postgres only."""

    def __init__(self):
        self.secure_db = secure_db
        self.jwt_secret = os.getenv("JWT_SECRET", self._generate_default_secret())
        self.token_expiry_hours = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))

    def _generate_default_secret(self) -> str:
        secret_file = Path("config/.jwt_secret")
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        if secret_file.exists():
            return secret_file.read_text().strip()
        secret = secrets.token_urlsafe(32)
        secret_file.write_text(secret)
        return secret

    def _get_audit_info(self) -> Dict[str, Any]:
        return {
            "ip_address": request.environ.get("REMOTE_ADDR") if request else None,
            "user_agent": request.environ.get("HTTP_USER_AGENT") if request else None,
        }

    def register_user(self, email: str, password: str, display_name: str = None) -> Dict[str, Any]:
        if not email or not password:
            return {"success": False, "error": "Email and password are required"}
        if len(password) < 8:
            return {"success": False, "error": "Password must be at least 8 characters"}
        if self._load_user_from_secure_db(email):
            return {"success": False, "error": "User already exists"}

        salt = secrets.token_urlsafe(32)
        password_hash = self._hash_password(password, salt)

        # New signups default to the Free plan with a time-boxed trial.
        # FREE_TRIAL_DAYS sets the window (default 7). Enforcement of the
        # limit (the access guardrail) is handled separately; here we only
        # stamp the account so that logic has something to read.
        trial_days = int(os.getenv("FREE_TRIAL_DAYS", "7"))
        _now = datetime.utcnow()
        trial_info = {
            "plan": "free",
            "trial_days": trial_days,
            "started_at": _now.isoformat(),
            "expires_at": (_now + timedelta(days=trial_days)).isoformat(),
        }
        user_data = {
            "email": email,
            "display_name": display_name or email.split("@")[0],
            "password_hash": password_hash,
            "salt": salt,
            "workspaces": [f"{email.split('@')[0]}_workspace"],
            "role": "user",
            "status": "active",
            "preferences": {
                "theme": "light",
                "timezone": "UTC",
                "plan": "free",
                "trial": trial_info,
            },
            "created_at": _now.isoformat(),
            "last_login": None,
        }

        audit_info = self._get_audit_info()
        audit_info["user_email"] = email
        if not self.secure_db.store_user_credentials(email, user_data, audit_info):
            return {"success": False, "error": "Failed to create user"}

        workspace_id = user_data["workspaces"][0]
        try:
            from services.workspace.postgres_backend import PostgresWorkspaceBackend

            PostgresWorkspaceBackend().create_workspace(
                workspace_id,
                user_data["display_name"],
                f"Workspace for {email}",
            )
        except Exception as e:
            logger.warning("Could not create workspace for %s: %s", email, e)

        token = self.generate_token(user_data)
        return {
            "success": True,
            "token": token,
            "message": "User registered successfully",
            "user": {
                "email": email,
                "display_name": user_data["display_name"],
                "workspaces": user_data["workspaces"],
                "role": user_data["role"],
                "preferences": user_data["preferences"],
            },
        }

    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        user_data = self._load_user_from_secure_db(email)
        if not user_data:
            return {"success": False, "valid": False, "error": "Invalid credentials"}
        if user_data.get("status") != "active":
            return {"success": False, "valid": False, "error": "Account is disabled"}

        stored_hash = user_data.get("password_hash")
        salt = user_data.get("salt")
        if not stored_hash or not salt:
            return {"success": False, "valid": False, "error": "Invalid account configuration"}
        if not self._verify_password(password, stored_hash, salt):
            return {"success": False, "valid": False, "error": "Invalid credentials"}

        user_data["last_login"] = datetime.utcnow().isoformat()
        audit_info = self._get_audit_info()
        audit_info["user_email"] = email
        self.secure_db.store_user_credentials(email, user_data, audit_info)

        token = self.generate_token(user_data)
        user_public = {
            "email": user_data["email"],
            "display_name": user_data["display_name"],
            "workspaces": user_data["workspaces"],
            "role": user_data["role"],
            "preferences": user_data["preferences"],
        }
        return {
            "success": True,
            "valid": True,
            "token": token,
            "user": user_public,
            "expires_in": self.token_expiry_hours * 3600,
        }

    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            if datetime.utcnow().timestamp() > payload.get("exp", 0):
                return {"valid": False, "error": "Token expired"}
            email = payload.get("email")
            if not email:
                return {"valid": False, "error": "Invalid token"}
            user_data = self._load_user_from_secure_db(email)
            if not user_data or user_data.get("status") != "active":
                return {"valid": False, "error": "User not found"}
            return {
                "valid": True,
                "user": {
                    "email": user_data["email"],
                    "display_name": user_data["display_name"],
                    "workspaces": user_data["workspaces"],
                    "role": user_data["role"],
                    "preferences": user_data["preferences"],
                },
            }
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "error": "Invalid token"}
        except Exception as e:
            return {"valid": False, "error": f"Token verification failed: {str(e)}"}

    def update_user(self, user_email: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        user_data = self._load_user_from_secure_db(user_email)
        if not user_data:
            return {"success": False, "error": "User not found"}
        if "display_name" in updates:
            name = updates["display_name"].strip()
            if not name:
                return {"success": False, "error": "Display name cannot be empty"}
            user_data["display_name"] = name
        if "password" in updates:
            if len(updates["password"]) < 8:
                return {"success": False, "error": "Password must be at least 8 characters"}
            salt = secrets.token_urlsafe(32)
            user_data["password_hash"] = self._hash_password(updates["password"], salt)
            user_data["salt"] = salt
        if "preferences" in updates:
            user_data.setdefault("preferences", {}).update(updates["preferences"])
        user_data["updated_at"] = datetime.utcnow().isoformat()
        audit_info = self._get_audit_info()
        audit_info["user_email"] = user_email
        if not self.secure_db.store_user_credentials(user_email, user_data, audit_info):
            return {"success": False, "error": "Failed to update profile"}
        return {
            "success": True,
            "user": {
                "email": user_data["email"],
                "display_name": user_data["display_name"],
                "workspaces": user_data.get("workspaces", []),
                "role": user_data.get("role", "user"),
                "preferences": user_data.get("preferences", {}),
            },
            "message": "Profile updated successfully",
        }

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        user_data = self._load_user_from_secure_db(email)
        if not user_data:
            return None
        return {
            "email": user_data["email"],
            "display_name": user_data["display_name"],
            "workspaces": user_data["workspaces"],
            "role": user_data["role"],
            "status": user_data["status"],
            "preferences": user_data["preferences"],
            "created_at": user_data.get("created_at"),
            "last_login": user_data.get("last_login"),
        }

    def check_workspace_access(self, user_email: str, workspace_id: str) -> bool:
        user_data = self._load_user_from_secure_db(user_email)
        if not user_data:
            return False
        return workspace_id in user_data.get("workspaces", [])

    def grant_workspace_access(self, user_email: str, workspace_id: str) -> bool:
        user_data = self._load_user_from_secure_db(user_email)
        if not user_data:
            return False
        workspaces = user_data.get("workspaces", [])
        if workspace_id in workspaces:
            return True
        workspaces.append(workspace_id)
        user_data["workspaces"] = workspaces
        audit_info = self._get_audit_info()
        audit_info["user_email"] = user_email
        audit_info["workspace_id"] = workspace_id
        return self.secure_db.store_user_credentials(user_email, user_data, audit_info)

    def revoke_workspace_access(self, user_email: str, workspace_id: str) -> bool:
        user_data = self._load_user_from_secure_db(user_email)
        if not user_data:
            return False
        workspaces = user_data.get("workspaces", [])
        if workspace_id not in workspaces:
            return True
        workspaces.remove(workspace_id)
        user_data["workspaces"] = workspaces
        audit_info = self._get_audit_info()
        audit_info["user_email"] = user_email
        audit_info["workspace_id"] = workspace_id
        return self.secure_db.store_user_credentials(user_email, user_data, audit_info)

    def generate_token(self, user_data: Dict[str, Any]) -> str:
        now = int(time.time())
        payload = {
            "email": user_data["email"],
            "display_name": user_data.get("display_name", ""),
            "workspaces": user_data.get("workspaces", []),
            "role": user_data.get("role", "user"),
            "exp": now + (self.token_expiry_hours * 3600),
            "iat": now,
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token if isinstance(token, str) else token.decode("utf-8")

    def get_user_profile(self, email: str) -> Dict[str, Any]:
        user_data = self._load_user_from_secure_db(email)
        if not user_data:
            return {"success": False, "error": "User not found"}
        return {
            "success": True,
            "user": {
                "email": user_data["email"],
                "display_name": user_data["display_name"],
                "workspaces": user_data.get("workspaces", []),
                "role": user_data.get("role", "user"),
                "preferences": user_data.get("preferences", {}),
                "created_at": user_data.get("created_at"),
            },
        }

    def get_user_workspaces(self, user_email: str) -> Dict[str, Any]:
        user_data = self._load_user_from_secure_db(user_email)
        if not user_data:
            return {"workspaces": [], "error": "User not found"}
        return {"workspaces": user_data.get("workspaces", [])}

    def add_user_to_workspace(
        self, user_email: str, workspace_id: str, role: str = "member"
    ) -> Dict[str, Any]:
        if self.grant_workspace_access(user_email, workspace_id):
            return {
                "success": True,
                "message": f"User {user_email} added to workspace {workspace_id} as {role}",
            }
        return {"success": False, "error": "Failed to add user to workspace"}

    def list_users(self) -> List[Dict[str, Any]]:
        return self.secure_db.list_all_users()

    def _load_user_from_secure_db(self, email: str) -> Optional[Dict[str, Any]]:
        audit_info = self._get_audit_info()
        audit_info["user_email"] = email
        return self.secure_db.get_user_credentials(email, audit_info)

    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        return self._hash_password(password, salt) == stored_hash

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000
        ).hex()

    def health_check(self) -> Dict[str, Any]:
        db_health = self.secure_db.health_check()
        return {
            "status": "ok" if db_health.get("database_connected") else "error",
            "auth_backend": "postgresql",
            "secure_storage": db_health,
            "security_enabled": True,
        }


secure_user_service = SecureUserService()

# Back-compat alias for any legacy imports
UserService = SecureUserService
