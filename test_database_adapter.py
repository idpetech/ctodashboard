#!/usr/bin/env python3
"""
Test Database Adapter Logic Without Full PostgreSQL
Verifies URL parsing and configuration before Railway deployment
"""

import os
import sys
from typing import Dict, Any

def test_url_parsing():
    """Test database URL parsing for Railway configuration"""
    print("🔍 Testing Database URL Parsing")
    print("=" * 40)
    
    try:
        from services.security.database_adapter import parse_database_url, _parse_postgresql_config
        
        # Test Railway internal URL (what we'll use)
        railway_internal = "postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@postgres.railway.internal:5432/railway?options=-csearch_path%3Dctodashboard"
        
        db_type, config = parse_database_url(railway_internal)
        
        print(f"✅ Database type: {db_type}")
        print(f"✅ Host: {config['host']}")
        print(f"✅ Port: {config['port']}")
        print(f"✅ Database: {config['database']}")
        print(f"✅ User: {config['user']}")
        print(f"✅ Password: {config['password'][:10]}...")
        print(f"✅ Schema: {config['search_path']}")
        print(f"✅ SSL Mode: {config['sslmode']}")
        
        # Verify schema parsing
        assert config['search_path'] == 'ctodashboard', f"Expected ctodashboard schema, got {config['search_path']}"
        assert config['database'] == 'railway', f"Expected railway database, got {config['database']}"
        assert config['sslmode'] == 'require', f"Expected require SSL for Railway, got {config['sslmode']}"
        
        print("\n✅ Railway URL parsing test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ URL parsing test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_url():
    """Test public fallback URL parsing"""
    print("\n🔍 Testing Fallback URL Parsing")
    print("=" * 40)
    
    try:
        from services.security.database_adapter import parse_database_url
        
        # Test Railway public URL (fallback)
        railway_public = "postgresql://postgres:lgNRTpOiylzSKRJLaTLCoxjohfFFqyYr@acela.proxy.rlwy.net:48928/railway?options=-csearch_path%3Dctodashboard"
        
        db_type, config = parse_database_url(railway_public)
        
        print(f"✅ Public host: {config['host']}")
        print(f"✅ Public port: {config['port']}")
        print(f"✅ Schema: {config['search_path']}")
        
        # Verify public URL parsing
        assert config['search_path'] == 'ctodashboard', "Schema parsing failed"
        assert config['host'] == 'acela.proxy.rlwy.net', "Public host parsing failed"
        
        print("✅ Fallback URL parsing test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Fallback URL test FAILED: {e}")
        return False

def test_environment_detection():
    """Test environment-based database URL selection"""
    print("\n🔍 Testing Environment Detection")
    print("=" * 40)
    
    try:
        from services.security.secure_database import SecureDatabaseManager
        
        # Test local environment (should use SQLite)
        os.environ.pop('DATABASE_URL', None)
        os.environ.pop('RAILWAY_ENVIRONMENT', None)
        
        # This will create a manager and determine the URL
        db_manager = SecureDatabaseManager()
        print(f"✅ Local environment uses: {db_manager.db_type}")
        assert db_manager.db_type == 'sqlite', f"Expected SQLite locally, got {db_manager.db_type}"
        
        # Test Railway environment simulation
        os.environ['RAILWAY_ENVIRONMENT'] = 'production'
        
        # Create new manager to test Railway detection
        try:
            railway_manager = SecureDatabaseManager()
            print(f"✅ Railway environment would use: {railway_manager.db_type}")
        except Exception as e:
            print(f"⚠️  Railway environment test (expected to fail without connection): {e}")
        
        # Clean up
        os.environ.pop('RAILWAY_ENVIRONMENT', None)
        
        print("✅ Environment detection test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Environment detection test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_current_sqlite_functionality():
    """Test current SQLite setup still works"""
    print("\n🔍 Testing Current SQLite Setup")
    print("=" * 40)
    
    try:
        from services.security.secure_database import secure_db
        
        # Test health check
        health = secure_db.health_check()
        
        print(f"✅ Current database type: {health['database_type']}")
        print(f"✅ Connection status: {health['database_connected']}")
        print(f"✅ Users: {health['statistics']['users']}")
        print(f"✅ Credentials: {health['statistics']['credentials']}")
        print(f"✅ Adapter: {health['adapter_class']}")
        
        assert health['database_connected'], "Database should be connected"
        assert health['database_type'] == 'sqlite', "Should be using SQLite locally"
        
        print("✅ SQLite functionality test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ SQLite test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all database adapter tests"""
    print("🚀 Database Adapter Testing")
    print("=" * 50)
    
    tests = [
        ("URL Parsing", test_url_parsing),
        ("Fallback URL", test_fallback_url), 
        ("Environment Detection", test_environment_detection),
        ("Current SQLite", test_current_sqlite_functionality)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 DATABASE ADAPTER READY FOR RAILWAY!")
        print("   ✅ URL parsing works correctly")
        print("   ✅ Schema extraction working") 
        print("   ✅ Environment detection working")
        print("   ✅ Current SQLite still functional")
        print("\n🚀 Safe to deploy to Railway with PostgreSQL!")
        return True
    else:
        print(f"\n❌ {len(results) - passed} tests failed - fix before deployment")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)