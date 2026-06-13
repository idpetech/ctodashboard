"""Build connector config for metrics from Postgres credentials + assignment metadata."""

from services.auth.credential_service import CredentialService


def stored_connector_credentials(
    workspace_id: str, assignment_id: str, connector_type: str
) -> dict:
    return (
        CredentialService().get_workspace_credentials(workspace_id, assignment_id, connector_type)
        or {}
    )


def connector_credentials_ready(workspace_id: str, assignment_id: str, connector_type: str) -> bool:
    """True when this assignment has stored credentials for the connector (not platform env)."""
    stored = stored_connector_credentials(workspace_id, assignment_id, connector_type)
    if connector_type == "github":
        token = stored.get("github_token") or stored.get("token")
        org = stored.get("github_org") or stored.get("org")
        return bool(token and org)
    if connector_type == "jira":
        return bool(
            (stored.get("jira_token") or stored.get("token"))
            and (stored.get("jira_email") or stored.get("email"))
            and (stored.get("jira_url") or stored.get("url"))
        )
    if connector_type == "aws":
        return bool(stored.get("aws_access_key") and stored.get("aws_secret_key"))
    if connector_type == "openai":
        return bool(stored.get("openai_api_key") or stored.get("api_key"))
    if connector_type == "railway":
        token = stored.get("railway_token") or stored.get("token")
        project_id = stored.get("railway_project_id") or stored.get("project_id")
        return bool(token and project_id)
    if connector_type == "vercel":
        token = stored.get("vercel_token") or stored.get("token")
        project_id = stored.get("vercel_project_id") or stored.get("project_id")
        return bool(token and project_id)
    return bool(stored)


def missing_connector_message(connector_type: str) -> str:
    labels = {
        "github": "GitHub",
        "jira": "Jira",
        "aws": "AWS",
        "openai": "OpenAI",
        "railway": "Railway",
        "vercel": "Vercel",
    }
    name = labels.get(connector_type, connector_type)
    return (
        f"{name} is enabled for this assignment but credentials are not configured. "
        "Add them in Setup → Workspace Settings → Connector Credentials."
    )


def github_metrics_config(workspace_id: str, assignment_id: str, github_config: dict) -> dict:
    stored = stored_connector_credentials(workspace_id, assignment_id, "github")
    legacy = github_config.get("auth_instance", {}).get("credentials", {}) or {}
    org = stored.get("github_org") or legacy.get("github_org") or stored.get("org") or ""
    repos_raw = stored.get("github_repos") or legacy.get("github_repos") or ""
    repos = [r.strip() for r in repos_raw.split(",") if r.strip()]
    return {"org": org, "repos": repos}


def jira_metrics_config(workspace_id: str, assignment_id: str, jira_config: dict) -> dict:
    stored = stored_connector_credentials(workspace_id, assignment_id, "jira")
    merged = {**jira_config, **stored}
    if not merged.get("project_key"):
        projects = merged.get("jira_projects") or merged.get("project_key")
        if projects:
            merged["project_key"] = str(projects).split(",")[0].strip()
    return merged


def railway_metrics_config(workspace_id: str, assignment_id: str, railway_config: dict) -> dict:
    stored = stored_connector_credentials(workspace_id, assignment_id, "railway")
    return {
        "project_id": stored.get("railway_project_id") or railway_config.get("project_id") or "",
        "project_name": stored.get("railway_project_name")
        or railway_config.get("project_name")
        or "",
    }


def vercel_metrics_config(workspace_id: str, assignment_id: str, vercel_config: dict) -> dict:
    stored = stored_connector_credentials(workspace_id, assignment_id, "vercel")
    return {
        "project_id": stored.get("vercel_project_id") or vercel_config.get("project_id") or "",
        "team_id": stored.get("vercel_team_id") or vercel_config.get("team_id") or "",
    }
