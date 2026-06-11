"""
Shared dependencies for API route modules.

Lazy service accessors, auth decorators, connector metrics helpers, and
analytics tracking used across routes.api.* modules.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.logging_config import get_logger
from connectors.registry import ConnectorRegistry
from services.assignment_metrics_config import (
    github_metrics_config as build_github_metrics_config,
)
from services.assignment_metrics_config import (
    jira_metrics_config as build_jira_metrics_config,
)
from services.auth.auth_middleware import create_auth_decorators, get_current_user
from services.auth.secure_user_service import SecureUserService
from services.data_export_service import DataExportService
from services.data_import_service import DataImportService
from services.embedded.aws_metrics import EmbeddedAWSMetrics
from services.embedded.github_metrics import EmbeddedGitHubMetrics
from services.embedded.jira_metrics import (
    EmbeddedJiraMetrics,
)
from services.embedded.railway_metrics import RailwayMetrics
from services.service_manager import ServiceManager
from services.workspace.workspace_service import WorkspaceService

# Initialize logging
logger = get_logger(__name__)


def _track_product_event(event_name: str, metadata=None, user_id=None):
    """Fire-and-forget product analytics (no-op when flag off)."""
    from services.analytics.event_tracker import track_from_flask

    track_from_flask(event_name, user_id=user_id, metadata=metadata)


def _track_report_generated(source: str, workspace_id: str, **extra):
    from services.analytics.event_tracker import track_from_flask
    from services.analytics.models import EVENT_REPORT_GENERATED

    meta = {"source": source, "workspace_id": workspace_id, **extra}
    track_from_flask(EVENT_REPORT_GENERATED, metadata=meta)


# Lazy service initialization - services created only when needed
_service_manager = None
_workspace_service = None
_user_service = None
_export_service = None
_import_service = None


def get_service_manager():
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager


def get_workspace_service():
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service


def get_user_service():
    global _user_service
    if _user_service is None:
        _user_service = SecureUserService()
    return _user_service


def get_export_service():
    global _export_service
    if _export_service is None:
        _export_service = DataExportService()
    return _export_service


def get_import_service():
    global _import_service
    if _import_service is None:
        _import_service = DataImportService()
    return _import_service


# Lazy authentication decorators - created only when needed
_auth_decorators = None


def get_auth_decorators():
    global _auth_decorators
    if _auth_decorators is None:
        _auth_decorators = create_auth_decorators(get_user_service())
    return _auth_decorators


def get_require_auth():
    return get_auth_decorators()[0]


def get_require_workspace_access():
    return get_auth_decorators()[1]


def get_optional_auth():
    return get_auth_decorators()[2]


def get_require_web_auth():
    decorators = get_auth_decorators()
    return decorators[3] if len(decorators) >= 4 else None


def get_require_web_workspace_access():
    decorators = get_auth_decorators()
    return decorators[4] if len(decorators) >= 5 else None


# Global connector instances (for backward compatibility)
aws_metrics = EmbeddedAWSMetrics()
github_metrics = EmbeddedGitHubMetrics()
jira_metrics = EmbeddedJiraMetrics()
railway_metrics = RailwayMetrics()


def get_workspace_connectors(workspace_id, assignment_id):
    """
    Create workspace-scoped connector instances with credentials from Postgres store.
    """
    return {
        "github": EmbeddedGitHubMetrics(workspace_id=workspace_id, assignment_id=assignment_id),
        "jira": EmbeddedJiraMetrics(workspace_id=workspace_id, assignment_id=assignment_id),
        "aws": EmbeddedAWSMetrics(workspace_id=workspace_id, assignment_id=assignment_id),
        "openai": ConnectorRegistry.get_connector("openai", workspace_id, assignment_id),
    }


def _run_connector_metrics(name: str, fn):
    """Run one connector fetch; return (name, result, elapsed_seconds)."""
    started = time.monotonic()
    try:
        result = fn()
        return name, result, time.monotonic() - started
    except Exception as e:
        logger.exception("%s metrics fetch failed", name)
        return name, {"error": str(e)}, time.monotonic() - started


def collect_assignment_metrics(workspace_id: str, assignment_id: str, assignment: dict) -> dict:
    """Gather enabled connector metrics in parallel (external APIs are slow)."""
    started_total = time.monotonic()
    connectors = get_workspace_connectors(workspace_id, assignment_id)
    metrics = {}
    metrics_config = assignment.get("metrics_config") or {}
    jobs = {}

    aws_config = metrics_config.get("aws", {})
    if aws_config.get("enabled", False):
        jobs["aws"] = lambda: connectors["aws"].get_metrics()

    github_config = metrics_config.get("github", {})
    if github_config.get("enabled", False):
        gh_cfg = build_github_metrics_config(workspace_id, assignment_id, github_config)
        jobs["github"] = lambda c=connectors["github"], g=gh_cfg: c.get_metrics(g)

    jira_config = metrics_config.get("jira", {})
    if jira_config.get("enabled", False):
        jira_merged = build_jira_metrics_config(workspace_id, assignment_id, jira_config)
        jobs["jira"] = lambda c=connectors["jira"], j=jira_merged: c.get_metrics(j)

    openai_config = metrics_config.get("openai", {})
    if openai_config.get("enabled", False):
        openai_connector = ConnectorRegistry.get_connector("openai", workspace_id, assignment_id)
        jobs["openai"] = lambda o=openai_connector, cfg=openai_config: o.get_metrics(cfg)

    railway_config = metrics_config.get("railway", {})
    if railway_config.get("enabled", False):
        import asyncio

        pid = railway_config.get("project_id")
        pname = railway_config.get("project_name")

        def _railway():
            return asyncio.run(railway_metrics.get_metrics(project_id=pid, project_name=pname))

        jobs["railway"] = _railway

    if not jobs:
        return metrics

    max_workers = min(len(jobs), 4)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_connector_metrics, name, fn): name for name, fn in jobs.items()}
        for future in as_completed(futures, timeout=90):
            name, result, elapsed = future.result()
            metrics[name] = result
            logger.info(
                "Metrics %s ws=%s assignment=%s done in %.1fs",
                name,
                workspace_id,
                assignment_id,
                elapsed,
            )
            if isinstance(result, dict):
                err = result.get("error") or (
                    result.get("cost_analysis", {}).get("error") if name == "aws" else None
                )
                if err:
                    logger.warning(
                        "Metrics %s error ws=%s assignment=%s: %s",
                        name,
                        workspace_id,
                        assignment_id,
                        err,
                    )

    logger.info(
        "Metrics total ws=%s assignment=%s %.1fs connectors=%s",
        workspace_id,
        assignment_id,
        time.monotonic() - started_total,
        list(metrics.keys()),
    )
    return metrics


def _refresh_workspace_attention_briefing(workspace_id: str) -> None:
    """Rebuild stored CTO briefing after assignment/budget changes (best-effort)."""
    try:
        from services.security.secure_database import secure_db

        ws_result = get_workspace_service().get_workspace_assignments(workspace_id)
        assignments = ws_result.get("assignments") or []

        if os.getenv("ENABLE_CTOLENS_BRIEFING", "false").lower() == "true":
            # CTOLens uses fingerprint staleness; user refreshes from the UI.
            return

        if os.getenv("ENABLE_ATTENTION_ENGINE", "false").lower() != "true":
            return

        from services.attention_engine import (
            build_attention_briefing,
            get_stored_briefing,
            store_briefing_in_workspace,
        )

        previous = get_stored_briefing(secure_db, workspace_id)
        last_import = (
            (secure_db.get_workspace(workspace_id) or {}).get("settings", {}).get("last_import")
        )
        briefing = build_attention_briefing(
            assignments,
            previous_briefing=previous,
            import_metadata=last_import,
        )
        store_briefing_in_workspace(secure_db, workspace_id, briefing)
    except Exception as e:
        logger.warning("Briefing auto-refresh failed for %s: %s", workspace_id, e)
