#!/bin/bash
# Test before deploying to Railway
# This script runs all validations and local tests

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           TEST BEFORE DEPLOY TO RAILWAY                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Run validation pipeline
echo "🔍 Running validation pipeline..."
./pre_deploy_check.sh
echo ""

# 2. Check if local server is running
echo "🌐 Checking local server..."
if curl -s http://localhost:3001/health > /dev/null 2>&1; then
    echo "  ✅ Local server is running"
    
    # Test key endpoints
    echo ""
    echo "🧪 Testing local endpoints..."
    
    # Health check
    if curl -s http://localhost:3001/health | grep -q "read_only"; then
        echo "  ✅ /health endpoint working"
    else
        echo "  ❌ /health endpoint failed"
        exit 1
    fi
    
    # Assignments
    if curl -s http://localhost:3001/api/assignments | grep -q "ideptech"; then
        echo "  ✅ /api/assignments endpoint working"
    else
        echo "  ❌ /api/assignments endpoint failed"
        exit 1
    fi
    
    # Feature flags
    if curl -s http://localhost:3001/api/feature-flags | grep -q "service_config_ui"; then
        echo "  ✅ /api/feature-flags endpoint working"
    else
        echo "  ❌ /api/feature-flags endpoint failed"
        exit 1
    fi
    
else
    echo "  ⚠️  Local server not running"
    echo "     Start it with: python3 integrated_dashboard.py"
    echo "     Or skip local tests with: ./scripts/test_before_deploy.sh --skip-local"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ ALL TESTS PASSED - READY TO DEPLOY                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Commit your changes: git add . && git commit -m 'Your message'"
echo "  2. Push to deploy: git push origin master"
echo "  3. Or deploy directly: railway up"
echo ""
