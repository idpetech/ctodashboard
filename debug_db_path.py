#!/usr/bin/env python3
"""
Debug exactly which database path is being used
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("🔍 DATABASE PATH DEBUG")
print("=" * 50)

# Check environment variables
print("📋 Environment Variables:")
print(f"  RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'NOT SET')}")
print(f"  RAILWAY_VOLUME_MOUNT_PATH: {os.getenv('RAILWAY_VOLUME_MOUNT_PATH', 'NOT SET')}")
print(f"  DB_PATH: {os.getenv('DB_PATH', 'NOT SET')}")
print()

# Import and check database path
try:
    from services.security.secure_database import get_secure_db
    
    db = get_secure_db()
    print(f"📁 Database Configuration:")
    print(f"  Database path: {db.db_path}")
    print(f"  Database path exists: {db.db_path.exists()}")
    print(f"  Database parent exists: {db.db_path.parent.exists()}")
    print()
    
    # Check all possible paths
    paths_to_check = [
        Path("/data/config/secure_credentials.db"),
        Path("/app/config/secure_credentials.db"), 
        Path("config/secure_credentials.db"),
        Path("secure_credentials.db")
    ]
    
    print("🗃️ Checking all possible database locations:")
    for path in paths_to_check:
        print(f"  {path}:")
        print(f"    Exists: {path.exists()}")
        if path.exists():
            try:
                size = path.stat().st_size
                print(f"    Size: {size} bytes")
                
                # Try to read as SQLite
                import sqlite3
                try:
                    conn = sqlite3.connect(str(path))
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    print(f"    Tables: {[table[0] for table in tables]}")
                    
                    if 'secure_users' in [table[0] for table in tables]:
                        cursor = conn.execute("SELECT COUNT(*) FROM secure_users")
                        count = cursor.fetchone()[0]
                        print(f"    User count: {count}")
                    
                    conn.close()
                except Exception as e:
                    print(f"    SQLite error: {e}")
                    
            except Exception as e:
                print(f"    Stat error: {e}")
        print()
        
except Exception as e:
    print(f"❌ Error importing database: {e}")
    import traceback
    traceback.print_exc()