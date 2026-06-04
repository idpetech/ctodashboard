#!/usr/bin/env python3
"""
Railway Multi-Schema PostgreSQL Setup
Creates dedicated schemas for each application with shared auth
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# PostgreSQL connection details
POSTGRES_URL = "postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@postgres.railway.internal:5432/railway"

# Schema configuration
SCHEMAS = {
    "auth": {
        "description": "Shared authentication and user management",
        "tables": ["users", "sessions", "user_roles", "user_preferences"]
    },
    "ctodashboard": {
        "description": "CTO Dashboard application data",
        "tables": ["workspaces", "assignments", "credentials", "metrics", "audit_logs"]
    },
    "enaam": {
        "description": "Enaam application data",
        "tables": ["agents", "conversations", "knowledge_base", "integrations"]
    },
    "baassistant": {
        "description": "BA Assistant application data", 
        "tables": ["projects", "requirements", "documents", "analysis"]
    },
    "insightvault": {
        "description": "InsightVault application data",
        "tables": ["captures", "insights", "knowledge_graphs", "exports"]
    }
}

def connect_to_postgres():
    """Connect to PostgreSQL database"""
    try:
        # Parse URL components
        import urllib.parse as urlparse
        url = urlparse.urlparse(POSTGRES_URL)
        
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            user=url.username,
            password=url.password,
            database=url.path[1:]  # Remove leading /
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        logger.info("✅ Connected to PostgreSQL database")
        return conn
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        return None

def create_schemas(conn):
    """Create all application schemas"""
    cursor = conn.cursor()
    
    for schema_name, config in SCHEMAS.items():
        try:
            # Create schema
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            
            # Add comment describing the schema
            cursor.execute(f"COMMENT ON SCHEMA {schema_name} IS '{config['description']}'")
            
            logger.info(f"✅ Schema '{schema_name}' created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create schema '{schema_name}': {e}")
            
    cursor.close()

def create_auth_schema_tables(conn):
    """Create tables in the auth schema for shared authentication"""
    cursor = conn.cursor()
    
    auth_tables = """
    -- Shared users table
    CREATE TABLE IF NOT EXISTS auth.users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        display_name TEXT,
        encrypted_password_data BYTEA,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'active',
        preferences JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    );
    
    -- User sessions for cross-app authentication
    CREATE TABLE IF NOT EXISTS auth.sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES auth.users(id) ON DELETE CASCADE,
        session_token TEXT UNIQUE NOT NULL,
        app_context TEXT NOT NULL, -- 'ctodashboard', 'enaam', etc.
        expires_at TIMESTAMP NOT NULL,
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- User roles and permissions across apps
    CREATE TABLE IF NOT EXISTS auth.user_roles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES auth.users(id) ON DELETE CASCADE,
        app_name TEXT NOT NULL, -- 'ctodashboard', 'enaam', etc.
        role_name TEXT NOT NULL, -- 'admin', 'user', 'viewer', etc.
        permissions JSONB DEFAULT '[]',
        granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        granted_by INTEGER REFERENCES auth.users(id),
        UNIQUE(user_id, app_name)
    );
    
    -- App-specific user preferences
    CREATE TABLE IF NOT EXISTS auth.user_preferences (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES auth.users(id) ON DELETE CASCADE,
        app_name TEXT NOT NULL,
        preferences JSONB DEFAULT '{}',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, app_name)
    );
    
    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_sessions_token ON auth.sessions(session_token);
    CREATE INDEX IF NOT EXISTS idx_sessions_expires ON auth.sessions(expires_at);
    CREATE INDEX IF NOT EXISTS idx_user_roles_app ON auth.user_roles(user_id, app_name);
    CREATE INDEX IF NOT EXISTS idx_user_prefs_app ON auth.user_preferences(user_id, app_name);
    """
    
    try:
        cursor.execute(auth_tables)
        logger.info("✅ Auth schema tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create auth tables: {e}")
        
    cursor.close()

def create_ctodashboard_schema_tables(conn):
    """Create tables in the ctodashboard schema"""
    cursor = conn.cursor()
    
    ctodashboard_tables = """
    -- Workspaces
    CREATE TABLE IF NOT EXISTS ctodashboard.workspaces (
        id SERIAL PRIMARY KEY,
        workspace_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        settings JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Assignments
    CREATE TABLE IF NOT EXISTS ctodashboard.assignments (
        id SERIAL PRIMARY KEY,
        assignment_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL REFERENCES ctodashboard.workspaces(workspace_id),
        name TEXT,
        description TEXT,
        team_size INTEGER,
        monthly_burn_rate INTEGER,
        status TEXT DEFAULT 'active',
        metrics_config JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(assignment_id, workspace_id)
    );
    
    -- Encrypted credentials
    CREATE TABLE IF NOT EXISTS ctodashboard.credentials (
        id SERIAL PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        connector_type TEXT NOT NULL,
        encrypted_credentials BYTEA NOT NULL,
        auth_configured BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(workspace_id, assignment_id, connector_type),
        FOREIGN KEY(workspace_id, assignment_id) REFERENCES ctodashboard.assignments(workspace_id, assignment_id)
    );
    
    -- Metrics data
    CREATE TABLE IF NOT EXISTS ctodashboard.metrics (
        id SERIAL PRIMARY KEY,
        assignment_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        value JSONB NOT NULL,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(workspace_id, assignment_id) REFERENCES ctodashboard.assignments(workspace_id, assignment_id)
    );
    
    -- Audit logs
    CREATE TABLE IF NOT EXISTS ctodashboard.audit_logs (
        id SERIAL PRIMARY KEY,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        user_id INTEGER REFERENCES auth.users(id),
        workspace_id TEXT,
        connector_type TEXT,
        success BOOLEAN,
        error_message TEXT,
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_assignments_workspace ON ctodashboard.assignments(workspace_id);
    CREATE INDEX IF NOT EXISTS idx_credentials_lookup ON ctodashboard.credentials(workspace_id, assignment_id, connector_type);
    CREATE INDEX IF NOT EXISTS idx_metrics_assignment ON ctodashboard.metrics(assignment_id, recorded_at);
    CREATE INDEX IF NOT EXISTS idx_audit_entity ON ctodashboard.audit_logs(entity_type, entity_id);
    """
    
    try:
        cursor.execute(ctodashboard_tables)
        logger.info("✅ CTO Dashboard schema tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create ctodashboard tables: {e}")
        
    cursor.close()

def create_placeholder_schemas(conn):
    """Create placeholder tables for other app schemas"""
    cursor = conn.cursor()
    
    # Create basic placeholder tables for other apps
    other_schemas = ['enaam', 'baassistant', 'insightvault']
    
    for schema in other_schemas:
        try:
            placeholder_sql = f"""
            -- Placeholder table for {schema} schema
            CREATE TABLE IF NOT EXISTS {schema}.app_metadata (
                id SERIAL PRIMARY KEY,
                app_name TEXT DEFAULT '{schema}',
                version TEXT DEFAULT '1.0.0',
                schema_initialized BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Insert initial metadata
            INSERT INTO {schema}.app_metadata (app_name, schema_initialized)
            VALUES ('{schema}', FALSE)
            ON CONFLICT DO NOTHING;
            """
            
            cursor.execute(placeholder_sql)
            logger.info(f"✅ Placeholder tables created for {schema} schema")
            
        except Exception as e:
            logger.error(f"❌ Failed to create placeholder for {schema}: {e}")
            
    cursor.close()

def create_schema_version_tracking(conn):
    """Create schema version tracking table"""
    cursor = conn.cursor()
    
    version_sql = """
    -- Schema version tracking across all schemas
    CREATE TABLE IF NOT EXISTS public.schema_versions (
        id SERIAL PRIMARY KEY,
        schema_name TEXT NOT NULL,
        version INTEGER NOT NULL,
        description TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(schema_name, version)
    );
    
    -- Insert initial versions
    INSERT INTO public.schema_versions (schema_name, version, description) VALUES
    ('auth', 1, 'Initial auth schema with shared authentication'),
    ('ctodashboard', 1, 'Initial ctodashboard schema migration from SQLite'),
    ('enaam', 1, 'Initial enaam schema placeholder'),
    ('baassistant', 1, 'Initial baassistant schema placeholder'),
    ('insightvault', 1, 'Initial insightvault schema placeholder')
    ON CONFLICT DO NOTHING;
    """
    
    try:
        cursor.execute(version_sql)
        logger.info("✅ Schema version tracking created")
    except Exception as e:
        logger.error(f"❌ Failed to create version tracking: {e}")
        
    cursor.close()

def grant_permissions(conn):
    """Grant appropriate permissions on schemas"""
    cursor = conn.cursor()
    
    permissions = [
        # Grant usage on all schemas to postgres user
        "GRANT USAGE ON SCHEMA auth TO postgres",
        "GRANT USAGE ON SCHEMA ctodashboard TO postgres",  
        "GRANT USAGE ON SCHEMA enaam TO postgres",
        "GRANT USAGE ON SCHEMA baassistant TO postgres",
        "GRANT USAGE ON SCHEMA insightvault TO postgres",
        
        # Grant all privileges on tables to postgres user
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO postgres",
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ctodashboard TO postgres",
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA enaam TO postgres", 
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA baassistant TO postgres",
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA insightvault TO postgres",
        
        # Grant sequence privileges
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO postgres",
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ctodashboard TO postgres",
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA enaam TO postgres",
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA baassistant TO postgres", 
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA insightvault TO postgres",
    ]
    
    for perm in permissions:
        try:
            cursor.execute(perm)
        except Exception as e:
            logger.warning(f"Permission warning: {e}")
            
    logger.info("✅ Permissions granted")
    cursor.close()

def verify_setup(conn):
    """Verify the multi-schema setup"""
    cursor = conn.cursor()
    
    try:
        # Check schemas exist
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('auth', 'ctodashboard', 'enaam', 'baassistant', 'insightvault')")
        schemas = [row[0] for row in cursor.fetchall()]
        
        logger.info("📋 Setup verification:")
        for schema in SCHEMAS.keys():
            if schema in schemas:
                logger.info(f"   ✅ {schema} schema exists")
                
                # Count tables in each schema
                cursor.execute(f"""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = '{schema}'
                """)
                table_count = cursor.fetchone()[0]
                logger.info(f"      Tables: {table_count}")
            else:
                logger.error(f"   ❌ {schema} schema missing")
                
        # Check version tracking
        cursor.execute("SELECT schema_name, version FROM public.schema_versions ORDER BY schema_name")
        versions = cursor.fetchall()
        logger.info("📋 Schema versions:")
        for schema_name, version in versions:
            logger.info(f"   {schema_name}: v{version}")
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        
    cursor.close()

def main():
    """Main setup process"""
    logger.info("🚀 Railway Multi-Schema PostgreSQL Setup")
    logger.info("=" * 50)
    
    # Connect to PostgreSQL
    conn = connect_to_postgres()
    if not conn:
        sys.exit(1)
        
    try:
        # Create schemas
        logger.info("🔄 Creating schemas...")
        create_schemas(conn)
        
        # Create auth tables
        logger.info("🔄 Creating auth schema tables...")
        create_auth_schema_tables(conn)
        
        # Create ctodashboard tables  
        logger.info("🔄 Creating ctodashboard schema tables...")
        create_ctodashboard_schema_tables(conn)
        
        # Create placeholder schemas
        logger.info("🔄 Creating placeholder schemas...")
        create_placeholder_schemas(conn)
        
        # Create version tracking
        logger.info("🔄 Creating schema version tracking...")
        create_schema_version_tracking(conn)
        
        # Grant permissions
        logger.info("🔄 Granting permissions...")
        grant_permissions(conn)
        
        # Verify setup
        logger.info("🔍 Verifying setup...")
        verify_setup(conn)
        
        logger.info("")
        logger.info("🎉 MULTI-SCHEMA SETUP COMPLETE!")
        logger.info("   📁 auth schema: Shared authentication")
        logger.info("   📁 ctodashboard schema: CTO Dashboard data")  
        logger.info("   📁 enaam schema: Enaam application")
        logger.info("   📁 baassistant schema: BA Assistant")
        logger.info("   📁 insightvault schema: InsightVault")
        logger.info("")
        logger.info("🔗 Connection string for ctodashboard:")
        logger.info("   DATABASE_URL=postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@postgres.railway.internal:5432/railway?options=-csearch_path%3Dctodashboard,auth")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()