#!/bin/bash

# Setup Local PostgreSQL for CTODashboard (No Docker)
# Creates like-for-like testing surface with Railway production

echo "🚀 Setting up Local PostgreSQL for CTODashboard"
echo "==============================================="

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found. Installing..."
    
    # Detect OS and install
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "📦 Installing PostgreSQL via Homebrew..."
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew required. Install from: https://brew.sh/"
            exit 1
        fi
        brew install postgresql@15
        brew services start postgresql@15
        echo "✅ PostgreSQL installed and started"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        echo "📦 Installing PostgreSQL..."
        sudo apt update
        sudo apt install -y postgresql-15 postgresql-contrib-15
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        echo "✅ PostgreSQL installed and started"
    else
        echo "❌ Unsupported OS. Please install PostgreSQL manually."
        exit 1
    fi
else
    echo "✅ PostgreSQL found"
fi

# Setup database and user
echo "🔧 Setting up database..."

# Create database and user (macOS vs Linux differences)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - user is current user
    createdb railway 2>/dev/null || echo "Database 'railway' already exists"
    psql railway << EOF
-- Create ctodashboard schema
CREATE SCHEMA IF NOT EXISTS ctodashboard;
COMMENT ON SCHEMA ctodashboard IS 'CTO Dashboard application data - local development';

-- Show schemas
\dn

-- Show current user
SELECT current_user;
EOF
else
    # Linux - use postgres user
    sudo -u postgres createdb railway 2>/dev/null || echo "Database 'railway' already exists"
    sudo -u postgres psql railway << EOF
-- Create ctodashboard schema
CREATE SCHEMA IF NOT EXISTS ctodashboard;
COMMENT ON SCHEMA ctodashboard IS 'CTO Dashboard application data - local development';

-- Create app user with same name as current user
CREATE USER $(whoami) WITH PASSWORD 'localdevpassword';
GRANT USAGE ON SCHEMA ctodashboard TO $(whoami);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ctodashboard TO $(whoami);
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ctodashboard TO $(whoami);
ALTER DEFAULT PRIVILEGES IN SCHEMA ctodashboard GRANT ALL ON TABLES TO $(whoami);
ALTER DEFAULT PRIVILEGES IN SCHEMA ctodashboard GRANT ALL ON SEQUENCES TO $(whoami);

-- Show schemas
\dn
EOF
fi

# Setup environment
echo "🔧 Setting up environment..."

# Create local environment file
cat > .env.local << EOF
# Local Development Environment - PostgreSQL
# Like-for-like testing surface with Railway production

# Local PostgreSQL connection
DATABASE_URL=postgresql://$(whoami):localdevpassword@localhost:5432/railway?options=-csearch_path%3Dctodashboard

# Development settings
CREDENTIAL_MASTER_KEY=local_dev_key_for_testing_only
ENVIRONMENT=development

# Local environment markers
RAILWAY_ENVIRONMENT=false
RAILWAY_PROJECT_ID=local-dev
EOF

# Copy to main .env file
cp .env.local .env
echo "✅ Environment configured"

# Test connection
echo "🔍 Testing database connection..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    psql railway -c "SELECT current_database(), current_schema(), version();" || {
        echo "❌ Database connection failed"
        exit 1
    }
else
    # Linux
    psql "postgresql://$(whoami):localdevpassword@localhost:5432/railway" -c "SELECT current_database(), current_schema(), version();" || {
        echo "❌ Database connection failed"
        exit 1
    }
fi

echo "✅ Database connection successful"

# Run schema migration if script exists
if [ -f "railway_schema_migration.py" ]; then
    echo "🔄 Setting up database schema..."
    python3 railway_schema_migration.py
fi

echo ""
echo "🎉 LOCAL POSTGRESQL SETUP COMPLETE!"
echo "   📊 PostgreSQL running natively on localhost:5432"
echo "   📁 Database: railway"
echo "   📁 Schema: ctodashboard"
echo "   🔗 DATABASE_URL configured for like-for-like testing"
echo ""
echo "💡 Connection details:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "   psql railway"
else
    echo "   psql postgresql://$(whoami):localdevpassword@localhost:5432/railway"
fi
echo "   \\c railway"
echo "   SET search_path TO ctodashboard;"
echo "   \\dt"