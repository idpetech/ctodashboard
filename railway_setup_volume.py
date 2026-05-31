#!/usr/bin/env python3
"""
Railway Volume Setup Script
Ensures the Railway volume is properly configured for database persistence
"""

import os
import sys
from pathlib import Path

def setup_railway_volume():
    """Setup Railway volume for database persistence"""
    print("🚂 Railway Volume Setup")
    print("=" * 50)
    
    # Check Railway environment
    railway_env = os.getenv("RAILWAY_ENVIRONMENT")
    volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    
    print(f"Railway Environment: {railway_env or 'Not set'}")
    print(f"Volume Mount Path: {volume_mount or 'Not set'}")
    
    if not railway_env:
        print("❌ Not running on Railway - exiting")
        return False
    
    if not volume_mount:
        print("❌ RAILWAY_VOLUME_MOUNT_PATH not set")
        print("💡 Make sure you have a volume configured in railway.json")
        return False
    
    # Create directory structure
    try:
        config_dir = Path(volume_mount) / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Set permissions
        os.chmod(config_dir, 0o755)
        
        print(f"✅ Created config directory: {config_dir}")
        print(f"✅ Set permissions to 755")
        
        # Test write access
        test_file = config_dir / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        
        print("✅ Write access confirmed")
        
        # Show final paths
        db_path = config_dir / "secure_credentials.db"
        print(f"📁 Database path will be: {db_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup volume: {e}")
        return False

def check_volume_status():
    """Check current volume status"""
    print("📊 Volume Status Check")
    print("=" * 30)
    
    volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
    config_path = Path(volume_mount) / "config"
    db_path = config_path / "secure_credentials.db"
    
    print(f"Volume mount: {volume_mount}")
    print(f"Exists: {Path(volume_mount).exists()}")
    print(f"Writable: {os.access(volume_mount, os.W_OK) if Path(volume_mount).exists() else False}")
    print()
    print(f"Config directory: {config_path}")
    print(f"Exists: {config_path.exists()}")
    print(f"Writable: {os.access(config_path, os.W_OK) if config_path.exists() else False}")
    print()
    print(f"Database file: {db_path}")
    print(f"Exists: {db_path.exists()}")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"Size: {size:,} bytes ({size / 1024:.1f} KB)")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_volume_status()
    else:
        success = setup_railway_volume()
        if success:
            print("\n✅ Railway volume setup complete!")
            print("You can now run database operations.")
        else:
            print("\n❌ Railway volume setup failed!")
            sys.exit(1)