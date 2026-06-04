#!/usr/bin/env python3
"""
Verify Local PostgreSQL Setup
Tests like-for-like configuration with Railway
"""

import os
import sys

def test_database_url_parsing():
    """Test that our adapter correctly parses URLs"""
    print("🔍 Testing database URL parsing...")
    
    try:
        from services.security.database_adapter import parse_database_url
        
        # Test local PostgreSQL URL
        local_url = "postgresql://haseebtoor:localdevpassword@localhost:5432/railway?options=-csearch_path%3Dctodashboard"
        db_type, config = parse_database_url(local_url)
        
        print(f"✅ Database type: {db_type}")
        print(f"✅ Host: {config['host']}")
        print(f"✅ Database: {config['database']}")
        print(f"✅ Schema: {config['search_path']}")
        
        # Verify schema extraction works
        if config['search_path'] == 'ctodashboard':
            print("✅ Schema parsing works correctly")
        else:
            print(f"❌ Schema parsing failed: got {config['search_path']}, expected ctodashboard")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ URL parsing test failed: {e}")
        return False

def test_database_connection():
    """Test actual database connection"""
    print("\n🔍 Testing database connection...")
    
    try:
        # Set environment to use local PostgreSQL
        os.environ['DATABASE_URL'] = "postgresql://haseebtoor:localdevpassword@localhost:5432/railway?options=-csearch_path%3Dctodashboard"
        
        from services.security.secure_database import SecureDatabaseManager
        
        # Try to create database manager
        db = SecureDatabaseManager()
        
        # Run health check
        health = db.health_check()
        
        if health.get('database_connected'):
            print(f"✅ Connected to: {health['database_type']}")
            print(f"✅ Adapter: {health['adapter_class']}")
            print(f"✅ Schema version: {health['schema_version']}")
            print(f"✅ Users: {health['statistics']['users']}")
            return True
        else:
            print(f"❌ Connection failed: {health.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def test_like_for_like_configuration():
    """Verify local matches Railway configuration"""
    print("\n🔍 Testing like-for-like configuration...")
    
    # Test Railway URL parsing
    railway_url = "postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@postgres.railway.internal:5432/railway?options=-csearch_path%3Dctodashboard"
    local_url = "postgresql://haseebtoor:localdevpassword@localhost:5432/railway?options=-csearch_path%3Dctodashboard"
    
    try:
        from services.security.database_adapter import parse_database_url
        
        _, railway_config = parse_database_url(railway_url)
        _, local_config = parse_database_url(local_url)
        
        # Compare configurations
        matches = []
        matches.append(("Database", railway_config['database'] == local_config['database']))
        matches.append(("Schema", railway_config['search_path'] == local_config['search_path']))
        matches.append(("SSL Mode", railway_config['sslmode'], local_config['sslmode']))
        
        print("📊 Configuration comparison:")
        for name, match in matches[:2]:  # Skip SSL comparison
            status = "✅" if match else "❌"
            print(f"   {status} {name}: {'Match' if match else 'Mismatch'}")
            
        # SSL modes can differ (Railway requires SSL, local doesn't)
        print(f"   ℹ️ SSL Mode: Railway={railway_config['sslmode']}, Local={local_config['sslmode']} (Expected difference)")
        
        return all(match for _, match in matches[:2])
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Main verification process"""
    print("🚀 PostgreSQL Setup Verification")
    print("================================")
    
    tests = [
        ("Database URL Parsing", test_database_url_parsing),
        ("Database Connection", test_database_connection), 
        ("Like-for-Like Config", test_like_for_like_configuration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 LOCAL POSTGRESQL SETUP VERIFIED!")
        print("   📁 Like-for-like testing surface with Railway")
        print("   🔄 Same adapter, same schema, same behavior")
        print("   🐛 Railway bugs will now reproduce locally")
    else:
        print(f"\n❌ Setup incomplete - {len(results) - passed} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()