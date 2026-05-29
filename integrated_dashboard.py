#!/usr/bin/env python3
"""
Integrated CTO Dashboard - Clean WSGI Boot File
All service logic is now in services/* modules and imported via routes/api_routes.py
"""

import os
import secrets
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Feature Flags - must match those in services/service_manager.py
FEATURE_FLAGS = {
    "multi_tenancy": os.getenv("ENABLE_MULTI_TENANCY", "false").lower() == "true",
    "workstream_management": os.getenv("ENABLE_WORKSTREAM_MGMT", "false").lower() == "true",
    "service_config_ui": os.getenv("ENABLE_SERVICE_CONFIG_UI", "false").lower() == "true",
    "advanced_billing": os.getenv("ENABLE_BILLING", "false").lower() == "true",
    "database_storage": os.getenv("ENABLE_DATABASE", "false").lower() == "true"
}

# Configure Flask paths
app = Flask(__name__, template_folder='templates')

# Configure sessions for web authentication
app.secret_key = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

# Development-friendly session configuration
# This allows sessions to work across localhost/127.0.0.1/IP addresses
app.config['SESSION_COOKIE_DOMAIN'] = None  # Don't restrict to specific domain
app.config['SESSION_COOKIE_PATH'] = '/'     # Available across entire site
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow reasonable cross-origin usage
app.config['SESSION_COOKIE_SECURE'] = False    # Allow HTTP for development
app.config['SESSION_COOKIE_HTTPONLY'] = True   # Prevent JavaScript access (security)

# For production, you would set:
# app.config['SESSION_COOKIE_DOMAIN'] = '.yourdomain.com'  # Allow subdomains
# app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only

# Enable CORS for all routes
CORS(app, origins=["*"])

# Import and register routes
from routes.api_routes import register_routes
register_routes(app)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8520))  # Use allocated CTO Dashboard port
    app.run(host="0.0.0.0", port=port, debug=True)