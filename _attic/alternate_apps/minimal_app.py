#!/usr/bin/env python3

from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>🚀 CTO Dashboard - WORKING!</h1>
    <p>Flask app is running successfully.</p>
    <p><a href="/api/health">Check API Health</a></p>
    <p><a href="/api/test">Test API</a></p>
    """

@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Flask app is working!"
    })

@app.route("/api/test")
def test():
    return jsonify({
        "message": "API is working!",
        "timestamp": datetime.utcnow().isoformat(),
        "test_data": {
            "github": "Mock GitHub data",
            "aws": "Mock AWS data", 
            "jira": "Mock Jira data"
        }
    })

if __name__ == "__main__":
    import os
    port = int(os.getenv('PORT', 8000))
    print(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
