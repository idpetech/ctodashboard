import logging
import os
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


def normalize_jira_base_url(url: str) -> str:
    """Normalize user-entered Jira site URL to scheme + host only."""
    raw = (url or "").strip()
    if not raw:
        return ""
    if not raw.startswith("http"):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.netloc:
        return ""
    scheme = parsed.scheme or "https"
    return f"{scheme}://{parsed.netloc}".rstrip("/")


def test_jira_connection(url: str, email: str, token: str) -> dict:
    """Validate Jira Cloud/Server credentials against the REST API."""
    jira_url = normalize_jira_base_url(url)
    if not jira_url:
        return {"valid": False, "error": "Jira URL is required"}

    email = (email or "").strip()
    token = (token or "").strip()
    if not email:
        return {"valid": False, "error": "Jira email is required"}
    if not token:
        return {"valid": False, "error": "Jira token is required"}

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "CTOLens/1.0",
        }
    )

    def _redirect_error(response, context):
        if response.history:
            return {
                "valid": False,
                "error": (
                    f"Jira redirected {context} to {response.url}. "
                    f"Use only your site root URL, e.g. https://yourcompany.atlassian.net"
                ),
            }
        return None

    def _html_error(response, context):
        text = (response.text or "").strip()
        if text.lstrip().startswith("<"):
            return {
                "valid": False,
                "error": (
                    f"Jira returned a web page instead of API data when checking {context}. "
                    f"Use your site root URL only (https://yourcompany.atlassian.net), "
                    "not a project, board, or browse link."
                ),
            }
        return None

    try:
        info_resp = session.get(
            f"{jira_url}/rest/api/3/serverInfo",
            timeout=15,
            allow_redirects=True,
        )
        redirect_err = _redirect_error(info_resp, "the site URL")
        if redirect_err:
            return redirect_err
        if info_resp.status_code == 200:
            html_err = _html_error(info_resp, "the site URL")
            if html_err:
                return html_err
            try:
                info_resp.json()
            except ValueError:
                return {
                    "valid": False,
                    "error": (
                        f"{jira_url} did not return valid Jira API data. "
                        "Use your Atlassian site root, e.g. https://yourcompany.atlassian.net"
                    ),
                }

        auth = HTTPBasicAuth(email, token)
        last_error = "Could not reach Jira API — check URL and credentials"

        for api_path in ("/rest/api/3/myself", "/rest/api/2/myself"):
            response = session.get(
                f"{jira_url}{api_path}",
                auth=auth,
                timeout=15,
                allow_redirects=True,
            )

            redirect_err = _redirect_error(response, "authentication")
            if redirect_err:
                return redirect_err

            if response.status_code == 404 and api_path.endswith("/3/myself"):
                continue

            if response.status_code == 200:
                text = (response.text or "").strip()
                if not text:
                    return {
                        "valid": False,
                        "error": (
                            "Jira returned an empty response — "
                            "use https://yourcompany.atlassian.net (site root only)"
                        ),
                    }
                html_err = _html_error(response, "authentication")
                if html_err:
                    return html_err
                try:
                    user_data = response.json()
                except ValueError:
                    return {
                        "valid": False,
                        "error": "Jira returned unexpected data — verify the site URL and API token",
                    }
                return {
                    "valid": True,
                    "user": user_data.get("emailAddress") or user_data.get("name"),
                    "displayName": user_data.get("displayName"),
                    "accountId": user_data.get("accountId") or user_data.get("key"),
                }

            if response.status_code == 401:
                return {
                    "valid": False,
                    "error": (
                        "Authentication failed — the email must match the Atlassian account "
                        "that created the API token. Create or verify your token at "
                        "id.atlassian.com/manage-profile/security/api-tokens"
                    ),
                }
            if response.status_code == 403:
                return {"valid": False, "error": "Jira token lacks required permissions"}
            if response.status_code == 404:
                last_error = (
                    f"Jira API not found at {jira_url}. "
                    "Use your Atlassian Cloud site root, e.g. https://yourcompany.atlassian.net"
                )
            else:
                last_error = f"Jira API error: HTTP {response.status_code}"

        return {"valid": False, "error": last_error}
    except requests.exceptions.ConnectionError:
        return {
            "valid": False,
            "error": f"Cannot connect to {jira_url} — check the site URL and network access",
        }
    except requests.exceptions.Timeout:
        return {"valid": False, "error": "Jira API request timed out"}
    except Exception as e:
        return {"valid": False, "error": f"Jira connection failed: {str(e)}"}


class EmbeddedJiraMetrics:
    """Jira metrics embedded directly in the Flask app"""

    def __init__(self, workspace_id=None, assignment_id=None):
        # Phase 3: Support workspace credentials with environment variable fallback
        self.workspace_id = workspace_id
        self.assignment_id = assignment_id

        # Initialize credentials (preserves existing behavior if no workspace context)
        self._init_credentials()

    def _init_credentials(self):
        """Initialize Jira credentials with workspace support and env var fallback"""
        if self.workspace_id and self.assignment_id:
            try:
                from services.auth.credential_service import CredentialService

                credential_service = CredentialService()
                credentials = credential_service.get_jira_credentials(
                    self.workspace_id, self.assignment_id
                )
                self.base_url = credentials.get("url") or os.getenv("JIRA_URL")
                self.email = credentials.get("email") or os.getenv("JIRA_EMAIL")
                self.token = credentials.get("token") or os.getenv("JIRA_TOKEN")
            except Exception as e:
                logger.warning(
                    "Could not load workspace credentials, falling back to env vars: %s", e
                )
                self.base_url = os.getenv("JIRA_URL")
                self.email = os.getenv("JIRA_EMAIL")
                self.token = os.getenv("JIRA_TOKEN")
        else:
            # Fallback to environment variables (preserves existing behavior)
            self.base_url = os.getenv("JIRA_URL")
            self.email = os.getenv("JIRA_EMAIL")
            self.token = os.getenv("JIRA_TOKEN")

        if self.base_url:
            self.base_url = normalize_jira_base_url(self.base_url)
        if self.email:
            self.email = self.email.strip()
        if self.token:
            self.token = self.token.strip()

    def get_project_metrics(self, project_key: str) -> dict:
        """Get Jira project metrics"""
        if not all([self.base_url, self.email, self.token]):
            return {"error": "Jira credentials not configured"}

        try:
            auth = (self.email, self.token)
            headers = {"Accept": "application/json"}

            # Get project info
            project_url = f"{self.base_url}/rest/api/3/project/{project_key}"
            project_response = requests.get(project_url, auth=auth, headers=headers, timeout=10)
            project_data = project_response.json() if project_response.status_code == 200 else {}

            # Issues last 7 and 30 days
            issues_7 = self._search_issues(project_key, auth, headers, days=7)
            search_url = f"{self.base_url}/rest/api/3/search/jql"
            jql_query = f"project = '{project_key}' AND created >= -30d"
            search_payload = {
                "jql": jql_query,
                "fields": ["status", "priority", "created", "resolutiondate"],
                "maxResults": 100,
            }

            headers_with_content = {**headers, "Content-Type": "application/json"}
            search_response = requests.post(
                search_url, auth=auth, headers=headers_with_content, json=search_payload, timeout=10
            )

            if search_response.status_code != 200:
                return {
                    "error": f"Jira API returned {search_response.status_code}: {search_response.text[:200]}"
                }

            search_data = search_response.json()
            issues = search_data.get("issues", [])

            # Calculate metrics
            total_issues = len(issues)
            resolved_issues = len([i for i in issues if i["fields"].get("resolutiondate")])

            return {
                "project_key": project_key,
                "project_name": project_data.get("name", "Unknown"),
                "jira_issues_last_7_days": issues_7,
                "total_issues_last_30_days": total_issues,
                "resolved_issues_last_30_days": resolved_issues,
                "resolution_rate": round(resolved_issues / total_issues * 100, 1)
                if total_issues > 0
                else 0,
            }

        except Exception as e:
            return {"error": f"Jira API error: {str(e)}"}

    def _search_issues(self, project_key: str, auth, headers, *, days: int) -> int:
        search_url = f"{self.base_url}/rest/api/3/search/jql"
        jql_query = f"project = '{project_key}' AND created >= -{days}d"
        search_payload = {
            "jql": jql_query,
            "fields": ["status"],
            "maxResults": 100,
        }
        headers_with_content = {**headers, "Content-Type": "application/json"}
        search_response = requests.post(
            search_url,
            auth=auth,
            headers=headers_with_content,
            json=search_payload,
            timeout=10,
        )
        if search_response.status_code != 200:
            return 0
        return len(search_response.json().get("issues", []))

    def get_metrics(self, config: dict) -> dict:
        """Get Jira metrics with configuration - main method called by routes"""
        project_key = config.get("project_key")
        if not project_key:
            return {"error": "No Jira project_key specified in configuration"}

        metrics = self.get_project_metrics(project_key)

        # Add configuration context
        metrics["config"] = {
            "project_key": project_key,
            "track_sprints": config.get("track_sprints", False),
            "track_bugs": config.get("track_bugs", False),
            "enabled": config.get("enabled", False),
        }

        return metrics


# Note: This is a service class, no Flask routes needed here
# Routes are handled in the main integrated_dashboard.py file
