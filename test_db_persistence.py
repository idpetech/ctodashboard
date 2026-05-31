#!/usr/bin/env python3
"""
Test Railway Database Persistence
Check if database file persists across deployments
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def test_database_persistence():
    """Test if database and volume persist"""
    
    # Check environment
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
    config_dir = Path("/app/config") if is_railway else Path("config")
    test_file = config_dir / "persistence_test.json"
    db_file = config_dir / "secure_credentials.db"
    
    print(f"🌍 Environment: {'Railway' if is_railway else 'Local'}")
    print(f"📁 Config directory: {config_dir}")
    print(f"📄 Test file: {test_file}")
    print(f"🗄️  Database file: {db_file}")
    
    # Ensure config directory exists
    config_dir.mkdir(exist_ok=True, parents=True)
    
    # Check if test file exists (proves persistence)
    if test_file.exists():
        try:
            with open(test_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Persistence test file found!")
            print(f"   Created: {data.get('created_at')}")
            print(f"   Deploy count: {data.get('deploy_count', 0)}")
            
            # Increment deploy count
            data['deploy_count'] = data.get('deploy_count', 0) + 1
            data['last_seen'] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"❌ Error reading test file: {e}")
            data = {
                "created_at": datetime.now().isoformat(),
                "deploy_count": 1,
                "last_seen": datetime.now().isoformat()
            }
    else:
        print(f"📝 Creating new persistence test file...")
        data = {
            "created_at": datetime.now().isoformat(),
            "deploy_count": 1,
            "last_seen": datetime.now().isoformat()
        }
    
    # Write test file
    try:
        with open(test_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ Test file updated: deploy #{data['deploy_count']}")
    except Exception as e:
        print(f"❌ Error writing test file: {e}")
        return False
    
    # Check database file
    if db_file.exists():
        size = db_file.stat().st_size
        print(f"✅ Database file exists: {size} bytes")
        
        # Try to check user count
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from services.security.secure_database import secure_db
            health = secure_db.health_check()
            user_count = health.get('statistics', {}).get('users', 0)
            print(f"👥 Database has {user_count} users")
            
            if user_count == 0:
                print("⚠️  WARNING: Database exists but has no users!")
                print("   This suggests the database file was recreated")
                return False
                
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            return False
    else:
        print(f"❌ Database file does not exist")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 Testing Railway Database Persistence...")
    success = test_database_persistence()
    
    if success:
        print("✅ Database persistence test PASSED")
        sys.exit(0)
    else:
        print("❌ Database persistence test FAILED")
        sys.exit(1)