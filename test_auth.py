#!/usr/bin/env python3
"""
Test authentication logic
"""

import sys
import os
sys.path.append(os.getcwd())

from services.auth.user_service import UserService

def test_authentication():
    user_service = UserService()
    
    print("Testing authentication with admin@ideptech.com / admin123")
    result = user_service.authenticate_user("admin@ideptech.com", "admin123")
    
    print(f"Authentication result: {result}")
    
    if result.get("success"):
        print("✅ Authentication successful!")
        print(f"User: {result.get('user', {}).get('display_name', 'Unknown')}")
        print(f"Workspaces: {result.get('user', {}).get('workspaces', [])}")
    else:
        print("❌ Authentication failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        
        # Let's check if user exists
        user_file = user_service.users_dir / "admin@ideptech.com.json"
        if user_file.exists():
            print(f"✓ User file exists at: {user_file}")
            
            import json
            with open(user_file, 'r') as f:
                user_data = json.load(f)
            
            print(f"User status: {user_data.get('status', 'unknown')}")
            print(f"Email: {user_data.get('email', 'unknown')}")
            print(f"Has password_hash: {'password_hash' in user_data}")
            print(f"Has salt: {'salt' in user_data}")
        else:
            print(f"❌ User file does not exist at: {user_file}")

if __name__ == "__main__":
    test_authentication()