"""API route module — see routes.api.register_routes."""

from flask import jsonify, request

from routes.api.deps import (
    _track_product_event,
    get_current_user,
    get_require_auth,
    get_user_service,
    logger,
)
from services.stripe_billing_service import (
    billing_summary,
    confirm_checkout_session,
    create_checkout_session,
    create_portal_session,
    handle_webhook,
    is_billing_enabled,
)
from services.trial_service import admin_trial_summary
from services.user_access import resolve_account_state


def register_auth_billing_routes(app):
    """Register auth billing routes."""
    # ===== AUTHENTICATION ENDPOINTS (Phase 3) =====

    @app.route("/api/auth/register", methods=["POST"])
    def register():
        """Register a new user account and auto-login"""
        from flask import session

        data = request.get_json()
        if not data:
            return jsonify({"error": "No registration data provided"}), 400

        email = data.get("email")
        password = data.get("password")
        display_name = data.get("display_name") or data.get("name")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        result = get_user_service().register_user(email, password, display_name)

        if result.get("success"):
            token = result.get("token")
            user = result.get("user")
            if not token:
                login_result = get_user_service().authenticate_user(email, password)
                token = login_result.get("token")
                user = login_result.get("user") or user

            if token:
                session["user_email"] = email
                session["auth_token"] = token
                session["user_data"] = user
                session.permanent = True
                _track_product_event(
                    "user_signup", metadata={"email_domain": email.split("@")[-1]}, user_id=email
                )
                _track_product_event(
                    "user_login", metadata={"method": "register_auto_login"}, user_id=email
                )
                return jsonify(
                    {
                        "success": True,
                        "message": "User registered and logged in successfully",
                        "user": user,
                        "token": token,
                        "auto_logged_in": True,
                    }
                ), 201

            return jsonify(
                {
                    "success": True,
                    "message": "User registered but login failed. Please sign in manually.",
                    "user": user,
                    "auto_login_error": "No token issued",
                }
            ), 201
        else:
            return jsonify(result), 400

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        """Authenticate user and return token"""
        from flask import session

        data = request.get_json()
        if not data:
            return jsonify({"error": "No login data provided"}), 400

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        result = get_user_service().authenticate_user(email, password)

        if result.get("success"):
            # Store authentication in session for web pages
            session["user_email"] = email
            session["auth_token"] = result.get("token")
            session["user_data"] = result.get("user")
            session.permanent = True  # Keep session across browser restarts
            _track_product_event("user_login", metadata={"method": "password"}, user_id=email)

            return jsonify(result), 200
        else:
            return jsonify(result), 401

    @app.route("/api/auth/logout", methods=["POST"])
    def logout():
        """Logout user and clear session"""
        from flask import session

        from services.analytics.event_tracker import end_flask_session

        end_flask_session(session.get("user_email"))
        session.clear()
        return jsonify({"success": True, "message": "Logged out successfully"}), 200

    @app.route("/api/auth/verify", methods=["GET"])
    def verify_token():
        """Verify current token or session and return user info"""
        from flask import session

        # Check session first (for page refreshes)
        if "user_email" in session and "auth_token" in session:
            verification = get_user_service().verify_token(session["auth_token"])
            if verification.get("valid"):
                return jsonify(
                    {
                        "valid": True,
                        "user": verification["user"],
                        "token": session["auth_token"],
                    }
                )

        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            try:
                scheme, token = auth_header.split(" ")
                if scheme.lower() == "bearer":
                    verification = get_user_service().verify_token(token)
                    if verification.get("valid"):
                        return jsonify(
                            {
                                "valid": True,
                                "user": verification["user"],
                                "token": token,
                            }
                        )
            except ValueError:
                pass

        return jsonify({"valid": False, "error": "No valid authentication found"}), 401

    @app.route("/api/auth/users", methods=["GET"])
    @get_require_auth()
    def list_users():
        """List all users (admin only)"""
        current_user = get_current_user()

        # Only admins can list users
        if current_user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        users = []
        for row in get_user_service().list_users():
            full = get_user_service().get_user_by_email(row.get("email"))
            if full:
                users.append(admin_trial_summary(full))
            else:
                users.append(row)
        return jsonify({"users": users})

    @app.route("/api/auth/users/<user_email>/trial", methods=["PATCH"])
    @get_require_auth()
    def admin_update_user_trial(user_email):
        """Update trial status for a user (admin only)."""
        current_user = get_current_user()
        if current_user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        data = request.get_json() or {}
        result = get_user_service().set_user_trial(
            user_email,
            trial_status=data.get("trial_status"),
            trial_end_date=data.get("trial_end_date"),
            extend_days=data.get("extend_days"),
        )
        if result.get("success"):
            return jsonify(result)
        return jsonify(result), 400

    @app.route("/api/auth/trial", methods=["GET"])
    @get_require_auth()
    def get_trial_status():
        """Current user's trial + billing status for dashboard banner and UI."""
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Authentication required"}), 401
        full = get_user_service().get_user_by_email(current_user.get("email"))
        if not full:
            return jsonify({"error": "User not found"}), 404
        return jsonify(resolve_account_state(full))

    @app.route("/api/billing/status", methods=["GET"])
    @get_require_auth()
    def get_billing_status():
        """Billing summary for the current user."""
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Authentication required"}), 401
        full = get_user_service().get_user_by_email(current_user.get("email"))
        if not full:
            return jsonify({"error": "User not found"}), 404
        return jsonify(resolve_account_state(full))

    @app.route("/api/billing/checkout", methods=["POST"])
    @get_require_auth()
    def billing_checkout():
        """Create a Stripe Checkout session for subscription upgrade."""
        if not is_billing_enabled():
            return jsonify({"error": "Billing is not enabled"}), 503

        current_user = get_current_user()
        data = request.get_json() or {}
        plan = (data.get("plan") or "").strip().lower()
        if plan != "starter":
            return jsonify({"error": "Invalid plan. Only Starter is available at this time."}), 400

        full = get_user_service().get_user_by_email(current_user.get("email"))
        if not full:
            return jsonify({"error": "User not found"}), 404

        billing = billing_summary(full)
        base_url = request.host_url.rstrip("/")
        try:
            session = create_checkout_session(
                full["email"],
                plan,
                success_url=f"{base_url}/dashboard?billing=success&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{base_url}/dashboard?billing=canceled",
                existing_customer_id=billing.get("stripe_customer_id"),
            )
            return jsonify(session)
        except Exception as e:
            logger.error("Checkout session failed: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/billing/confirm", methods=["POST"])
    @get_require_auth()
    def billing_confirm():
        """Confirm checkout after redirect (no webhook required)."""
        if not is_billing_enabled():
            return jsonify({"error": "Billing is not enabled"}), 503

        current_user = get_current_user()
        data = request.get_json() or {}
        session_id = (data.get("session_id") or "").strip()
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        try:
            confirm_checkout_session(session_id, current_user.get("email"))
            full = get_user_service().get_user_by_email(current_user.get("email"))
            return jsonify(resolve_account_state(full))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error("Billing confirm failed: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/billing/portal", methods=["POST"])
    @get_require_auth()
    def billing_portal():
        """Create a Stripe Billing Portal session."""
        if not is_billing_enabled():
            return jsonify({"error": "Billing is not enabled"}), 503

        current_user = get_current_user()
        full = get_user_service().get_user_by_email(current_user.get("email"))
        if not full:
            return jsonify({"error": "User not found"}), 404

        billing = billing_summary(full)
        customer_id = billing.get("stripe_customer_id")
        if not customer_id:
            return jsonify({"error": "No billing account found. Upgrade first."}), 400

        base_url = request.host_url.rstrip("/")
        try:
            session = create_portal_session(customer_id, return_url=f"{base_url}/dashboard")
            return jsonify(session)
        except Exception as e:
            logger.error("Portal session failed: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/billing/webhook", methods=["POST"])
    def billing_webhook():
        """Stripe webhook handler (no auth — verified by signature)."""
        if not is_billing_enabled():
            return jsonify({"error": "Billing is not enabled"}), 503

        payload = request.get_data()
        sig = request.headers.get("Stripe-Signature", "")
        try:
            result = handle_webhook(payload, sig)
            return jsonify(result)
        except ValueError as e:
            logger.warning("Invalid webhook payload: %s", e)
            return jsonify({"error": "Invalid payload"}), 400
        except Exception as e:
            logger.error("Webhook error: %s", e)
            return jsonify({"error": str(e)}), 400

    @app.route("/api/auth/users/<user_email>/workspaces", methods=["POST"])
    @get_require_auth()
    def grant_workspace_access(user_email):
        """Grant user access to workspace (admin only)"""
        current_user = get_current_user()

        # Only admins can grant access (for now)
        if current_user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No workspace data provided"}), 400

        workspace_id = data.get("workspace_id")
        role = data.get("role", "member")

        if not workspace_id:
            return jsonify({"error": "Workspace ID is required"}), 400

        result = get_user_service().add_user_to_workspace(user_email, workspace_id, role)

        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    @app.route("/api/auth/profile", methods=["GET", "PUT"])
    @get_require_auth()
    def profile():
        """Get or update user profile information - Phase 5B"""
        current_user = get_current_user()
        user_email = current_user.get("email")

        if not user_email:
            return jsonify({"error": "User email not found in token"}), 401

        if request.method == "GET":
            # Get user profile
            result = get_user_service().get_user_profile(user_email)
            if result.get("success"):
                return jsonify(result["user"]), 200
            else:
                return jsonify(result), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No profile data provided"}), 400

        # Validate allowed fields for profile update
        allowed_fields = {"display_name", "password", "preferences"}
        updates = {k: v for k, v in data.items() if k in allowed_fields}

        if not updates:
            return jsonify({"error": "No valid profile fields provided"}), 400

        # Update the user profile
        result = get_user_service().update_user(user_email, updates)

        if result.get("success"):
            return jsonify(
                {"success": True, "message": result.get("message"), "user": result.get("user")}
            ), 200
        else:
            return jsonify({"success": False, "error": result.get("error")}), 400
