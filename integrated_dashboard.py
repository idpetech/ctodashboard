#!/usr/bin/env python3
"""
Integrated CTO Dashboard - Clean WSGI Boot File
All service logic is now in services/* modules and imported via routes/api_routes.py
Database persistence test deployment
"""

import os
import secrets

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# Load environment variables. .env holds shared keys; .env.local holds local-only
# values (e.g. DATABASE_URL) and is layered on top so local runs need no external
# `export` step. Skipped on Railway, where platform-provided env vars are authoritative.
load_dotenv()
if not os.getenv("RAILWAY_ENVIRONMENT"):
    load_dotenv(".env.local", override=True)

# Setup centralized logging before anything else
from config.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# Feature Flags - must match those in services/service_manager.py
FEATURE_FLAGS = {
    "multi_tenancy": os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true",
    "workstream_management": os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true",
    "service_config_ui": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true",
    "advanced_billing": os.getenv("ENABLE_BILLING", "false").lower() == "true",
    "database_storage": os.getenv("ENABLE_DATABASE", "false").lower() == "true",
    "portfolio_dashboard": os.getenv("ENABLE_PORTFOLIO_DASHBOARD", "false").lower() == "true",
    "csv_import": os.getenv("ENABLE_CSV_IMPORT", "false").lower() == "true",
    "attention_engine": os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() == "true",
    "ctolens_scheduled_enrichment": os.getenv(
        "ENABLE_CTOLENS_SCHEDULED_ENRICHMENT", "false"
    ).lower()
    == "true",
    "product_analytics": os.getenv("ENABLE_PRODUCT_ANALYTICS", "false").lower() == "true",
    "railway_connector": os.getenv("ENABLE_RAILWAY_CONNECTOR", "false").lower() == "true",
    "vercel_connector": os.getenv("ENABLE_VERCEL_CONNECTOR", "false").lower() == "true",
    "azure_connector": os.getenv("ENABLE_AZURE_CONNECTOR", "false").lower() == "true",
}

# Configure Flask paths
app = Flask(__name__, template_folder="templates")


def _is_railway_production() -> bool:
    return os.getenv("RAILWAY_ENVIRONMENT", "").lower() in ("true", "1", "production")


# Reload templates on every request in local dev (RAILWAY_ENVIRONMENT=false must not disable this)
app.config["TEMPLATES_AUTO_RELOAD"] = not _is_railway_production()

# Log application startup
logger.info(
    "CTOLens application starting up",
    extra={
        "operation": "startup",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "feature_flags": FEATURE_FLAGS,
    },
)

# Configure sessions for web authentication
app.secret_key = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

# Development-friendly session configuration
# This allows sessions to work across localhost/127.0.0.1/IP addresses
app.config["SESSION_COOKIE_DOMAIN"] = None  # Don't restrict to specific domain
app.config["SESSION_COOKIE_PATH"] = "/"  # Available across entire site
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Allow reasonable cross-origin usage
app.config["SESSION_COOKIE_SECURE"] = False  # Allow HTTP for development
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access (security)

# For production, you would set:
# app.config['SESSION_COOKIE_DOMAIN'] = '.yourdomain.com'  # Allow subdomains
# app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only

# Enable CORS with credentials support
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:8520", "http://localhost:8520"])

# Import and register routes
from routes.api_routes import register_routes
from routes.database_admin import register_database_admin_routes
from routes.homepage_routes import homepage_bp
from routes.mcp_routes import mcp_bp

# Register homepage routes first to claim root route
app.register_blueprint(homepage_bp)

# Register MCP routes for external secure access
app.register_blueprint(mcp_bp)

register_routes(app)
register_database_admin_routes(app)


# Debug routes — local only (disabled on Railway/production deploys)
if not os.getenv("RAILWAY_ENVIRONMENT"):

    @app.route("/debug/auth")
    def debug_auth():
        """Debug endpoint to check authentication status - v2"""
        try:
            from services.security.secure_database import secure_db

            health = secure_db.health_check()

            logger.info(
                "Debug auth endpoint accessed",
                extra={
                    "operation": "debug_auth",
                    "database_connected": health.get("database_connected", False),
                    "user_count": health.get("statistics", {}).get("users", 0),
                },
            )

            return {
                "database_connected": health.get("database_connected", False),
                "user_count": health.get("statistics", {}).get("users", 0),
                "encryption_available": health.get("encryption_available", False),
                "master_key_configured": health.get("master_key_configured", False),
                "environment": os.getenv("RAILWAY_ENVIRONMENT", "local"),
                "debug": True,
            }
        except Exception as e:
            logger.error(
                "Debug auth endpoint failed",
                extra={"operation": "debug_auth", "error": str(e)},
                exc_info=e,
            )
            return {
                "error": str(e),
                "database_connected": False,
                "environment": os.getenv("RAILWAY_ENVIRONMENT", "local"),
                "debug": True,
            }, 500

    @app.route("/debug/force-init")
    def force_init():
        """Force database initialization - emergency endpoint"""
        try:
            from services.security.secure_database import secure_db

            # Force auto-initialization
            secure_db._auto_initialize_if_empty()

            # Check result
            health = secure_db.health_check()

            return {
                "forced_initialization": True,
                "user_count": health.get("statistics", {}).get("users", 0),
                "database_connected": health.get("database_connected", False),
                "message": "Force initialization completed",
                "environment": os.getenv("RAILWAY_ENVIRONMENT", "local"),
            }
        except Exception as e:
            return {
                "forced_initialization": False,
                "error": str(e),
                "message": "Force initialization failed",
            }, 500

    @app.route("/debug/db-location")
    def debug_db_location():
        """Show exactly where database is being written"""
        try:
            from services.security.secure_database import secure_db

            db_path = secure_db.db_path
            abs_db_path = os.path.abspath(db_path)

            # Check if file exists and get info
            if os.path.exists(db_path):
                stat = os.stat(db_path)
                file_size = stat.st_size
                file_exists = True
            else:
                file_size = 0
                file_exists = False

            return {
                "database_path": str(db_path),
                "absolute_path": str(abs_db_path),
                "file_exists": file_exists,
                "file_size_bytes": file_size,
                "working_directory": os.getcwd(),
                "railway_environment": os.getenv("RAILWAY_ENVIRONMENT", "local"),
                "volume_mount": os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data"),
                "expected_railway_path": "/data/config/secure_credentials.db",
            }
        except Exception as e:
            return {
                "error": str(e),
                "working_directory": os.getcwd(),
                "railway_environment": os.getenv("RAILWAY_ENVIRONMENT", "local"),
            }, 500

    @app.route("/debug/test-write")
    def test_database_write():
        """Test writing a record to verify database location"""
        try:
            import sqlite3
            import time

            # Determine database path based on environment
            railway_env = os.getenv("RAILWAY_ENVIRONMENT")
            if railway_env:
                # On Railway, use volume mount
                db_path = "/data/config/secure_credentials.db"
                config_dir = "/data/config"
            else:
                # Local development
                db_path = "config/secure_credentials.db"
                config_dir = "config"

            # Ensure directory exists
            os.makedirs(config_dir, exist_ok=True)

            # Get file size before
            if os.path.exists(db_path):
                size_before = os.stat(db_path).st_size
            else:
                size_before = 0

            # Simple SQLite test - just connect and count tables
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                table_count = len(tables)
                conn.close()
                connection_success = True
            except Exception as sqlite_error:
                table_count = 0
                connection_success = False
                sqlite_error_msg = str(sqlite_error)
            else:
                sqlite_error_msg = None

            # Get file size after
            if os.path.exists(db_path):
                size_after = os.stat(db_path).st_size
            else:
                size_after = 0

            return {
                "database_path": db_path,
                "absolute_path": os.path.abspath(db_path),
                "size_before": size_before,
                "size_after": size_after,
                "size_changed": size_after != size_before,
                "table_count": table_count,
                "file_exists": os.path.exists(db_path),
                "connection_success": connection_success,
                "sqlite_error": sqlite_error_msg,
                "working_directory": os.getcwd(),
                "config_dir_exists": os.path.exists(config_dir),
                "timestamp": int(time.time()),
                "railway_environment": railway_env or "local",
            }
        except Exception as e:
            import traceback

            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "working_directory": os.getcwd(),
                "railway_environment": os.getenv("RAILWAY_ENVIRONMENT", "local"),
            }, 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8520))  # Use allocated CTO Dashboard port

    # Enable debug mode only in production (Railway); "false" in .env.local is not production
    debug_mode = not _is_railway_production()

    logger.info(
        "Starting Flask application server",
        extra={
            "operation": "server_start",
            "port": port,
            "debug_mode": debug_mode,
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        },
    )

    app.run(host="0.0.0.0", port=port, debug=debug_mode)
