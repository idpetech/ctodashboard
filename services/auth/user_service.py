"""Back-compat: auth is Postgres-only via SecureUserService."""

from services.auth.secure_user_service import SecureUserService as UserService

__all__ = ["UserService"]
