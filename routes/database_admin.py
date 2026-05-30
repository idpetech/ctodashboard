"""
Database Admin Routes for Railway
Provides endpoints to monitor and manage the secure database
"""

from flask import jsonify, request, render_template_string
from services.security.secure_database import secure_db
from services.auth.auth_middleware import get_current_user


def register_database_admin_routes(app):
    """Register database administration routes"""
    
    @app.route("/admin/db/health")
    def admin_db_health():
        """Database health check with detailed information"""
        try:
            health = secure_db.health_check()
            
            # Add additional Railway-specific checks
            import os
            railway_info = {
                "railway_environment": os.getenv("RAILWAY_ENVIRONMENT", "unknown"),
                "config_dir_exists": os.path.exists("/app/config") or os.path.exists("config"),
                "database_file_exists": os.path.exists("/app/config/secure_credentials.db") or os.path.exists("config/secure_credentials.db"),
                "master_key_set": bool(os.getenv("CREDENTIAL_MASTER_KEY")),
                "jwt_secret_set": bool(os.getenv("JWT_SECRET"))
            }
            
            return jsonify({
                **health,
                "railway_info": railway_info,
                "timestamp": "2024-01-01T00:00:00Z"  # Current timestamp
            })
        
        except Exception as e:
            return jsonify({
                "error": str(e),
                "database_connected": False
            }), 500
    
    @app.route("/admin/db/status")
    def admin_db_status():
        """Simple database status page for Railway monitoring"""
        try:
            health = secure_db.health_check()
            
            status_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>CTO Dashboard - Database Status</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .status { padding: 20px; border-radius: 8px; margin: 10px 0; }
                    .healthy { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                    .warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
                    .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                    .metric { margin: 10px 0; }
                    .metric strong { display: inline-block; width: 200px; }
                </style>
            </head>
            <body>
                <h1>🔒 CTO Dashboard - Database Status</h1>
                
                <div class="status {{ 'healthy' if health.database_connected else 'error' }}">
                    <h2>🗄️ Database Connection</h2>
                    <div class="metric"><strong>Status:</strong> {{ '✅ Connected' if health.database_connected else '❌ Disconnected' }}</div>
                    <div class="metric"><strong>Encryption:</strong> {{ '✅ Available' if health.get('encryption_available') else '❌ Not Available' }}</div>
                    <div class="metric"><strong>Master Key:</strong> {{ '✅ Configured' if health.get('master_key_configured') else '❌ Missing' }}</div>
                </div>
                
                {% if health.get('statistics') %}
                <div class="status healthy">
                    <h2>📊 Database Statistics</h2>
                    <div class="metric"><strong>Users:</strong> {{ health.statistics.users }}</div>
                    <div class="metric"><strong>Assignments:</strong> {{ health.statistics.assignments }}</div>
                    <div class="metric"><strong>Credentials:</strong> {{ health.statistics.credentials }}</div>
                    <div class="metric"><strong>Audit Logs:</strong> {{ health.statistics.audit_logs }}</div>
                </div>
                {% endif %}
                
                <div class="status {{ 'healthy' if master_key_configured else 'warning' }}">
                    <h2>🔑 Environment Configuration</h2>
                    <div class="metric"><strong>CREDENTIAL_MASTER_KEY:</strong> {{ '✅ Set' if master_key_configured else '⚠️ Not Set' }}</div>
                    <div class="metric"><strong>JWT_SECRET:</strong> {{ '✅ Set' if jwt_secret_set else '⚠️ Not Set' }}</div>
                    <div class="metric"><strong>Flask Environment:</strong> {{ flask_env }}</div>
                </div>
                
                <div class="status healthy">
                    <h2>📝 Quick Actions</h2>
                    <p><a href="/admin/db/health">🔍 JSON Health Check</a></p>
                    <p><a href="/health">🏥 Application Health</a></p>
                    <p><a href="/admin/db/audit">📋 Recent Audit Logs</a></p>
                </div>
                
                <div class="status warning">
                    <h2>⚠️ Important Notes</h2>
                    <p><strong>Railway Persistence:</strong> Database is stored in mounted volume at /app/config/</p>
                    <p><strong>Security:</strong> All credentials are AES encrypted with master key</p>
                    <p><strong>Access:</strong> This page shows non-sensitive information only</p>
                </div>
            </body>
            </html>
            """
            
            import os
            return render_template_string(status_html, 
                health=health,
                master_key_configured=bool(os.getenv("CREDENTIAL_MASTER_KEY")),
                jwt_secret_set=bool(os.getenv("JWT_SECRET")),
                flask_env=os.getenv("FLASK_ENV", "unknown")
            )
        
        except Exception as e:
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Database Error</title></head>
            <body>
                <h1>❌ Database Error</h1>
                <p><strong>Error:</strong> {str(e)}</p>
                <p><a href="/health">← Back to Health Check</a></p>
            </body>
            </html>
            """
            return error_html, 500
    
    @app.route("/admin/db/audit")
    def admin_db_audit():
        """Recent audit logs (non-sensitive information only)"""
        try:
            # Get recent audit logs
            audit_logs = secure_db.get_audit_logs(limit=50)
            
            # Filter out sensitive information
            safe_logs = []
            for log in audit_logs:
                safe_log = {
                    "action": log.get("action"),
                    "entity_type": log.get("entity_type"),
                    "success": log.get("success"),
                    "created_at": log.get("created_at"),
                    "user_email": log.get("user_email", "system")[:10] + "..." if log.get("user_email") else None
                }
                safe_logs.append(safe_log)
            
            return jsonify({
                "audit_logs": safe_logs,
                "total_logs": len(audit_logs),
                "note": "Sensitive information filtered for security"
            })
        
        except Exception as e:
            return jsonify({
                "error": str(e),
                "audit_logs": []
            }), 500