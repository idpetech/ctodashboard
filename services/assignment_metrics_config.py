"""Build connector config for metrics from Postgres credentials + assignment metadata."""

from services.auth.credential_service import CredentialService


def stored_connector_credentials(
    workspace_id: str, assignment_id: str, connector_type: str
) -> dict:
    return (
        CredentialService().get_workspace_credentials(
            workspace_id, assignment_id, connector_type
        )
        or {}
    )


def github_metrics_config(
    workspace_id: str, assignment_id: str, github_config: dict
) -> dict:
    stored = stored_connector_credentials(workspace_id, assignment_id, "github")
    legacy = github_config.get("auth_instance", {}).get("credentials", {}) or {}
    org = (
        stored.get("github_org")
        or legacy.get("github_org")
        or stored.get("org")
        or ""
    )
    repos_raw = stored.get("github_repos") or legacy.get("github_repos") or ""
    repos = [r.strip() for r in repos_raw.split(",") if r.strip()]
    return {"org": org, "repos": repos}


def jira_metrics_config(
    workspace_id: str, assignment_id: str, jira_config: dict
) -> dict:
    stored = stored_connector_credentials(workspace_id, assignment_id, "jira")
    merged = {**jira_config, **stored}
    if not merged.get("project_key"):
        projects = merged.get("jira_projects") or merged.get("project_key")
        if projects:
            merged["project_key"] = str(projects).split(",")[0].strip()
    return merged
