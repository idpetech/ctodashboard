"""
Authentication Middleware - Phase 3
Protects workspace endpoints with user authentication
"""

from functools import wraps

from flask import g, jsonify, redirect, request, session, url_for

from config.logging_config import get_logger

logger = get_logger(__name__)


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
            # FIRST: Check session (session cookie is sufficient auth)
            if "user_email" in session and "auth_token" in session:
                verification = user_service.verify_token(session["auth_token"])
                if verification.get("valid"):
                    g.current_user = verification["user"]
                    return f(*args, **kwargs)

            # THEN: Check for Authorization header (fallback for back-compat)
            auth_header = request.headers.get("Authorization")
            if auth_header:
                try:
                    scheme, token = auth_header.split(" ")
                    if scheme.lower() == "bearer":
                        verification = user_service.verify_token(token)
                        if verification.get("valid"):
                            g.current_user = verification["user"]
                            return f(*args, **kwargs)
                except ValueError:
                    pass

            # No valid session or Bearer token found
            return jsonify(
                {
                    "error": "Authentication required",
                    "message": "Please log in to access this resource",
                }
            ), 401

        return decorated_function

    def require_workspace_access(f):
        """
        Decorator to check workspace access for authenticated users.
        Phase 3: Ensure users can only access their workspaces.
        """

        @wraps(f)
        def decorated_function(*args, **kwargs):
            # STEP 1: Check authentication (session-first, then header fallback)
            user_authenticated = False

            # FIRST: Check session (session cookie is sufficient auth)
            if "user_email" in session and "auth_token" in session:
                verification = user_service.verify_token(session["auth_token"])
                if verification.get("valid"):
                    g.current_user = verification["user"]
                    user_authenticated = True

            # THEN: Check for Authorization header (fallback for back-compat)
            if not user_authenticated:
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    try:
                        scheme, token = auth_header.split(" ")
                        if scheme.lower() == "bearer":
                            verification = user_service.verify_token(token)
                            if verification.get("valid"):
                                g.current_user = verification["user"]
                                user_authenticated = True
                    except ValueError:
                        pass

            # No valid authentication found
            if not user_authenticated:
                return jsonify(
                    {
                        "error": "Authentication required",
                        "message": "Please log in to access this resource",
                    }
                ), 401

            # STEP 2: Check workspace access
            workspace_id = kwargs.get("workspace_id") or request.view_args.get("workspace_id")

            if not workspace_id:
                return jsonify(
                    {
                        "error": "Workspace ID required",
                        "message": "This endpoint requires a workspace ID",
                    }
                ), 400

            # Check if user has access to this workspace
            user_email = g.current_user["email"]
            if not user_service.check_workspace_access(user_email, workspace_id):
                return jsonify(
                    {
                        "error": "Access denied",
                        "message": f"You don't have access to workspace '{workspace_id}'",
                    }
                ), 403

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
            auth_header = request.headers.get("Authorization")

            if auth_header:
                try:
                    scheme, token = auth_header.split(" ")
                    if scheme.lower() == "bearer":
                        verification = user_service.verify_token(token)
                        if verification.get("valid"):
                            g.current_user = verification["user"]
                        else:
                            g.current_user = None
                    else:
                        g.current_user = None
                except (KeyError, ValueError, Exception) as e:
                    logger.warning("Authentication failed: %s", e)
                    g.current_user = None
            else:
                g.current_user = None

            return f(*args, **kwargs)

        return decorated_function

    def require_web_auth(f):
        """
        Decorator for web pages that require authentication.
        Redirects to login page if not authenticated instead of returning JSON.
        """

        @wraps(f)
        def decorated_function(*args, **kwargs):
            # For web pages, we can check session first, then fall back to header
            user = None

            # Option 1: Check session (if implemented)
            if "user_email" in session and "auth_token" in session:
                verification = user_service.verify_token(session["auth_token"])
                if verification.get("valid"):
                    user = verification["user"]

            # Option 2: Check Authorization header (for cases where JS sets it)
            if not user:
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    try:
                        scheme, token = auth_header.split(" ")
                        if scheme.lower() == "bearer":
                            verification = user_service.verify_token(token)
                            if verification.get("valid"):
                                user = verification["user"]
                    except (ValueError, KeyError) as e:
                        logger.warning("Token verification failed: %s", e)
                        pass

            # If no valid authentication found, redirect to login
            if not user:
                return redirect(url_for("index"))  # Redirect to dashboard/login page

            # Store user info for the endpoint
            g.current_user = user

            return f(*args, **kwargs)

        return decorated_function

    def require_admin(f):
        """Require authenticated user with admin role."""

        @require_auth
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user or user.get("role") != "admin":
                return jsonify(
                    {
                        "error": "Admin access required",
                        "message": "This endpoint is restricted to administrators",
                    }
                ), 403

            return f(*args, **kwargs)

        return decorated_function

    def require_web_workspace_access(f):
        """
        Decorator for web pages that require workspace access.
        Combines authentication check with workspace access check.
        """

        @wraps(f)
        def decorated_function(*args, **kwargs):
            # STEP 1: Check authentication (same as require_web_auth)
            user = None

            # Debug logging
            print(f"DEBUG: Workspace auth check for {request.url}")
            print(f"DEBUG: Session keys: {list(session.keys())}")

            # Check session first
            if "user_email" in session and "auth_token" in session:
                print(f"DEBUG: Found session data for {session['user_email']}")
                verification = user_service.verify_token(session["auth_token"])
                if verification.get("valid"):
                    print("DEBUG: Session token is valid")
                    user = verification["user"]
                else:
                    print(f"DEBUG: Session token invalid: {verification}")
            else:
                print("DEBUG: No session data found")

            # Fall back to Authorization header (for cross-hostname access)
            if not user:
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    try:
                        scheme, token = auth_header.split(" ")
                        if scheme.lower() == "bearer":
                            verification = user_service.verify_token(token)
                            if verification.get("valid"):
                                user = verification["user"]
                                # Restore session if header auth worked (helpful for hostname switches)
                                session["user_email"] = user["email"]
                                session["auth_token"] = token
                    except (ValueError, KeyError) as e:
                        logger.warning("Session restoration failed: %s", e)
                        pass

            # Final fallback: Check localStorage token via cookie
            if not user:
                # Check if there's a token in a special cookie (set by frontend)
                token_cookie = request.cookies.get("auth_token_backup")
                if token_cookie:
                    verification = user_service.verify_token(token_cookie)
                    if verification.get("valid"):
                        user = verification["user"]
                        # Restore session
                        session["user_email"] = user["email"]
                        session["auth_token"] = token_cookie

            # If no authentication, redirect to login
            if not user:
                return redirect(url_for("index"))

            g.current_user = user

            # STEP 2: Check workspace access
            workspace_id = kwargs.get("workspace_id") or request.view_args.get("workspace_id")

            if not workspace_id:
                # For web pages, we could redirect to a "select workspace" page
                return redirect(url_for("index"))

            # Check workspace access
            user_email = user["email"]
            if not user_service.check_workspace_access(user_email, workspace_id):
                # Redirect to dashboard with error message
                return redirect(url_for("index") + "?error=workspace_access_denied")

            g.current_workspace = workspace_id

            return f(*args, **kwargs)

        return decorated_function

    # Return all decorators from the factory function
    return (
        require_auth,
        require_workspace_access,
        optional_auth,
        require_web_auth,
        require_web_workspace_access,
        require_admin,
    )


def get_current_user():
    """Helper function to get current authenticated user"""
    return getattr(g, "current_user", None)


def get_current_workspace():
    """Helper function to get current workspace"""
    return getattr(g, "current_workspace", None)
