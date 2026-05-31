#!/usr/bin/env python3
"""
Manual Database Initialization Script
⚠️  MANUAL USE ONLY - DO NOT RUN AUTOMATICALLY ON DEPLOYMENT ⚠️

Run this script manually when:
- Setting up database for the first time
- Resetting database completely (destructive)
- Initializing new environment

Usage:
    python scripts/db_init_manual.py
    
Railway usage:
    railway run python scripts/db_init_manual.py
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def ensure_config_directory():
    """Ensure config directory exists with proper permissions"""
    # Railway debugging - check current working directory and environment
    logger.info("Current working directory: %s", os.getcwd())
    logger.info("Contents of current directory: %s", os.listdir('.'))
    logger.info("RAILWAY_ENVIRONMENT: %s", os.getenv("RAILWAY_ENVIRONMENT"))
    
    # Try Railway volume mount path first
    config_dir = Path("config")
    
    # Create directory if it doesn't exist
    try:
        config_dir.mkdir(exist_ok=True, parents=True)
        logger.info("Config directory ready: %s", config_dir.absolute())
    except Exception as e:
        logger.warning("Could not create config directory: %s", e)
        # Fallback to current directory
        config_dir = Path(".")
        logger.info("Using current directory as fallback: %s", config_dir.absolute())
    
    return config_dir

def initialize_secure_database():
    """Initialize the secure database if it doesn't exist"""
    try:
        from services.security.secure_database import secure_db
        
        # Test database connectivity
        health = secure_db.health_check()
        
        if health.get("database_connected"):
            logger.info("Secure database connected successfully")
            logger.info("Database statistics: %s", health.get('statistics', {}))
            logger.info("Encryption available: %s", health.get('encryption_available', False))
            logger.info("Master key configured: %s", health.get('master_key_configured', False))
            return True
        else:
            logger.error("Database connection failed: %s", health.get('error'))
            return False
    
    except Exception as e:
        logger.error("Database initialization error: %s", e, exc_info=True)
        return False

def create_initial_user_if_needed():
    """Create an admin user if no users exist (Railway first run)"""
    try:
        from services.security.secure_database import secure_db
        
        # Check if any users exist
        health = secure_db.health_check()
        user_count = health.get('statistics', {}).get('users', 0)
        
        if user_count == 0:
            logger.info("No users found - creating default admin user")
            
            # Create default admin user
            admin_data = {
                "email": "admin@railway.app",
                "display_name": "Railway Admin",
                "password_hash": "change_on_first_login",  # This should be changed
                "salt": "railway_default_salt",
                "workspaces": ["default_workspace"],
                "role": "admin",
                "status": "active",
                "preferences": {
                    "theme": "light",
                    "timezone": "UTC"
                }
            }
            
            audit_info = {
                "user_email": "system",
                "ip_address": "127.0.0.1",
                "user_agent": "railway_init_script"
            }
            
            if secure_db.store_user_credentials("admin@railway.app", admin_data, audit_info):
                logger.info("Default admin user created: admin@railway.app")
                logger.warning("IMPORTANT: Change the default password immediately!")
                return True
            else:
                logger.error("Failed to create default admin user")
                return False
        else:
            logger.info("Found %d existing users", user_count)
            return True
    
    except Exception as e:
        logger.error("User creation error: %s", e, exc_info=True)
        return False

def main():
    logger.warning("⚠️  MANUAL DATABASE INITIALIZATION SCRIPT ⚠️")
    logger.warning("This script should only be run manually!")
    logger.warning("Do not include in automatic deployment processes!")
    logger.info("🗄️  Manual Database Initialization Starting")
    
    # Step 1: Ensure directories exist
    ensure_config_directory()
    
    # Step 2: Initialize secure database
    if not initialize_secure_database():
        logger.error("Database initialization failed - exiting")
        sys.exit(1)
    
    # Step 3: Create initial user if needed
    if not create_initial_user_if_needed():
        logger.warning("User creation failed but continuing...")
    
    logger.info("Database initialization completed successfully!")
    logger.info("Secure credential storage is ready")
    logger.info("Check Railway logs for any issues")

if __name__ == "__main__":
    main()