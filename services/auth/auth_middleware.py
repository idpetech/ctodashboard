"""
Authentication Middleware - Phase 3
Protects workspace endpoints with user authentication
"""

from functools import wraps
from flask import request, jsonify, g

def create_auth_decorators(user_service):
    """
    Factory function to create authentication decorators with injected UserService.
    Eliminates global state and enables proper dependency injection.
    """
    
    def require_auth(f):
        """
        Decorator to require authentication for API endpoints.
        Phase 3: Protect workspace operations with user auth.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    "error": "Authentication required",
                    "message": "Please provide Authorization header with Bearer token"
                }), 401
            
            # Extract token
            try:
                scheme, token = auth_header.split(' ')
                if scheme.lower() != 'bearer':
                    raise ValueError("Invalid scheme")
            except ValueError:
                return jsonify({
                    "error": "Invalid authorization format",
                    "message": "Authorization header must be 'Bearer <token>'"
                }), 401
            
            # Verify token
            verification = user_service.verify_token(token)
            if not verification.get("valid"):
                return jsonify({
                    "error": "Invalid token",
                    "message": verification.get("error", "Token verification failed")
                }), 401
            
            # Store user info in Flask's g object for use in the endpoint
            g.current_user = verification["user"]
            
            return f(*args, **kwargs)
        
        return decorated_function

    def require_workspace_access(f):
        """
        Decorator to check workspace access for authenticated users.
        Phase 3: Ensure users can only access their workspaces.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # STEP 1: Check authentication (inline the require_auth logic)
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    "error": "Authentication required",
                    "message": "Please provide Authorization header with Bearer token"
                }), 401
            
            # Extract token
            try:
                scheme, token = auth_header.split(' ')
                if scheme.lower() != 'bearer':
                    raise ValueError("Invalid scheme")
            except ValueError:
                return jsonify({
                    "error": "Invalid authorization format",
                    "message": "Authorization header must be 'Bearer <token>'"
                }), 401
            
            # Verify token
            verification = user_service.verify_token(token)
            if not verification.get("valid"):
                return jsonify({
                    "error": "Invalid token",
                    "message": verification.get("error", "Token verification failed")
                }), 401
            
            # Store user info in Flask's g object for use in the endpoint
            g.current_user = verification["user"]
            
            # STEP 2: Check workspace access
            workspace_id = kwargs.get('workspace_id') or request.view_args.get('workspace_id')
            
            if not workspace_id:
                return jsonify({
                    "error": "Workspace ID required",
                    "message": "This endpoint requires a workspace ID"
                }), 400
            
            # Check if user has access to this workspace
            user_email = g.current_user["email"]
            if not user_service.check_workspace_access(user_email, workspace_id):
                return jsonify({
                    "error": "Access denied",
                    "message": f"You don't have access to workspace '{workspace_id}'"
                }), 403
            
            # Store workspace_id in g for use in endpoint
            g.current_workspace = workspace_id
            
            # STEP 3: Call the original function
            return f(*args, **kwargs)
        
        return decorated_function

    def optional_auth(f):
        """
        Decorator for optional authentication.
        Phase 3: Some endpoints work with or without auth.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for Authorization header
            auth_header = request.headers.get('Authorization')
            
            if auth_header:
                try:
                    scheme, token = auth_header.split(' ')
                    if scheme.lower() == 'bearer':
                        verification = user_service.verify_token(token)
                        if verification.get("valid"):
                            g.current_user = verification["user"]
                        else:
                            g.current_user = None
                    else:
                        g.current_user = None
                except:
                    g.current_user = None
            else:
                g.current_user = None
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    # Return all decorators from the factory function
    return require_auth, require_workspace_access, optional_auth

def get_current_user():
    """Helper function to get current authenticated user"""
    return getattr(g, 'current_user', None)

def get_current_workspace():
    """Helper function to get current workspace"""
    return getattr(g, 'current_workspace', None)