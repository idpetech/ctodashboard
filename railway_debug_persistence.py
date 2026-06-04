# DEPRECATED: see docs/DEPRECATION-MANIFEST.md — do not use in production paths.
#!/usr/bin/env python3
"""
Railway Database Persistence Debug Script
Find out WHY the database is being overwritten on deployments
"""

import os
import sys
from pathlib import Path
import stat
import time

def debug_railway_paths():
    """Debug Railway environment and file paths"""
    print("🔍 Railway Environment Debug")
    print("=" * 60)
    
    # Environment variables
    print("📋 Environment Variables:")
    print(f"  RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'NOT SET')}")
    print(f"  RAILWAY_VOLUME_MOUNT_PATH: {os.getenv('RAILWAY_VOLUME_MOUNT_PATH', 'NOT SET')}")
    print(f"  DB_PATH: {os.getenv('DB_PATH', 'NOT SET')}")
    print(f"  PWD: {os.getenv('PWD', 'NOT SET')}")
    print(f"  HOME: {os.getenv('HOME', 'NOT SET')}")
    print()
    
    # Check current working directory
    cwd = Path.cwd()
    print(f"📁 Current Working Directory: {cwd}")
    print(f"  Exists: {cwd.exists()}")
    print(f"  Writable: {os.access(cwd, os.W_OK)}")
    print()
    
    # Check volume mount path
    volume_path = Path(os.getenv('RAILWAY_VOLUME_MOUNT_PATH', '/data'))
    print(f"🗄️ Volume Mount Path: {volume_path}")
    print(f"  Exists: {volume_path.exists()}")
    if volume_path.exists():
        print(f"  Writable: {os.access(volume_path, os.W_OK)}")
        try:
            stat_info = volume_path.stat()
            print(f"  Mode: {stat.filemode(stat_info.st_mode)}")
            print(f"  Owner: {stat_info.st_uid}")
            print(f"  Group: {stat_info.st_gid}")
        except Exception as e:
            print(f"  Stat error: {e}")
    print()
    
    # Check config directories
    config_paths = [
        Path("config"),
        Path("/app/config"),
        volume_path / "config"
    ]
    
    print("📂 Config Directory Candidates:")
    for config_path in config_paths:
        print(f"  {config_path}:")
        print(f"    Exists: {config_path.exists()}")
        if config_path.exists():
            print(f"    Writable: {os.access(config_path, os.W_OK)}")
            try:
                files = list(config_path.iterdir())
                print(f"    Files: {[f.name for f in files[:5]]}")  # First 5 files
                if len(files) > 5:
                    print(f"    ... and {len(files) - 5} more")
            except Exception as e:
                print(f"    List error: {e}")
        print()
    
    # Check potential database paths
    db_paths = [
        Path("config/secure_credentials.db"),
        Path("/app/config/secure_credentials.db"),
        volume_path / "config/secure_credentials.db",
        Path("secure_credentials.db")
    ]
    
    print("🗃️ Database File Candidates:")
    for db_path in db_paths:
        print(f"  {db_path}:")
        print(f"    Exists: {db_path.exists()}")
        if db_path.exists():
            try:
                stat_info = db_path.stat()
                print(f"    Size: {stat_info.st_size} bytes")
                print(f"    Modified: {time.ctime(stat_info.st_mtime)}")
                print(f"    Mode: {stat.filemode(stat_info.st_mode)}")
            except Exception as e:
                print(f"    Stat error: {e}")
        print()

def debug_database_creation():
    """Debug what happens when database is created"""
    print("🔧 Database Creation Debug")
    print("=" * 60)
    
    try:
        # Add project root to path
        sys.path.insert(0, str(Path(__file__).parent))
        from services.security.secure_database import get_secure_db
        
        # Get the database instance
        db = get_secure_db()
        print(f"📍 Database instance created")
        print(f"  Database path: {db.db_path}")
        print(f"  Path exists: {db.db_path.exists()}")
        print(f"  Parent exists: {db.db_path.parent.exists()}")
        print(f"  Parent writable: {os.access(db.db_path.parent, os.W_OK)}")
        
        if db.db_path.exists():
            stat_info = db.db_path.stat()
            print(f"  Size: {stat_info.st_size} bytes")
            print(f"  Modified: {time.ctime(stat_info.st_mtime)}")
        
        # Check health
        health = db.health_check()
        print(f"📊 Database Health:")
        print(f"  Connected: {health.get('database_connected')}")
        print(f"  Users: {health.get('statistics', {}).get('users', 0)}")
        
    except Exception as e:
        print(f"❌ Database creation error: {e}")
        import traceback
        traceback.print_exc()

def test_file_persistence():
    """Test if files persist in volume mount"""
    print("💾 File Persistence Test")
    print("=" * 60)
    
    volume_path = Path(os.getenv('RAILWAY_VOLUME_MOUNT_PATH', '/data'))
    config_path = volume_path / "config"
    test_file = config_path / "persistence_test.txt"
    
    try:
        # Create config directory if needed
        config_path.mkdir(parents=True, exist_ok=True)
        
        # Write test file
        test_data = f"Test written at: {time.ctime()}"
        test_file.write_text(test_data)
        print(f"✅ Test file written: {test_file}")
        
        # Read it back
        read_data = test_file.read_text()
        print(f"✅ Test file read: {read_data}")
        
        # Check permissions
        stat_info = test_file.stat()
        print(f"📋 File info:")
        print(f"  Size: {stat_info.st_size} bytes")
        print(f"  Mode: {stat.filemode(stat_info.st_mode)}")
        print(f"  Modified: {time.ctime(stat_info.st_mtime)}")
        
        return True
        
    except Exception as e:
        print(f"❌ File persistence test failed: {e}")
        return False

if __name__ == "__main__":
    debug_railway_paths()
    print()
    debug_database_creation()
    print()
    test_file_persistence()