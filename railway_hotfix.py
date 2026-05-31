#!/usr/bin/env python3
"""
Railway Hotfix for 401 Issues
Quick fix to address authentication and DB initialization problems
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_authentication_setup():
    """Check if authentication is properly configured"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from services.auth.user_service import UserService
        from services.security.secure_database import secure_db
        
        # Check database health
        health = secure_db.health_check()
        logger.info(f"Database health: {health}")
        
        if not health.get("database_connected"):
            logger.error("Database not connected - this might cause 401 errors")
            return False
            
        # Check if users exist
        user_count = health.get('statistics', {}).get('users', 0)
        logger.info(f"User count: {user_count}")
        
        if user_count == 0:
            logger.warning("No users found - authentication will fail")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Authentication check failed: {e}")
        return False

def fix_railway_deployment():
    """Quick fixes for Railway deployment issues"""
    try:
        # Ensure we're not trying to run the old init script
        old_script = Path("railway_init_db.py")
        if old_script.exists():
            logger.warning("Found old railway_init_db.py - removing")
            old_script.unlink()
        
        # Check auth setup
        auth_ok = check_authentication_setup()
        
        if not auth_ok:
            logger.error("Authentication setup has issues")
            logger.info("Consider running: railway run python scripts/db_init_manual.py")
        
        return auth_ok
        
    except Exception as e:
        logger.error(f"Hotfix failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🔧 Railway Hotfix Starting")
    
    if fix_railway_deployment():
        logger.info("✅ Hotfix completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Hotfix failed - manual intervention required")
        sys.exit(1)