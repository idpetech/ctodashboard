"""
Database Abstraction Layer for Clean Migration Between Any Database System
Supports SQLite, PostgreSQL, MySQL, MongoDB, etc. with unified interface
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet

from config.logging_config import get_logger
logger = get_logger(__name__)


class DatabaseAdapter(ABC):
    """
    Abstract base class for database adapters.
    Provides unified interface for any database backend.
    """
    
    def __init__(self, connection_config: Dict[str, Any], encryption_key: Fernet):
        self.config = connection_config
        self.encryption_key = encryption_key
        self._connection = None
        
    @abstractmethod
    def connect(self) -> bool:
        """Establish database connection"""
        pass
        
    @abstractmethod
    def disconnect(self):
        """Close database connection"""
        pass
        
    @abstractmethod
    def create_tables(self):
        """Create all required tables with proper schema"""
        pass
        
    @abstractmethod
    def execute_query(self, query: str, params: Tuple = None) -> Any:
        """Execute a query and return results"""
        pass
        
    @abstractmethod
    def execute_update(self, query: str, params: Tuple = None) -> int:
        """Execute update/insert/delete and return affected rows"""
        pass
        
    @abstractmethod
    def begin_transaction(self):
        """Start database transaction"""
        pass
        
    @abstractmethod
    def commit_transaction(self):
        """Commit database transaction"""
        pass
        
    @abstractmethod
    def rollback_transaction(self):
        """Rollback database transaction"""  
        pass
        
    @abstractmethod
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        pass
        
    @abstractmethod
    def get_schema_version(self) -> int:
        """Get current database schema version"""
        pass
        
    @abstractmethod
    def set_schema_version(self, version: int, description: str = None):
        """Set database schema version"""
        pass
        
    # Common utility methods (database-agnostic)
    def encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt dictionary data"""
        try:
            json_str = json.dumps(data, sort_keys=True)
            return self.encryption_key.encrypt(json_str.encode())
        except Exception as e:
            logger.error("Encryption failed", extra={
                "operation": "encrypt_data",
                "error": str(e)
            })
            raise
            
    def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt data back to dictionary"""
        try:
            decrypted_bytes = self.encryption_key.decrypt(encrypted_data)
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            logger.error("Decryption failed", extra={
                "operation": "decrypt_data", 
                "error": str(e)
            })
            raise


class SQLiteAdapter(DatabaseAdapter):
    # DEPRECATED: scheduled for removal — see docs/DEPRECATION-MANIFEST.md

    """SQLite implementation of database adapter"""
    
    def __init__(self, connection_config: Dict[str, Any], encryption_key: Fernet):
        super().__init__(connection_config, encryption_key)
        import sqlite3
        self.sqlite3 = sqlite3
        
    def connect(self) -> bool:
        try:
            db_path = self.config.get('path', 'secure_credentials.db')
            self._connection = self.sqlite3.connect(
                db_path,
                check_same_thread=False,
                isolation_level=None  # autocommit mode
            )
            self._connection.row_factory = self.sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            logger.info("SQLite connection established", extra={
                "operation": "db_connect",
                "adapter": "sqlite",
                "path": db_path
            })
            return True
        except Exception as e:
            logger.error("SQLite connection failed", extra={
                "operation": "db_connect",
                "adapter": "sqlite",
                "error": str(e)
            })
            return False
            
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
            
    def create_tables(self):
        """Create SQLite tables with schema"""
        schema_sql = [
            """
            CREATE TABLE IF NOT EXISTS secure_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT,
                encrypted_password_data BLOB NOT NULL,
                workspaces TEXT,
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'active',
                preferences TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS secure_workspaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                encrypted_config_data BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS secure_assignments (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                assignment_type TEXT,
                status TEXT DEFAULT 'active',
                encrypted_metadata BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workspace_id) REFERENCES secure_workspaces(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS secure_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL,
                assignment_id TEXT NOT NULL,
                connector_type TEXT NOT NULL,
                encrypted_credentials BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workspace_id, assignment_id, connector_type),
                FOREIGN KEY (workspace_id) REFERENCES secure_workspaces(id),
                FOREIGN KEY (assignment_id) REFERENCES secure_assignments(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS credential_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                user_info TEXT,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for sql in schema_sql:
            self.execute_update(sql)
            
    def execute_query(self, query: str, params: Tuple = None) -> Any:
        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            logger.error("Query execution failed", extra={
                "operation": "execute_query",
                "query": query[:100] + "..." if len(query) > 100 else query,
                "error": str(e)
            })
            raise
            
    def execute_update(self, query: str, params: Tuple = None) -> int:
        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount
        except Exception as e:
            logger.error("Update execution failed", extra={
                "operation": "execute_update", 
                "query": query[:100] + "..." if len(query) > 100 else query,
                "error": str(e)
            })
            raise
            
    def begin_transaction(self):
        self._connection.execute("BEGIN")
        
    def commit_transaction(self):
        self._connection.execute("COMMIT")
        
    def rollback_transaction(self):
        self._connection.execute("ROLLBACK")
        
    def check_table_exists(self, table_name: str) -> bool:
        result = self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return len(result) > 0
        
    def get_schema_version(self) -> int:
        if not self.check_table_exists('schema_version'):
            return 0
        result = self.execute_query("SELECT MAX(version) FROM schema_version")
        return result[0][0] if result and result[0][0] else 0
        
    def set_schema_version(self, version: int, description: str = None):
        self.execute_update(
            "INSERT INTO schema_version (version, description) VALUES (?, ?)",
            (version, description)
        )


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL implementation of database adapter"""
    
    def __init__(self, connection_config: Dict[str, Any], encryption_key: Fernet):
        super().__init__(connection_config, encryption_key)
        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
        except ImportError:
            raise ImportError("psycopg2 required for PostgreSQL adapter. Install with: pip install psycopg2-binary")
        
    def connect(self) -> bool:
        try:
            self._connection = self.psycopg2.connect(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 5432),
                database=self.config.get('database'),
                user=self.config.get('user'),
                password=self.config.get('password'),
                sslmode=self.config.get('sslmode', 'prefer')
            )
            self._connection.autocommit = True
            
            # Set search path if specified
            search_path = self.config.get('search_path', 'public')
            if search_path and search_path != 'public':
                cursor = self._connection.cursor()
                cursor.execute(f"SET search_path TO {search_path}, public")
                cursor.close()
                logger.info(f"PostgreSQL search_path set to: {search_path}")
            
            logger.info("PostgreSQL connection established", extra={
                "operation": "db_connect",
                "adapter": "postgresql",
                "host": self.config.get('host'),
                "database": self.config.get('database'),
                "schema": search_path
            })
            return True
        except Exception as e:
            logger.error("PostgreSQL connection failed", extra={
                "operation": "db_connect",
                "adapter": "postgresql",
                "error": str(e)
            })
            return False
            
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
            
    def create_tables(self):
        """Create tables from canonical_schema (single source of truth)."""
        from .canonical_schema import apply_canonical_schema, SCHEMA_NAME

        search_path = self.config.get("search_path") or SCHEMA_NAME
        apply_canonical_schema(self._connection, search_path=search_path)

    def execute_query(self, query: str, params: Tuple = None) -> Any:
        try:
            cursor = self._connection.cursor(cursor_factory=self.extras.RealDictCursor)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            logger.error("PostgreSQL query execution failed", extra={
                "operation": "execute_query",
                "query": query[:100] + "..." if len(query) > 100 else query,
                "error": str(e)
            })
            raise
            
    def execute_update(self, query: str, params: Tuple = None) -> int:
        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount
        except Exception as e:
            logger.error("PostgreSQL update execution failed", extra={
                "operation": "execute_update",
                "query": query[:100] + "..." if len(query) > 100 else query, 
                "error": str(e)
            })
            raise
            
    def begin_transaction(self):
        self._connection.autocommit = False
        
    def commit_transaction(self):
        self._connection.commit()
        self._connection.autocommit = True
        
    def rollback_transaction(self):
        self._connection.rollback()
        self._connection.autocommit = True
        
    def check_table_exists(self, table_name: str) -> bool:
        schema = self.config.get("search_path") or "ctodashboard"
        result = self.execute_query(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            LIMIT 1
            """,
            (schema, table_name),
        )
        return len(result) > 0
        
    def get_schema_version(self) -> int:
        if not self.check_table_exists('schema_version'):
            return 0
        result = self.execute_query("SELECT MAX(version) FROM schema_version")
        return result[0]['max'] if result and result[0]['max'] else 0
        
    def set_schema_version(self, version: int, description: str = None):
        self.execute_update(
            "INSERT INTO schema_version (version, description) VALUES (%s, %s)",
            (version, description)
        )


def create_database_adapter(db_type: str, connection_config: Dict[str, Any], encryption_key: Fernet) -> DatabaseAdapter:
    """Factory — PostgreSQL only (see docs/POSTGRES-SINGLE-SOURCE-PLAN.md)."""
    if db_type != "postgresql":
        raise ValueError(
            f"Unsupported database type: {db_type}. "
            "Only postgresql is supported. Set DATABASE_URL to a PostgreSQL URL."
        )
    return PostgreSQLAdapter(connection_config, encryption_key)


def _parse_postgresql_config(database_url: str) -> Dict[str, Any]:
    """Parse PostgreSQL URL into connection configuration"""
    from urllib.parse import urlparse, parse_qs
    
    parsed = urlparse(database_url)
    
    # Extract search_path from query parameters
    from .canonical_schema import SCHEMA_NAME
    search_path = SCHEMA_NAME  # Default application schema
    if parsed.query:
        query_params = parse_qs(parsed.query)
        # Check for options parameter with search_path
        options = query_params.get('options', [])
        for option in options:
            if 'search_path' in option:
                # Extract schema from -csearch_path=schema or -csearch_path%3Dschema
                if '=' in option:
                    search_path = option.split('=')[1].replace('%3D', '=').replace('%2C', ',')
    
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password,
        'sslmode': 'require' if 'railway' in str(parsed.hostname) else 'prefer',
        'search_path': search_path
    }

def parse_database_url(database_url: str) -> Tuple[str, Dict[str, Any]]:
    """Parse database URL into type and connection config"""
    
    if database_url.startswith('sqlite:///'):
        raise ValueError(
            "SQLite is no longer supported. Use PostgreSQL DATABASE_URL with ctodashboard search_path."
        )
    elif database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
        return 'postgresql', _parse_postgresql_config(database_url)
    else:
        raise ValueError(f"Unsupported database URL format: {database_url}")