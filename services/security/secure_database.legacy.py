"""
Refactored Secure Database Storage with Clean Adapter Pattern
Maintains 100% API compatibility while supporting any database backend
"""

import os
import json
import base64
import hashlib
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.logging_config import get_logger
from .database_adapter import create_database_adapter, parse_database_url

logger = get_logger(__name__)


class SecureDatabaseManager:
    """
    Database-agnostic secure credential storage with field-level encryption.
    ACID compliant, thread-safe, with proper indexing and querying.
    Supports SQLite, PostgreSQL, MySQL, etc. through adapter pattern.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize with database adapter based on configuration"""
        
        # Get database URL from environment or construct from path
        self.db_url = self._determine_database_url(db_path)
        
        # Parse database URL into type and config
        self.db_type, self.connection_config = parse_database_url(self.db_url)
        
        # Set up encryption
        self._fernet = self._get_encryption_key()
        
        # Create database adapter
        self.adapter = create_database_adapter(self.db_type, self.connection_config, self._fernet)
        
        # Connect and initialize
        if not self.adapter.connect():
            raise RuntimeError(f"Failed to connect to {self.db_type} database")
            
        self._ensure_database_ready()
        
        logger.info("SecureDatabaseManager initialized", extra={
            "operation": "db_init",
            "db_type": self.db_type,
            "adapter": self.adapter.__class__.__name__
        })
    
    def _determine_database_url(self, db_path: str = None) -> str:
        """Determine database URL - PostgreSQL ONLY, no fallbacks"""
        
        # Priority 1: Explicit DATABASE_URL environment variable
        if os.getenv("DATABASE_URL"):
            return os.getenv("DATABASE_URL")
            
        # Priority 2: Railway PostgreSQL for ctodashboard
        if os.getenv("RAILWAY_ENVIRONMENT"):
            # Use ctodashboard-specific PostgreSQL in Railway
            return "postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@postgres.railway.internal:5432/railway?options=-csearch_path%3Dctodashboard"
            
        # Priority 3: Local PostgreSQL (no SQLite fallback)
        return "postgresql://haseebtoor@localhost:5432/railway?options=-csearch_path%3Dctodashboard"
    
    def _get_encryption_key(self) -> Fernet:
        """Generate encryption key using EXACT same method as original implementation"""
        import hashlib
        import platform
        
        master_key = os.getenv("CREDENTIAL_MASTER_KEY")
        
        if not master_key:
            # Use EXACT same development fallback as original
            machine_info = f"{platform.node()}{platform.machine()}{platform.processor()}"
            master_key = hashlib.sha256(machine_info.encode()).hexdigest()
            logger.warning("Using development credential key. Set CREDENTIAL_MASTER_KEY environment variable for production!")
        
        # Use EXACT same salt and derivation as original
        salt = b"ctodashboard_salt_v1"  # Fixed salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def _ensure_database_ready(self):
        """Ensure database is initialized and up to date"""
        if not self._database_exists_and_ready():
            self.adapter.create_tables()
            self.adapter.set_schema_version(1, "Initial schema creation")
            logger.info("Database initialized with initial schema")
        else:
            current_version = self.adapter.get_schema_version()
            target_version = self._get_target_schema_version()
            if current_version < target_version:
                self._run_migrations(current_version, target_version)
                
        # Auto-initialize if empty
        self._auto_initialize_if_empty()
    
    def _database_exists_and_ready(self) -> bool:
        """Check if database exists and has the basic tables"""
        required_tables = ['secure_users', 'secure_workspaces', 'secure_assignments', 'secure_credentials']
        return all(self.adapter.check_table_exists(table) for table in required_tables)
    
    def _get_target_schema_version(self) -> int:
        """Get the target schema version for this application version"""
        return 1
    
    def _run_migrations(self, from_version: int, to_version: int):
        """Run database migrations from one version to another"""
        logger.info("Starting database migration", extra={
            "operation": "db_migration_start",
            "from_version": from_version,
            "to_version": to_version
        })
        
        try:
            self.adapter.begin_transaction()
            for version in range(from_version + 1, to_version + 1):
                self._apply_migration(version)
                self.adapter.set_schema_version(version, f"Migration to version {version}")
            self.adapter.commit_transaction()
            
            logger.info("Database migration completed", extra={
                "operation": "db_migration_complete",
                "final_version": to_version
            })
        except Exception as e:
            self.adapter.rollback_transaction()
            logger.error("Database migration failed", extra={
                "operation": "db_migration_failed",
                "from_version": from_version,
                "to_version": to_version,
                "error": str(e)
            })
            raise
    
    def _apply_migration(self, version: int):
        """Apply a specific migration version"""
        logger.info("Applying migration", extra={
            "operation": "apply_migration",
            "version": version
        })
        
        # Future migrations would be implemented here
        # For now, version 1 is the initial schema
        if version == 1:
            # This is handled by create_tables()
            pass
        else:
            logger.warning("Unknown migration version requested", extra={
                "operation": "unknown_migration",
                "version": version
            })
    
    def _auto_initialize_if_empty(self):
        """Automatically create default user if database is empty"""
        try:
            # Check if any users exist
            result = self.adapter.execute_query("SELECT COUNT(*) FROM secure_users")
            if result and len(result) > 0:
                # Handle PostgreSQL RealDictRow vs SQLite tuple
                if hasattr(result[0], 'keys'):
                    # PostgreSQL RealDictRow
                    user_count = result[0]['count']
                else:
                    # SQLite tuple
                    user_count = result[0][0]
            else:
                user_count = 0
            
            if user_count == 0:
                logger.info("Database is empty - creating default admin user")
                
                # Create default admin user
                admin_data = {
                    "display_name": "admin",
                    "workspaces": ["admin_workspace"],
                    "role": "admin",
                    "status": "active", 
                    "preferences": {
                        "theme": "light",
                        "timezone": "UTC",
                        "default_workspace": "admin_workspace"
                    },
                    "password_hash": "$2b$12$K8gU2XtWx4YM9V7pGn1qJ.F4rKGQ8n3Z2mR5sT9xV6wP4bC1dA7hO",  # "securepassword123"
                    "salt": "fixed_salt_for_demo"
                }
                
                audit_info = {
                    "user_email": "system",
                    "ip_address": "127.0.0.1",
                    "user_agent": "auto_initialization"
                }
                
                if self.store_user_credentials("admin@ctodashboard.app", admin_data, audit_info):
                    logger.info("✅ Default admin user created automatically")
                else:
                    logger.error("❌ Failed to create default admin user")
            else:
                logger.info(f"Database has {user_count} existing users - no auto-initialization needed")
                
        except Exception as e:
            logger.error(f"Auto-initialization failed: {e}")
    
    # API Methods - Maintain exact compatibility with original SecureDatabaseManager
    
    def store_user_credentials(self, email: str, user_data: Dict[str, Any], audit_info: Dict[str, Any] = None) -> bool:
        """Store user with encrypted password data"""
        try:
            # Separate sensitive from non-sensitive data
            sensitive_data = {
                "password_hash": user_data.get("password_hash"),
                "salt": user_data.get("salt"),
            }
            
            encrypted_password_data = self.adapter.encrypt_data(sensitive_data) if any(sensitive_data.values()) else None
            
            # Prepare parameters based on database type
            if self.db_type == 'postgresql':
                # PostgreSQL uses %s placeholders
                query = """
                    INSERT INTO secure_users 
                    (email, display_name, encrypted_password_data, workspaces, role, status, preferences, last_login, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (email) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        encrypted_password_data = EXCLUDED.encrypted_password_data,
                        workspaces = EXCLUDED.workspaces,
                        role = EXCLUDED.role,
                        status = EXCLUDED.status,
                        preferences = EXCLUDED.preferences,
                        last_login = EXCLUDED.last_login,
                        updated_at = NOW()
                """
            else:
                # SQLite uses ? placeholders
                query = """
                    INSERT OR REPLACE INTO secure_users 
                    (email, display_name, encrypted_password_data, workspaces, role, status, preferences, last_login, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """
            
            params = (
                email,
                user_data.get("display_name"),
                encrypted_password_data,
                json.dumps(user_data.get("workspaces", [])),
                user_data.get("role", "user"),
                user_data.get("status", "active"),
                json.dumps(user_data.get("preferences", {})),
                user_data.get("last_login")
            )
            
            self.adapter.execute_update(query, params)
            self._audit_log("store_user", "user", email, audit_info, True)
            
            logger.info("User credentials stored successfully", extra={
                "operation": "store_user_credentials",
                "email": email,
                "role": user_data.get("role", "user")
            })
            return True
            
        except Exception as e:
            self._audit_log("store_user", "user", email, audit_info, False, str(e))
            logger.error("Failed to store user credentials", extra={
                "operation": "store_user_credentials",
                "email": email,
                "error": str(e)
            })
            return False
    
    def get_user_credentials(self, email: str, audit_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Retrieve user with decrypted password data"""
        try:
            # Database-specific query syntax
            if self.db_type == 'postgresql':
                query = "SELECT * FROM secure_users WHERE email = %s"
            else:
                query = "SELECT * FROM secure_users WHERE email = ?"
                
            result = self.adapter.execute_query(query, (email,))
            
            if not result:
                self._audit_log("get_user", "user", email, audit_info, False, "User not found")
                return None
            
            row = result[0]
            
            # Decrypt sensitive data
            encrypted_data = row["encrypted_password_data"] if hasattr(row, 'keys') else row[2]
            if encrypted_data:
                sensitive_data = self.adapter.decrypt_data(encrypted_data)
            else:
                sensitive_data = {}
            
            # Combine all user data
            user_data = {
                "email": row["email"] if hasattr(row, 'keys') else row[1],
                "display_name": row["display_name"] if hasattr(row, 'keys') else row[2],
                "workspaces": json.loads(row["workspaces"] or "[]") if hasattr(row, 'keys') else json.loads(row[4] or "[]"),
                "role": row["role"] if hasattr(row, 'keys') else row[5],
                "status": row["status"] if hasattr(row, 'keys') else row[6],
                "preferences": json.loads(row["preferences"] or "{}") if hasattr(row, 'keys') else json.loads(row[7] or "{}"),
                "created_at": row["created_at"] if hasattr(row, 'keys') else row[8],
                "last_login": row["last_login"] if hasattr(row, 'keys') else row[10],
                **sensitive_data
            }
            
            self._audit_log("get_user", "user", email, audit_info, True)
            return user_data
            
        except Exception as e:
            self._audit_log("get_user", "user", email, audit_info, False, str(e))
            logger.error("Failed to retrieve user credentials", extra={
                "operation": "get_user_credentials",
                "email": email,
                "error": str(e)
            })
            return None
    
    def store_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str, 
                                   credentials: Dict[str, Any], audit_info: Dict[str, Any] = None) -> bool:
        """Store assignment connector credentials"""
        try:
            encrypted_credentials = self.adapter.encrypt_data(credentials)
            
            # Database-specific query
            if self.db_type == 'postgresql':
                query = """
                    INSERT INTO secure_credentials 
                    (workspace_id, assignment_id, connector_type, encrypted_credentials, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (workspace_id, assignment_id, connector_type) DO UPDATE SET
                        encrypted_credentials = EXCLUDED.encrypted_credentials,
                        updated_at = NOW()
                """
            else:
                query = """
                    INSERT OR REPLACE INTO secure_credentials 
                    (workspace_id, assignment_id, connector_type, encrypted_credentials, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """
            
            self.adapter.execute_update(query, (workspace_id, assignment_id, connector_type, encrypted_credentials))
            self._audit_log("store_credentials", "credential", f"{workspace_id}/{assignment_id}/{connector_type}", audit_info, True)
            return True
            
        except Exception as e:
            self._audit_log("store_credentials", "credential", f"{workspace_id}/{assignment_id}/{connector_type}", audit_info, False, str(e))
            logger.error("Failed to store assignment credentials", extra={
                "operation": "store_assignment_credentials",
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "connector_type": connector_type,
                "error": str(e)
            })
            return False
    
    def get_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str,
                                 audit_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Retrieve assignment connector credentials"""
        try:
            # Database-specific query
            if self.db_type == 'postgresql':
                query = """
                    SELECT encrypted_credentials FROM secure_credentials 
                    WHERE workspace_id = %s AND assignment_id = %s AND connector_type = %s
                """
            else:
                query = """
                    SELECT encrypted_credentials FROM secure_credentials 
                    WHERE workspace_id = ? AND assignment_id = ? AND connector_type = ?
                """
            
            result = self.adapter.execute_query(query, (workspace_id, assignment_id, connector_type))
            
            if not result:
                self._audit_log("get_credentials", "credential", f"{workspace_id}/{assignment_id}/{connector_type}", audit_info, False, "Credentials not found")
                return None
            
            encrypted_data = result[0][0]
            credentials = self.adapter.decrypt_data(encrypted_data)
            
            self._audit_log("get_credentials", "credential", f"{workspace_id}/{assignment_id}/{connector_type}", audit_info, True)
            return credentials
            
        except Exception as e:
            self._audit_log("get_credentials", "credential", f"{workspace_id}/{assignment_id}/{connector_type}", audit_info, False, str(e))
            logger.error("Failed to retrieve assignment credentials", extra={
                "operation": "get_assignment_credentials",
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "connector_type": connector_type,
                "error": str(e)
            })
            return None
    
    def delete_assignment_credentials(self, workspace_id: str, assignment_id: str, connector_type: str,
                                    audit_info: Dict[str, Any] = None) -> bool:
        """Delete assignment connector credentials"""
        try:
            # Database-specific query
            if self.db_type == 'postgresql':
                query = """
                    DELETE FROM secure_credentials 
                    WHERE workspace_id = %s AND assignment_id = %s AND connector_type = %s
                """
            else:
                query = """
                    DELETE FROM secure_credentials 
                    WHERE workspace_id = ? AND assignment_id = ? AND connector_type = ?
                """
                
            rows_affected = self.adapter.execute_update(query, (workspace_id, assignment_id, connector_type))
            
            if rows_affected > 0:
                self._audit_log("delete_credentials", "credential", f"{workspace_id}/{assignment_id}/{connector_type}", audit_info, True)
                return True
            else:
                self._audit_log("delete_credentials", "credential", f"{workspace_id}/{assignment_id}/{connector_type}", audit_info, False, "Credentials not found")
                return False
                
        except Exception as e:
            self._audit_log("delete_credentials", "credential", f"{workspace_id}/{assignment_id}/{connector_type}", audit_info, False, str(e))
            logger.error("Failed to delete assignment credentials", extra={
                "operation": "delete_assignment_credentials",
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "connector_type": connector_type,
                "error": str(e)
            })
            return False
    
    def list_assignment_credentials(self, workspace_id: str, assignment_id: str) -> Dict[str, bool]:
        """List which connectors have stored credentials for an assignment"""
        try:
            # Database-specific query
            if self.db_type == 'postgresql':
                query = """
                    SELECT connector_type FROM secure_credentials 
                    WHERE workspace_id = %s AND assignment_id = %s
                """
            else:
                query = """
                    SELECT connector_type FROM secure_credentials 
                    WHERE workspace_id = ? AND assignment_id = ?
                """
                
            result = self.adapter.execute_query(query, (workspace_id, assignment_id))
            
            # Return status for all known connector types
            connector_types = ['github', 'jira', 'aws', 'openai']
            configured_types = [row[0] for row in result] if result else []
            
            return {connector_type: connector_type in configured_types for connector_type in connector_types}
            
        except Exception as e:
            logger.error("Failed to list assignment credentials", extra={
                "operation": "list_assignment_credentials",
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "error": str(e)
            })
            return {connector_type: False for connector_type in ['github', 'jira', 'aws', 'openai']}
    
    def get_workspace_assignments(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all assignments for workspace with credential status"""
        try:
            # Database-specific query
            if self.db_type == 'postgresql':
                query = "SELECT * FROM secure_assignments WHERE workspace_id = %s"
            else:
                query = "SELECT * FROM secure_assignments WHERE workspace_id = ?"
                
            result = self.adapter.execute_query(query, (workspace_id,))
            
            assignments = []
            for row in result:
                assignment = {
                    "id": row["id"] if hasattr(row, 'keys') else row[0],
                    "workspace_id": row["workspace_id"] if hasattr(row, 'keys') else row[1],
                    "name": row["name"] if hasattr(row, 'keys') else row[2],
                    "description": row["description"] if hasattr(row, 'keys') else row[3],
                    "assignment_type": row["assignment_type"] if hasattr(row, 'keys') else row[4],
                    "status": row["status"] if hasattr(row, 'keys') else row[5],
                    "created_at": row["created_at"] if hasattr(row, 'keys') else row[7],
                }
                
                # Add credential status
                assignment["credentials"] = self.list_assignment_credentials(workspace_id, assignment["id"])
                assignments.append(assignment)
            
            return assignments
            
        except Exception as e:
            logger.error("Failed to get workspace assignments", extra={
                "operation": "get_workspace_assignments",
                "workspace_id": workspace_id,
                "error": str(e)
            })
            return []
    
    def store_assignment(self, assignment_data: Dict[str, Any]) -> bool:
        """Store assignment metadata (without credentials)"""
        try:
            # Database-specific query - use actual column names from existing schema
            if self.db_type == 'postgresql':
                query = """
                    INSERT INTO secure_assignments 
                    (assignment_id, workspace_id, name, description, team_size, monthly_burn_rate, status, metrics_config, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (assignment_id, workspace_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        team_size = EXCLUDED.team_size,
                        monthly_burn_rate = EXCLUDED.monthly_burn_rate,
                        status = EXCLUDED.status,
                        metrics_config = EXCLUDED.metrics_config,
                        updated_at = NOW()
                """
            else:
                query = """
                    INSERT OR REPLACE INTO secure_assignments 
                    (assignment_id, workspace_id, name, description, team_size, monthly_burn_rate, status, metrics_config, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """
            
            # Convert metrics config to JSON string if present  
            metrics_config = assignment_data.get("metrics_config", {})
            metrics_json = json.dumps(metrics_config) if metrics_config else None
            
            params = (
                assignment_data.get("assignment_id"),
                assignment_data.get("workspace_id"),
                assignment_data.get("name"),
                assignment_data.get("description"),
                assignment_data.get("team_size"),
                assignment_data.get("monthly_burn_rate"),
                assignment_data.get("status", "active"),
                metrics_json
            )
            
            self.adapter.execute_update(query, params)
            return True
            
        except Exception as e:
            logger.error("Failed to store assignment", extra={
                "operation": "store_assignment",
                "assignment_id": assignment_data.get("id"),
                "error": str(e)
            })
            return False
    
    def _audit_log(self, action: str, entity_type: str, entity_id: str, audit_info: Dict[str, Any] = None, 
                  success: bool = True, error: str = None):
        """Log audit trail for security monitoring"""
        try:
            audit_info = audit_info or {}
            
            # Use legacy schema for existing SQLite database
            if self.db_type == 'postgresql':
                query = """
                    INSERT INTO credential_audit 
                    (action, entity_type, entity_id, user_info, success, error_message, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    action,
                    entity_type,
                    entity_id,
                    json.dumps(audit_info),
                    success,
                    error,
                    audit_info.get("ip_address"),
                    audit_info.get("user_agent")
                )
            else:
                # Legacy SQLite schema compatibility
                query = """
                    INSERT INTO credential_audit 
                    (action, entity_type, entity_id, user_email, success, error_message, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    action,
                    entity_type,
                    entity_id,
                    audit_info.get("user_email", "system"),
                    success,
                    error,
                    audit_info.get("ip_address"),
                    audit_info.get("user_agent")
                )
            
            self.adapter.execute_update(query, params)
            
        except Exception as e:
            logger.error("Failed to write audit log", extra={
                "operation": "audit_log",
                "action": action,
                "error": str(e)
            })
    
    def get_audit_logs(self, limit: int = 100, entity_type: str = None) -> List[Dict[str, Any]]:
        """Get recent audit logs for security monitoring"""
        try:
            # Database-specific query
            if self.db_type == 'postgresql':
                if entity_type:
                    query = """
                        SELECT * FROM credential_audit 
                        WHERE entity_type = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """
                    params = (entity_type, limit)
                else:
                    query = "SELECT * FROM credential_audit ORDER BY created_at DESC LIMIT %s"
                    params = (limit,)
            else:
                if entity_type:
                    query = """
                        SELECT * FROM credential_audit 
                        WHERE entity_type = ? 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """
                    params = (entity_type, limit)
                else:
                    query = "SELECT * FROM credential_audit ORDER BY created_at DESC LIMIT ?"
                    params = (limit,)
            
            result = self.adapter.execute_query(query, params)
            
            logs = []
            for row in result:
                log = {
                    "id": row["id"] if hasattr(row, 'keys') else row[0],
                    "timestamp": row["created_at"] if hasattr(row, 'keys') else row[1],
                    "action": row["action"] if hasattr(row, 'keys') else row[2],
                    "entity_type": row["entity_type"] if hasattr(row, 'keys') else row[3],
                    "entity_id": row["entity_id"] if hasattr(row, 'keys') else row[4],
                    "user_info": json.loads(row["user_info"] or "{}") if hasattr(row, 'keys') else json.loads(row[5] or "{}"),
                    "success": row["success"] if hasattr(row, 'keys') else row[6],
                    "error_message": row["error_message"] if hasattr(row, 'keys') else row[7],
                    "ip_address": row["ip_address"] if hasattr(row, 'keys') else row[8],
                    "user_agent": row["user_agent"] if hasattr(row, 'keys') else row[9]
                }
                logs.append(log)
            
            return logs
            
        except Exception as e:
            logger.error("Failed to get audit logs", extra={
                "operation": "get_audit_logs",
                "error": str(e)
            })
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health and security status"""
        try:
            def _extract_count(result):
                """Extract count value from result (handles both PostgreSQL and SQLite)"""
                if result and len(result) > 0:
                    if hasattr(result[0], 'keys'):
                        # PostgreSQL RealDictRow
                        return result[0]['count']
                    else:
                        # SQLite tuple
                        return result[0][0]
                return 0
            
            # Get user count
            user_result = self.adapter.execute_query("SELECT COUNT(*) FROM secure_users")
            user_count = _extract_count(user_result)
            
            # Get credential count
            cred_result = self.adapter.execute_query("SELECT COUNT(*) FROM secure_credentials")
            cred_count = _extract_count(cred_result)
            
            # Get assignment count
            assignment_result = self.adapter.execute_query("SELECT COUNT(*) FROM secure_assignments")
            assignment_count = _extract_count(assignment_result)
            
            # Get recent audit activity - database-specific syntax
            if self.db_type == 'postgresql':
                audit_query = "SELECT COUNT(*) FROM credential_audit WHERE created_at > NOW() - INTERVAL '24 hours'"
            else:
                # SQLite - use created_at column
                audit_query = "SELECT COUNT(*) FROM credential_audit WHERE created_at > datetime('now', '-24 hours')"
                
            audit_result = self.adapter.execute_query(audit_query)
            recent_audit_count = _extract_count(audit_result)
            
            return {
                "database_connected": True,
                "database_type": self.db_type,
                "adapter_class": self.adapter.__class__.__name__,
                "schema_version": self.adapter.get_schema_version(),
                "statistics": {
                    "users": user_count,
                    "credentials": cred_count,
                    "assignments": assignment_count,
                    "recent_audit_events": recent_audit_count
                },
                "security": {
                    "encryption_enabled": True,
                    "audit_logging": True,
                    "master_key_configured": bool(os.getenv("CREDENTIAL_MASTER_KEY"))
                }
            }
            
        except Exception as e:
            logger.error("Health check failed", extra={
                "operation": "health_check",
                "error": str(e)
            })
            return {
                "database_connected": False,
                "error": str(e)
            }
    
    # Legacy compatibility properties
    @property 
    def db_path(self):
        """Legacy compatibility for db_path access"""
        if self.db_type == 'sqlite':
            return Path(self.connection_config.get('path', 'secure_credentials.db'))
        else:
            return Path(f"{self.db_type}://database")
    
    def _get_connection(self):
        """Legacy compatibility for direct connection access"""
        return self.adapter._connection
    
    def _encrypt_data(self, data):
        """Legacy compatibility for encryption"""
        return self.adapter.encrypt_data(data)
        
    def _decrypt_data(self, encrypted_data):
        """Legacy compatibility for decryption"""
        return self.adapter.decrypt_data(encrypted_data)


# Singleton pattern for backward compatibility
_secure_db_instance = None
_secure_db_lock = threading.Lock()

def get_secure_db() -> SecureDatabaseManager:
    """Get singleton instance of SecureDatabaseManager with thread safety"""
    global _secure_db_instance
    
    if _secure_db_instance is None:
        with _secure_db_lock:
            if _secure_db_instance is None:  # Double-check locking
                logger.info("Creating singleton SecureDatabaseManager instance", extra={
                    "operation": "singleton_creation",
                    "thread_id": threading.current_thread().ident
                })
                _secure_db_instance = SecureDatabaseManager()
                logger.info("Singleton SecureDatabaseManager instance created successfully", extra={
                    "operation": "singleton_created",
                    "thread_id": threading.current_thread().ident
                })
    
    return _secure_db_instance

class _SecureDbProxy:
    """Proxy object for secure_db global instance"""
    def __getattr__(self, name):
        return getattr(get_secure_db(), name)

# Global instance for backward compatibility
secure_db = _SecureDbProxy()