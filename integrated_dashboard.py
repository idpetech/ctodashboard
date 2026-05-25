#!/usr/bin/env python3
"""
Integrated CTO Dashboard - Clean WSGI Boot File
All service logic is now in services/* modules and imported via routes/api_routes.py
"""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Flask paths
base_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(base_dir, 'frontend', 'dist')
template_folder = os.path.join(base_dir, 'templates')
app = Flask(__name__, static_folder=static_folder, static_url_path='', template_folder=template_folder)

# Enable CORS for all routes
CORS(app, origins=["*"])

# Import and register routes
from routes.api_routes import register_routes
register_routes(app)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3001))
    app.run(host="0.0.0.0", port=port, debug=True)