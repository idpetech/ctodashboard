#!/bin/bash

# Railway Post-Deploy Hook
# Runs after successful Railway deployment to set up PostgreSQL schema

echo "🚀 Railway Post-Deploy: Setting up PostgreSQL schema"
echo "===================================================="

# Ensure we're in Railway environment
if [[ -z "$RAILWAY_ENVIRONMENT" ]]; then
    echo "⚠️  Not running in Railway - skipping schema setup"
    exit 0
fi

echo "✅ Running in Railway environment: $RAILWAY_ENVIRONMENT"

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Verify DATABASE_URL is set (should be set in Railway project variables)
if [[ -z "$DATABASE_URL" ]]; then
    echo "❌ DATABASE_URL not set - please configure in Railway dashboard"
    exit 1
fi

echo "✅ DATABASE_URL configured for cross-project connection"

# Run schema migration
echo "🔄 Creating PostgreSQL schema..."
python railway_deploy_migration.py

if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL schema setup complete!"
else
    echo "❌ PostgreSQL schema setup failed!"
    exit 1
fi