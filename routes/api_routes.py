"""
Backward-compatible API routes entry point.

Implementation lives in routes.api.* modules; this module re-exports shared
helpers used by services (e.g. collect_assignment_metrics).
"""

from routes.api import register_routes
from routes.api.deps import (
    aws_metrics,
    collect_assignment_metrics,
    get_auth_decorators,
    get_export_service,
    get_import_service,
    get_optional_auth,
    get_require_auth,
    get_require_web_auth,
    get_require_web_workspace_access,
    get_require_workspace_access,
    get_service_manager,
    get_user_service,
    get_workspace_connectors,
    get_workspace_service,
    github_metrics,
    jira_metrics,
    railway_metrics,
)

__all__ = [
    "register_routes",
    "collect_assignment_metrics",
    "get_workspace_service",
    "get_workspace_connectors",
    "get_user_service",
    "get_service_manager",
    "get_export_service",
    "get_import_service",
    "get_auth_decorators",
    "get_require_auth",
    "get_require_workspace_access",
    "get_optional_auth",
    "get_require_web_auth",
    "get_require_web_workspace_access",
    "aws_metrics",
    "github_metrics",
    "jira_metrics",
    "railway_metrics",
]
