"""
Secure Database Storage for Credentials
Uses SQLite with encrypted fields for proper data integrity and transactions
"""

import os
import json
import sqlite3
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import threading


class SecureDatabaseManager:
    """
    SQLite-based secure credential storage with field-level encryption.
    ACID compliant, thread-safe, with proper indexing and querying.
    """
    
    def __init__(self, db_path: str = "config/secure_credentials.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Thread-local storage for database connections
        self._local = threading.local()
        
        # Ensure database file is never committed
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            with open(gitignore_path, 'a') as f:
                f.write(f"\n# Auto-added by secure database\n{self.db_path}\n")
        
        self._fernet = self._get_encryption_key()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.execute("PRAGMA temp_store=MEMORY")
            self._local.connection.execute("PRAGMA foreign_keys=ON")
        
        return self._local.connection
    
    def _get_encryption_key(self) -> Fernet:
        """Generate encryption key from environment variable"""
        master_key = os.getenv("CREDENTIAL_MASTER_KEY")
        
        if not master_key:
            # Development fallback - generate from machine-specific data
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
    
    def _init_database(self):
        """Initialize database schema"""
        conn = self._get_connection()
        
        # Users table - stores user auth data with encrypted sensitive fields
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secure_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT,
                encrypted_password_data BLOB,  -- Encrypted: password_hash, salt
                workspaces TEXT,  -- JSON array
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'active',
                preferences TEXT,  -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Workspaces table - stores workspace metadata
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secure_workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT UNIQUE NOT NULL,
                name TEXT,
                description TEXT,
                settings TEXT,  -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Assignments table - stores assignment metadata (no credentials)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secure_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                name TEXT,
                description TEXT,
                team_size INTEGER,
                monthly_burn_rate INTEGER,
                status TEXT DEFAULT 'active',
                metrics_config TEXT,  -- JSON object without credentials
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(assignment_id, workspace_id),
                FOREIGN KEY(workspace_id) REFERENCES secure_workspaces(workspace_id)
            )
        """)
        
        # Credentials table - stores encrypted connector credentials
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secure_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL,
                assignment_id TEXT NOT NULL,
                connector_type TEXT NOT NULL,
                encrypted_credentials BLOB NOT NULL,  -- Encrypted credential data
                auth_configured BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workspace_id, assignment_id, connector_type),
                FOREIGN KEY(workspace_id, assignment_id) REFERENCES secure_assignments(workspace_id, assignment_id)
            )
        """)
        
        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON secure_users(email)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_id ON secure_workspaces(workspace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_workspace ON secure_assignments(workspace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_id ON secure_assignments(assignment_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_credentials_lookup ON secure_credentials(workspace_id, assignment_id, connector_type)")
        
        # Audit table for security logging
        conn.execute("""
            CREATE TABLE IF NOT EXISTS credential_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,  -- 'create', 'read', 'update', 'delete'
                entity_type TEXT NOT NULL,  -- 'user', 'assignment', 'credential'
                entity_id TEXT NOT NULL,
                user_email TEXT,
                workspace_id TEXT,
                connector_type TEXT,
                success BOOLEAN,
                error_message TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
    
    def _encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt dictionary data"""
        json_data = json.dumps(data, sort_keys=True)
        return self._fernet.encrypt(json_data.encode())
    
    def _decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt data back to dictionary"""
        decrypted_bytes = self._fernet.decrypt(encrypted_data)
        return json.loads(decrypted_bytes.decode())
    
    def store_user_credentials(self, email: str, user_data: Dict[str, Any], audit_info: Dict[str, Any] = None) -> bool:
        """Store user with encrypted password data"""
        try:
            conn = self._get_connection()
            
            # Separate sensitive from non-sensitive data
            sensitive_data = {
                "password_hash": user_data.get("password_hash"),
                "salt": user_data.get("salt"),
            }
            
            encrypted_password_data = self._encrypt_data(sensitive_data) if any(sensitive_data.values()) else None
            
            # Store user record
            conn.execute("""
                INSERT OR REPLACE INTO secure_users 
                (email, display_name, encrypted_password_data, workspaces, role, status, preferences, last_login, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                email,
                user_data.get("display_name"),
                encrypted_password_data,
                json.dumps(user_data.get("workspaces", [])),
                user_data.get("role", "user"),
                user_data.get("status", "active"),
                json.dumps(user_data.get("preferences", {})),
                user_data.get("last_login")
            ))
            
            conn.commit()
            
            # Audit log
            self._audit_log("create", "user", email, audit_info)
            
            return True
        except Exception as e:
            print(f"Error storing user credentials: {e}")
            self._audit_log("create", "user", email, audit_info, success=False, error=str(e))
            return False
    
    def get_user_credentials(self, email: str, audit_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Retrieve user with decrypted password data"""
        try:
            conn = self._get_connection()
            
            row = conn.execute("""
                SELECT email, display_name, encrypted_password_data, workspaces, role, status, 
                       preferences, created_at, last_login
                FROM secure_users WHERE email = ?
            """, (email,)).fetchone()
            
            if not row:
                return None
            
            user_data = {
                "email": row["email"],
                "display_name": row["display_name"],
                "workspaces": json.loads(row["workspaces"]) if row["workspaces"] else [],
                "role": row["role"],
                "status": row["status"],
                "preferences": json.loads(row["preferences"]) if row["preferences"] else {},
                "created_at": row["created_at"],
                "last_login": row["last_login"]
            }
            
            # Decrypt sensitive data if present
            if row["encrypted_password_data"]:
                sensitive_data = self._decrypt_data(row["encrypted_password_data"])
                user_data.update(sensitive_data)
            
            # Audit log
            self._audit_log("read", "user", email, audit_info)
            
            return user_data
        except Exception as e:
            print(f"Error retrieving user credentials: {e}")
            self._audit_log("read", "user", email, audit_info, success=False, error=str(e))
            return None
    
    def store_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str, 
                                   credentials: Dict[str, Any], audit_info: Dict[str, Any] = None) -> bool:
        """Store encrypted connector credentials"""
        try:
            conn = self._get_connection()
            
            encrypted_credentials = self._encrypt_data(credentials)
            
            conn.execute("""
                INSERT OR REPLACE INTO secure_credentials 
                (workspace_id, assignment_id, connector_type, encrypted_credentials, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (workspace_id, assignment_id, connector_type, encrypted_credentials))
            
            conn.commit()
            
            # Audit log
            self._audit_log("create", "credential", f"{workspace_id}:{assignment_id}:{connector_type}", audit_info)
            
            return True
        except Exception as e:
            print(f"Error storing assignment credentials: {e}")
            self._audit_log("create", "credential", f"{workspace_id}:{assignment_id}:{connector_type}", 
                          audit_info, success=False, error=str(e))
            return False
    
    def get_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str,
                                 audit_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt assignment connector credentials"""
        try:
            conn = self._get_connection()
            
            row = conn.execute("""
                SELECT encrypted_credentials FROM secure_credentials 
                WHERE workspace_id = ? AND assignment_id = ? AND connector_type = ?
            """, (workspace_id, assignment_id, connector_type)).fetchone()
            
            if not row:
                return None
            
            credentials = self._decrypt_data(row["encrypted_credentials"])
            
            # Audit log
            self._audit_log("read", "credential", f"{workspace_id}:{assignment_id}:{connector_type}", audit_info)
            
            return credentials
        except Exception as e:
            print(f"Error retrieving assignment credentials: {e}")
            self._audit_log("read", "credential", f"{workspace_id}:{assignment_id}:{connector_type}", 
                          audit_info, success=False, error=str(e))
            return None
    
    def delete_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str,
                                    audit_info: Dict[str, Any] = None) -> bool:
        """Delete assignment connector credentials"""
        try:
            conn = self._get_connection()
            
            conn.execute("""
                DELETE FROM secure_credentials 
                WHERE workspace_id = ? AND assignment_id = ? AND connector_type = ?
            """, (workspace_id, assignment_id, connector_type))
            
            conn.commit()
            
            # Audit log
            self._audit_log("delete", "credential", f"{workspace_id}:{assignment_id}:{connector_type}", audit_info)
            
            return True
        except Exception as e:
            print(f"Error deleting assignment credentials: {e}")
            self._audit_log("delete", "credential", f"{workspace_id}:{assignment_id}:{connector_type}", 
                          audit_info, success=False, error=str(e))
            return False
    
    def list_assignment_credentials(self, workspace_id: str, assignment_id: str) -> Dict[str, bool]:
        """List which connectors have stored credentials for an assignment"""
        try:
            conn = self._get_connection()
            
            rows = conn.execute("""
                SELECT connector_type FROM secure_credentials 
                WHERE workspace_id = ? AND assignment_id = ?
            """, (workspace_id, assignment_id)).fetchall()
            
            available_connectors = {row["connector_type"] for row in rows}
            
            # Return status for all known connector types
            connector_types = ['github', 'jira', 'aws', 'openai']
            return {connector_type: connector_type in available_connectors for connector_type in connector_types}
        except Exception as e:
            print(f"Error listing assignment credentials: {e}")
            return {}
    
    def get_workspace_assignments(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all assignments for workspace with credential status"""
        try:
            conn = self._get_connection()
            
            rows = conn.execute("""
                SELECT assignment_id, name, description, team_size, monthly_burn_rate, 
                       status, metrics_config, created_at, updated_at
                FROM secure_assignments WHERE workspace_id = ?
            """, (workspace_id,)).fetchall()
            
            assignments = []
            for row in rows:
                assignment = {
                    "id": row["assignment_id"],
                    "workspace_id": workspace_id,
                    "name": row["name"],
                    "description": row["description"],
                    "team_size": row["team_size"],
                    "monthly_burn_rate": row["monthly_burn_rate"],
                    "status": row["status"],
                    "metrics_config": json.loads(row["metrics_config"]) if row["metrics_config"] else {},
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
                
                # Add credential status for each connector
                credential_status = self.list_assignment_credentials(workspace_id, row["assignment_id"])
                metrics_config = assignment["metrics_config"]
                
                for connector_type, has_credentials in credential_status.items():
                    if connector_type not in metrics_config:
                        continue
                    
                    if "auth_instance" not in metrics_config[connector_type]:
                        metrics_config[connector_type]["auth_instance"] = {}
                    
                    metrics_config[connector_type]["auth_instance"]["auth_configured"] = has_credentials
                    metrics_config[connector_type]["auth_instance"]["credentials"] = {}  # Never include actual credentials
                
                assignments.append(assignment)
            
            return assignments
        except Exception as e:
            print(f"Error getting workspace assignments: {e}")
            return []
    
    def store_assignment(self, assignment_data: Dict[str, Any]) -> bool:
        """Store assignment metadata (without credentials)"""
        try:
            conn = self._get_connection()
            
            # Clean metrics_config of any credentials
            metrics_config = assignment_data.get("metrics_config", {})
            cleaned_metrics_config = {}
            
            for connector_type, config in metrics_config.items():
                cleaned_config = config.copy()
                if "auth_instance" in cleaned_config:
                    cleaned_config["auth_instance"] = {
                        k: v for k, v in cleaned_config["auth_instance"].items() 
                        if k != "credentials"
                    }
                    cleaned_config["auth_instance"]["credentials"] = {}
                cleaned_metrics_config[connector_type] = cleaned_config
            
            conn.execute("""
                INSERT OR REPLACE INTO secure_assignments 
                (assignment_id, workspace_id, name, description, team_size, monthly_burn_rate, 
                 status, metrics_config, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                assignment_data["id"],
                assignment_data["workspace_id"],
                assignment_data.get("name"),
                assignment_data.get("description"),
                assignment_data.get("team_size"),
                assignment_data.get("monthly_burn_rate"),
                assignment_data.get("status", "active"),
                json.dumps(cleaned_metrics_config)
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error storing assignment: {e}")
            return False
    
    def _audit_log(self, action: str, entity_type: str, entity_id: str, audit_info: Dict[str, Any] = None, 
                  success: bool = True, error: str = None):
        """Log credential access for security auditing"""
        try:
            if not audit_info:
                audit_info = {}
            
            conn = self._get_connection()
            
            conn.execute("""
                INSERT INTO credential_audit 
                (action, entity_type, entity_id, user_email, workspace_id, connector_type, 
                 success, error_message, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action,
                entity_type,
                entity_id,
                audit_info.get("user_email"),
                audit_info.get("workspace_id"),
                audit_info.get("connector_type"),
                success,
                error,
                audit_info.get("ip_address"),
                audit_info.get("user_agent")
            ))
            
            conn.commit()
        except Exception as e:
            print(f"Error writing audit log: {e}")
    
    def get_audit_logs(self, limit: int = 100, entity_type: str = None) -> List[Dict[str, Any]]:
        """Get recent audit logs for security monitoring"""
        try:
            conn = self._get_connection()
            
            where_clause = "WHERE entity_type = ?" if entity_type else ""
            params = [entity_type] if entity_type else []
            params.append(limit)
            
            rows = conn.execute(f"""
                SELECT * FROM credential_audit 
                {where_clause}
                ORDER BY created_at DESC LIMIT ?
            """, params).fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error retrieving audit logs: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health and security status"""
        try:
            conn = self._get_connection()
            
            # Test database connectivity
            conn.execute("SELECT 1").fetchone()
            
            # Get statistics
            user_count = conn.execute("SELECT COUNT(*) FROM secure_users").fetchone()[0]
            assignment_count = conn.execute("SELECT COUNT(*) FROM secure_assignments").fetchone()[0]
            credential_count = conn.execute("SELECT COUNT(*) FROM secure_credentials").fetchone()[0]
            audit_count = conn.execute("SELECT COUNT(*) FROM credential_audit").fetchone()[0]
            
            return {
                "database_connected": True,
                "encryption_available": bool(self._fernet),
                "master_key_configured": bool(os.getenv("CREDENTIAL_MASTER_KEY")),
                "statistics": {
                    "users": user_count,
                    "assignments": assignment_count,
                    "credentials": credential_count,
                    "audit_logs": audit_count
                }
            }
        except Exception as e:
            return {
                "database_connected": False,
                "error": str(e)
            }


# Global instance
secure_db = SecureDatabaseManager()