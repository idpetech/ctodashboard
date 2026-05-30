#!/bin/bash
# Railway Environment Setup for Secure CTO Dashboard
echo "🚄 Setting up Railway environment variables..."

# Core security keys (REQUIRED)
railway variables set CREDENTIAL_MASTER_KEY="632fced69c15a0eb6b7e2dd0385055ee505857fcf8a8fcfb29b63d52c5648cda5a18ea36c0a2539a03874f9bee967567677c4610101e72279ac45ef5925fa8d2"
railway variables set JWT_SECRET="4b4be937a7c75349b75bfba649cb1b01cfd3123e26d6809c6291960cc9222bff"

# Database configuration (IMPORTANT for SQLite)
railway variables set DATABASE_URL="sqlite:///config/secure_credentials.db"
railway variables set SQLITE_DATABASE_PATH="/app/config/secure_credentials.db"

# Application settings
railway variables set FLASK_ENV="production"
railway variables set FLASK_DEBUG="false"

# Ensure config directory exists and is writable
railway variables set CONFIG_DIR="/app/config"

echo "✅ Railway environment variables set!"
echo "🔒 Database will be created at: /app/config/secure_credentials.db"
echo "⚡ Next: Deploy and verify database creation"