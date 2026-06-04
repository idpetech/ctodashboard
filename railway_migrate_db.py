# DEPRECATED: see docs/DEPRECATION-MANIFEST.md — do not use in production paths.
#!/usr/bin/env python3
"""
Railway Database Migration Script
Migrate data from config/secure_credentials.db to proper volume mount location
"""

import os
import sys
import shutil
from pathlib import Path

def migrate_database():
    """Migrate database to proper volume mount location"""
    print("🔄 Railway Database Migration")
    print("=" * 50)
    
    # Source and target paths
    source_db = Path("config/secure_credentials.db")
    target_db = Path("/data/config/secure_credentials.db")
    
    print(f"📁 Source database: {source_db}")
    print(f"📁 Target database: {target_db}")
    print()
    
    # Check source exists
    if not source_db.exists():
        print("❌ Source database not found - nothing to migrate")
        return
        
    print(f"✅ Source database exists ({source_db.stat().st_size} bytes)")
    
    # Create target directory
    target_db.parent.mkdir(parents=True, exist_ok=True)
    print(f"✅ Target directory created: {target_db.parent}")
    
    # Check if target already exists
    if target_db.exists():
        target_size = target_db.stat().st_size
        source_size = source_db.stat().st_size
        print(f"⚠️  Target database already exists ({target_size} bytes)")
        
        if source_size > target_size:
            print("🔄 Source is larger - copying source to target")
            shutil.copy2(source_db, target_db)
            print(f"✅ Database migrated successfully")
        else:
            print("✅ Target database is already up to date")
    else:
        print("🔄 Copying database to target location")
        shutil.copy2(source_db, target_db)
        print(f"✅ Database migrated successfully")
        
    # Verify migration
    if target_db.exists():
        print()
        print("🔍 Migration verification:")
        print(f"  Target size: {target_db.stat().st_size} bytes")
        
        # Test SQLite integrity
        import sqlite3
        try:
            conn = sqlite3.connect(str(target_db))
            cursor = conn.execute("SELECT COUNT(*) FROM secure_users")
            user_count = cursor.fetchone()[0]
            print(f"  User count: {user_count}")
            conn.close()
            print("✅ Database integrity verified")
        except Exception as e:
            print(f"❌ Database integrity check failed: {e}")
            
    else:
        print("❌ Migration failed - target database not found")

if __name__ == "__main__":
    migrate_database()