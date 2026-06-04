#!/bin/bash

# Local Development Setup with PostgreSQL
# Ensures like-for-like testing surface with Railway production

echo "🚀 Setting up local PostgreSQL for CTODashboard"
echo "================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start PostgreSQL
echo "🔄 Starting PostgreSQL container..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to start..."
timeout 30s bash -c 'until docker-compose exec postgres pg_isready -U postgres > /dev/null 2>&1; do sleep 1; done'

if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL is ready!"
else
    echo "❌ PostgreSQL failed to start within 30 seconds"
    exit 1
fi

# Load environment variables
echo "🔧 Setting up environment..."
cp .env.local .env

# Apply canonical schema
echo "🔄 Setting up database schema..."
ENABLE_DB_AUTO_INIT=true python3 scripts/init_postgres_schema.py

# Verify setup
echo "🔍 Verifying setup..."
python3 -c "
from services.security.secure_database import secure_db
health = secure_db.health_check()
if health['database_type'] == 'postgresql':
    print('✅ Local PostgreSQL setup successful!')
    print(f'   Database type: {health[\"database_type\"]}')
    print(f'   Schema version: {health[\"schema_version\"]}')
else:
    print('❌ Setup verification failed')
    exit(1)
"

echo ""
echo "🎉 LOCAL DEVELOPMENT SETUP COMPLETE!"
echo "   📊 PostgreSQL running on localhost:5432"
echo "   📁 ctodashboard schema created"
echo "   🔗 DATABASE_URL configured for local development"
echo ""
echo "💡 Quick commands:"
echo "   Start:  docker-compose up -d"
echo "   Stop:   docker-compose down"  
echo "   Logs:   docker-compose logs postgres"
echo "   Shell:  docker-compose exec postgres psql -U postgres -d railway"