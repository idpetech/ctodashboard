#!/usr/bin/env python3
"""
Railway Database Inspection Script
Quick utility to inspect what users exist in the Railway database
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def inspect_database():
    """Inspect Railway database to see what users were created"""
    try:
        # Check Railway environment and paths
        print("🌐 Railway Environment Info")
        print("=" * 50)
        print(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}")
        print(f"RAILWAY_VOLUME_MOUNT_PATH: {os.getenv('RAILWAY_VOLUME_MOUNT_PATH', 'Not set')}")
        print(f"DB_PATH: {os.getenv('DB_PATH', 'Not set')}")
        
        # Check directory permissions
        volume_path = os.getenv('RAILWAY_VOLUME_MOUNT_PATH', '/data')
        config_path = f"{volume_path}/config" 
        print(f"Volume mount path: {volume_path}")
        print(f"Config path: {config_path}")
        print(f"Volume path exists: {os.path.exists(volume_path)}")
        print(f"Config path exists: {os.path.exists(config_path)}")
        
        # Check permissions
        if os.path.exists(volume_path):
            print(f"Volume path writable: {os.access(volume_path, os.W_OK)}")
        if os.path.exists(config_path):
            print(f"Config path writable: {os.access(config_path, os.W_OK)}")
        
        # Try to create config directory if it doesn't exist
        if not os.path.exists(config_path):
            try:
                os.makedirs(config_path, exist_ok=True)
                print(f"✅ Created config directory: {config_path}")
            except Exception as e:
                print(f"❌ Failed to create config directory: {e}")
        
        print()
        
        from services.security.secure_database import secure_db
        
        print("🔍 Railway Database Inspection")
        print("=" * 50)
        
        # Check database health
        health = secure_db.health_check()
        print(f"Database Connected: {health.get('database_connected')}")
        print(f"User Count: {health.get('statistics', {}).get('users', 0)}")
        print(f"Encryption Available: {health.get('encryption_available')}")
        print(f"Master Key Configured: {health.get('master_key_configured')}")
        print()
        
        # Get all user emails (safe info)
        try:
            users = secure_db.list_all_users()
            print("👥 Users Found:")
            if users:
                for i, user in enumerate(users, 1):
                    print(f"  {i}. Email: {user.get('email', 'Unknown')}")
                    print(f"     Display Name: {user.get('display_name', 'None')}")
                    print(f"     Role: {user.get('role', 'None')}")
                    print(f"     Status: {user.get('status', 'None')}")
                    print(f"     Workspaces: {user.get('workspaces', [])}")
                    print(f"     Has Password Hash: {'Yes' if user.get('password_hash') else 'No'}")
                    print(f"     Password Hash (first 20 chars): {user.get('password_hash', '')[:20]}...")
                    print(f"     Salt: {user.get('salt', '')}")
                    print()
            else:
                print("  No users found")
        except Exception as e:
            print(f"  Error listing users: {e}")
        
        # Show database file info
        db_path = secure_db.db_path
        print(f"📁 Database File Info:")
        print(f"  Path: {db_path}")
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"  Size: {size:,} bytes ({size / 1024:.1f} KB)")
            print(f"  Exists: Yes")
        else:
            print(f"  Exists: No")
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
        import traceback
        traceback.print_exc()

def reset_known_admin():
    """Reset admin to known credentials"""
    try:
        from services.security.secure_database import secure_db
        import hashlib
        import secrets
        
        print("🔄 Resetting admin credentials to known values")
        
        # Generate proper password hash for "admin123"
        password = "admin123"
        salt = secrets.token_urlsafe(32)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        ).hex()
        
        admin_data = {
            "email": "admin@idpetech.com",
            "display_name": "IDEEP Tech Admin",
            "password_hash": password_hash,
            "salt": salt,
            "workspaces": ["admin_workspace", "default_workspace"],
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
            "user_agent": "railway_reset_script"
        }
        
        if secure_db.store_user_credentials("admin@idpetech.com", admin_data, audit_info):
            print("✅ Admin credentials reset successfully!")
            print("📧 Email: admin@idpetech.com")
            print("🔑 Password: admin123")
        else:
            print("❌ Failed to reset admin credentials")
            
    except Exception as e:
        print(f"❌ Error resetting admin: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_known_admin()
    else:
        inspect_database()
        print("\n💡 To reset admin to known credentials, run:")
        print("   python railway_db_inspect.py reset")