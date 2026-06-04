#!/usr/bin/env python3
"""
Railway Deployment Migration Script
This runs INSIDE Railway to create the ctodashboard schema
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check if we're running in Railway environment"""
    railway_env = os.getenv("RAILWAY_ENVIRONMENT")
    if not railway_env:
        logger.warning("Not running in Railway environment")
        logger.info("This script should be run during Railway deployment")
        return False
    
    logger.info(f"✅ Running in Railway environment: {railway_env}")
    return True

def create_schema_in_railway():
    """Create ctodashboard schema in Railway PostgreSQL"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Use external DATABASE_URL (cross-project)
        connection_url = os.getenv("DATABASE_URL")
        if not connection_url:
            raise Exception("DATABASE_URL environment variable not set")
        
        # Remove schema parameter for connection, add it back later
        if "?options=" in connection_url:
            connection_url = connection_url.split("?options=")[0]
        
        conn = psycopg2.connect(connection_url, cursor_factory=RealDictCursor)
        conn.autocommit = True
        
        cursor = conn.cursor()
        
        # Create schema and tables
        schema_sql = """
        -- Create ctodashboard schema
        CREATE SCHEMA IF NOT EXISTS ctodashboard;
        COMMENT ON SCHEMA ctodashboard IS 'CTO Dashboard application data';
        
        -- Set search path
        SET search_path TO ctodashboard, public;
        
        -- Users table
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
        VALUES (1, 'Initial ctodashboard schema created in Railway')
        ON CONFLICT (version) DO NOTHING;
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_users_email ON ctodashboard.users(email);
        CREATE INDEX IF NOT EXISTS idx_workspaces_id ON ctodashboard.workspaces(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_assignments_workspace ON ctodashboard.assignments(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_credentials_lookup ON ctodashboard.credentials(workspace_id, assignment_id, connector_type);
        CREATE INDEX IF NOT EXISTS idx_audit_entity ON ctodashboard.audit_logs(entity_type, entity_id);
        """
        
        cursor.execute(schema_sql)
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'ctodashboard'
            ORDER BY table_name
        """)
        tables = [row['table_name'] for row in cursor.fetchall()]
        
        logger.info("✅ Railway PostgreSQL schema created successfully!")
        logger.info(f"   Created tables: {', '.join(tables)}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create Railway schema: {e}")
        return False

def main():
    """Main Railway migration process"""
    logger.info("🚀 Railway PostgreSQL Schema Creation")
    logger.info("=====================================")
    
    # Check environment
    if not check_environment():
        # Create schema anyway for testing
        logger.info("Proceeding with schema creation...")
    
    # Create schema
    if create_schema_in_railway():
        logger.info("🎉 Railway PostgreSQL setup complete!")
        logger.info("   The ctodashboard schema is ready for use")
        sys.exit(0)
    else:
        logger.error("❌ Railway PostgreSQL setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()