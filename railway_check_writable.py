#!/usr/bin/env python3
"""
Check which directories are writable on Railway
"""

import os
from pathlib import Path

def check_writable_locations():
    """Check various locations for write access"""
    print("🔍 Railway Writable Directory Check")
    print("=" * 50)
    
    locations_to_check = [
        "/",
        "/app",
        "/data", 
        "/tmp",
        "/var/tmp",
        "/home",
        "/opt",
        ".",
        "./config",
        os.getcwd(),
        f"{os.getcwd()}/config"
    ]
    
    writable_locations = []
    
    for location in locations_to_check:
        try:
            path = Path(location)
            if path.exists():
                writable = os.access(path, os.W_OK)
                print(f"📁 {location}:")
                print(f"   Exists: ✅")
                print(f"   Writable: {'✅' if writable else '❌'}")
                if writable:
                    writable_locations.append(location)
            else:
                print(f"📁 {location}:")
                print(f"   Exists: ❌")
            print()
        except Exception as e:
            print(f"📁 {location}: Error - {e}")
            print()
    
    print(f"✅ Writable locations found: {writable_locations}")
    
    # Test creating files in writable locations
    print("\n🧪 Testing file creation:")
    for location in writable_locations[:3]:  # Test top 3 writable locations
        try:
            test_file = Path(location) / "test_write.tmp"
            test_file.write_text("test")
            print(f"✅ Can create files in: {location}")
            test_file.unlink()  # Clean up
        except Exception as e:
            print(f"❌ Cannot create files in {location}: {e}")

if __name__ == "__main__":
    check_writable_locations()