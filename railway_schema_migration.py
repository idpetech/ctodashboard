# DEPRECATED: see docs/DEPRECATION-MANIFEST.md — do not use in production paths.
#!/usr/bin/env python3
"""
Railway Schema Migration for CTODashboard
Migrate SQLite data to ctodashboard schema in shared PostgreSQL
"""

import os
import sys
import json
import sqlite3
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Shared PostgreSQL connection
POSTGRES_URL = "postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@postgres.railway.internal:5432/railway"

def connect_to_postgres():
    """Connect to shared PostgreSQL with schema support"""
    try:
        conn = psycopg2.connect(POSTGRES_URL, cursor_factory=RealDictCursor)
        conn.autocommit = True
        logger.info("✅ Connected to shared PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        return None

def create_ctodashboard_schema(conn):
    """Create ctodashboard schema and tables"""
    cursor = conn.cursor()
    
    schema_sql = """
    -- Create ctodashboard schema
    CREATE SCHEMA IF NOT EXISTS ctodashboard;
    COMMENT ON SCHEMA ctodashboard IS 'CTO Dashboard application data';
    
    -- Set search path
    SET search_path TO ctodashboard, public;
    
    -- Users table (for now, until we have shared auth)
    CREATE TABLE IF NOT EXISTS ctodashboard.users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        display_name TEXT,
        encrypted_password_data BYTEA,
        workspaces TEXT,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'active', 
        preferences TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    );
    
    -- Workspaces
    CREATE TABLE IF NOT EXISTS ctodashboard.workspaces (
        id SERIAL PRIMARY KEY,
        workspace_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        settings TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Assignments  
    CREATE TABLE IF NOT EXISTS ctodashboard.assignments (
        id SERIAL PRIMARY KEY,
        assignment_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        name TEXT,
        description TEXT,
        team_size INTEGER,
        monthly_burn_rate INTEGER,
        status TEXT DEFAULT 'active',
        metrics_config TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(assignment_id, workspace_id)
    );
    
    -- Credentials
    CREATE TABLE IF NOT EXISTS ctodashboard.credentials (
        id SERIAL PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        connector_type TEXT NOT NULL,
        encrypted_credentials BYTEA NOT NULL,
        auth_configured BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(workspace_id, assignment_id, connector_type)
    );
    
    -- Audit logs
    CREATE TABLE IF NOT EXISTS ctodashboard.audit_logs (
        id SERIAL PRIMARY KEY,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL, 
        entity_id TEXT NOT NULL,
        user_email TEXT,
        workspace_id TEXT,
        connector_type TEXT,
        success BOOLEAN,
        error_message TEXT,
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Schema version tracking
    CREATE TABLE IF NOT EXISTS ctodashboard.schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    );
    
    -- Insert initial version
    INSERT INTO ctodashboard.schema_version (version, description) 
    VALUES (1, 'Initial ctodashboard schema from SQLite migration')
    ON CONFLICT (version) DO NOTHING;
    
    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_users_email ON ctodashboard.users(email);
    CREATE INDEX IF NOT EXISTS idx_workspaces_id ON ctodashboard.workspaces(workspace_id);
    CREATE INDEX IF NOT EXISTS idx_assignments_workspace ON ctodashboard.assignments(workspace_id);
    CREATE INDEX IF NOT EXISTS idx_credentials_lookup ON ctodashboard.credentials(workspace_id, assignment_id, connector_type);
    CREATE INDEX IF NOT EXISTS idx_audit_entity ON ctodashboard.audit_logs(entity_type, entity_id);
    """
    
    try:
        cursor.execute(schema_sql)
        logger.info("✅ CTODashboard schema created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create schema: {e}")
        return False
    finally:
        cursor.close()

def migrate_sqlite_data(conn):
    """Migrate data from SQLite to PostgreSQL ctodashboard schema"""
    sqlite_path = "config/secure_credentials.db"
    
    if not os.path.exists(sqlite_path):
        logger.warning(f"❌ SQLite database not found: {sqlite_path}")
        return False
        
    logger.info(f"📖 Reading SQLite database: {sqlite_path}")
    
    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Get PostgreSQL cursor
        pg_cursor = conn.cursor()
        
        # Set schema
        pg_cursor.execute("SET search_path TO ctodashboard, public")
        
        # Migrate users
        sqlite_cursor.execute("SELECT * FROM secure_users")
        users = sqlite_cursor.fetchall()
        
        for user in users:
            pg_cursor.execute("""
                INSERT INTO users 
                (email, display_name, encrypted_password_data, workspaces, role, status, preferences, created_at, updated_at, last_login)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    updated_at = EXCLUDED.updated_at
            """, (
                user['email'], user['display_name'], user['encrypted_password_data'],
                user['workspaces'], user['role'], user['status'], user['preferences'],
                user['created_at'], user['updated_at'], user['last_login']
            ))
        logger.info(f"   ✅ Migrated {len(users)} users")
        
        # Migrate workspaces
        sqlite_cursor.execute("SELECT * FROM secure_workspaces")
        workspaces = sqlite_cursor.fetchall()
        
        for workspace in workspaces:
            pg_cursor.execute("""
                INSERT INTO workspaces 
                (workspace_id, name, description, settings, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    settings = EXCLUDED.settings,
                    updated_at = EXCLUDED.updated_at
            """, (
                workspace['workspace_id'], workspace['name'], workspace['description'],
                workspace.get('settings'), workspace['created_at'], workspace['updated_at']
            ))
        logger.info(f"   ✅ Migrated {len(workspaces)} workspaces")
        
        # Migrate assignments
        sqlite_cursor.execute("SELECT * FROM secure_assignments")
        assignments = sqlite_cursor.fetchall()
        
        for assignment in assignments:
            pg_cursor.execute("""
                INSERT INTO assignments 
                (assignment_id, workspace_id, name, description, team_size, monthly_burn_rate, status, metrics_config, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (assignment_id, workspace_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    team_size = EXCLUDED.team_size,
                    monthly_burn_rate = EXCLUDED.monthly_burn_rate,
                    status = EXCLUDED.status,
                    metrics_config = EXCLUDED.metrics_config,
                    updated_at = EXCLUDED.updated_at
            """, (
                assignment['assignment_id'], assignment['workspace_id'], assignment['name'],
                assignment['description'], assignment['team_size'], assignment['monthly_burn_rate'],
                assignment['status'], assignment.get('metrics_config'), 
                assignment['created_at'], assignment['updated_at']
            ))
        logger.info(f"   ✅ Migrated {len(assignments)} assignments")
        
        # Migrate credentials
        sqlite_cursor.execute("SELECT * FROM secure_credentials")
        credentials = sqlite_cursor.fetchall()
        
        for credential in credentials:
            pg_cursor.execute("""
                INSERT INTO credentials 
                (workspace_id, assignment_id, connector_type, encrypted_credentials, auth_configured, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, assignment_id, connector_type) DO UPDATE SET
                    encrypted_credentials = EXCLUDED.encrypted_credentials,
                    auth_configured = EXCLUDED.auth_configured,
                    updated_at = EXCLUDED.updated_at
            """, (
                credential['workspace_id'], credential['assignment_id'], credential['connector_type'],
                credential['encrypted_credentials'], credential['auth_configured'],
                credential['created_at'], credential['updated_at']
            ))
        logger.info(f"   ✅ Migrated {len(credentials)} credentials")
        
        # Migrate audit logs
        sqlite_cursor.execute("SELECT * FROM credential_audit")
        audit_logs = sqlite_cursor.fetchall()
        
        for audit in audit_logs:
            pg_cursor.execute("""
                INSERT INTO audit_logs 
                (action, entity_type, entity_id, user_email, workspace_id, connector_type, success, error_message, ip_address, user_agent, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                audit['action'], audit['entity_type'], audit['entity_id'], audit['user_email'],
                audit['workspace_id'], audit['connector_type'], audit['success'], audit['error_message'],
                audit['ip_address'], audit['user_agent'], audit['created_at']
            ))
        logger.info(f"   ✅ Migrated {len(audit_logs)} audit logs")
        
        sqlite_conn.close()
        pg_cursor.close()
        
        logger.info("🎉 Data migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_database_config():
    """Update secure_database.py to use PostgreSQL with ctodashboard schema"""
    logger.info("🔧 Updating database configuration...")
    
    config_update = """
# Add this to your Railway environment variables:
DATABASE_URL=postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@postgres.railway.internal:5432/railway?options=-csearch_path%3Dctodashboard

# Or set these environment variables:
POSTGRESQL_HOST=postgres.railway.internal
POSTGRESQL_PORT=5432
POSTGRESQL_DATABASE=railway
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr
POSTGRESQL_SCHEMA=ctodashboard
    """
    
    logger.info("📋 Configuration required:")
    logger.info(config_update)

def verify_migration(conn):
    """Verify the migration was successful"""
    try:
        cursor = conn.cursor()
        cursor.execute("SET search_path TO ctodashboard, public")
        
        # Check table counts
        tables = ['users', 'workspaces', 'assignments', 'credentials', 'audit_logs']
        
        logger.info("📊 Migration verification:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"   {table}: {count} records")
            
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main migration process"""
    logger.info("🚀 CTODashboard PostgreSQL Schema Migration")
    logger.info("=" * 50)
    
    # Connect to PostgreSQL
    conn = connect_to_postgres()
    if not conn:
        sys.exit(1)
        
    try:
        # Create schema
        if not create_ctodashboard_schema(conn):
            sys.exit(1)
            
        # Migrate data  
        if not migrate_sqlite_data(conn):
            sys.exit(1)
            
        # Verify migration
        if not verify_migration(conn):
            sys.exit(1)
            
        # Show config
        update_database_config()
        
        logger.info("")
        logger.info("🎉 SCHEMA MIGRATION COMPLETE!")
        logger.info("   📁 ctodashboard schema created in shared PostgreSQL")
        logger.info("   🔄 All SQLite data migrated successfully")
        logger.info("   🔗 Update your DATABASE_URL to use the schema")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()