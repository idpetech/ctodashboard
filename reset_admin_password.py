#!/usr/bin/env python3
"""
Quick utility to reset admin password for testing
"""

import json
import hashlib
import secrets
from pathlib import Path

def hash_password(password: str, salt: str = None) -> tuple:
    """Hash password with salt"""
    if salt is None:
        salt = secrets.token_urlsafe(32)
    
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # iterations
    )
    return password_hash.hex(), salt

def reset_admin_password(new_password: str = "admin123"):
    """Reset admin@ideptech.com password to known value"""
    user_file = Path("config/users/admin@ideptech.com.json")
    
    if not user_file.exists():
        print(f"User file not found: {user_file}")
        return
    
    # Read existing user data
    with open(user_file, 'r') as f:
        user_data = json.load(f)
    
    # Generate new password hash
    password_hash, salt = hash_password(new_password)
    
    # Update password
    user_data["password_hash"] = password_hash
    user_data["salt"] = salt
    
    # Write back to file
    with open(user_file, 'w') as f:
        json.dump(user_data, f, indent=2)
    
    print(f"✅ Password reset for admin@ideptech.com")
    print(f"📧 Email: admin@ideptech.com")
    print(f"🔑 Password: {new_password}")
    print(f"🏢 Workspaces: {user_data.get('workspaces', [])}")

if __name__ == "__main__":
    reset_admin_password("admin123")