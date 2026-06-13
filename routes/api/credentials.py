"""Connector credential validation helpers for workspace routes."""

from connectors.registry import ConnectorRegistry
from routes.api.deps import get_workspace_service
from services.embedded.jira_metrics import test_jira_connection


def get_workspace_credential_status(workspace_id):
    """Get credential configuration status for workspace"""
    try:
        workspace = get_workspace_service().get_workspace(workspace_id)
        if "error" in workspace:
            return {"error": "Workspace not found"}

        assignments = get_workspace_service().get_workspace_assignments(workspace_id)
        status = {
            "workspace_id": workspace_id,
            "connectors": {
                "github": {"configured": False, "assignments": []},
                "jira": {"configured": False, "assignments": []},
                "aws": {"configured": False, "assignments": []},
                "openai": {"configured": False, "assignments": []},
                "railway": {"configured": False, "assignments": []},
                "vercel": {"configured": False, "assignments": []},
                "azure": {"configured": False, "assignments": []},
            },
        }

        from services.security.secure_database import secure_db

        for assignment in assignments.get("assignments", []):
            assignment_id = assignment.get("id")
            configured = secure_db.list_assignment_credentials(workspace_id, assignment_id)
            for connector_type in ["github", "jira", "aws", "openai", "railway", "vercel", "azure"]:
                if configured.get(connector_type):
                    status["connectors"][connector_type]["configured"] = True
                    status["connectors"][connector_type]["assignments"].append(
                        {
                            "id": assignment_id,
                            "name": assignment.get("name", assignment_id),
                        }
                    )

        return status
    except Exception as e:
        return {"error": f"Failed to get credential status: {str(e)}"}


def basic_validate_credentials(connector_type, credentials):
    """Basic validation - just check required fields are present"""
    if connector_type == "github":
        required_fields = ["github_token"]
        missing = [field for field in required_fields if not credentials.get(field)]
        if missing:
            return {"valid": False, "error": f"Missing required fields: {', '.join(missing)}"}

    elif connector_type == "jira":
        required_fields = ["jira_url", "jira_email", "jira_token"]
        missing = [field for field in required_fields if not credentials.get(field)]
        if missing:
            return {"valid": False, "error": f"Missing required fields: {', '.join(missing)}"}

    elif connector_type == "aws":
        required_fields = ["aws_access_key", "aws_secret_key"]
        missing = [field for field in required_fields if not credentials.get(field)]
        if missing:
            return {"valid": False, "error": f"Missing required fields: {', '.join(missing)}"}

    elif connector_type == "openai":
        required_fields = ["openai_api_key"]
        missing = [field for field in required_fields if not credentials.get(field)]
        if missing:
            return {"valid": False, "error": f"Missing required fields: {', '.join(missing)}"}

    elif connector_type == "railway":
        required_fields = ["railway_token", "railway_project_id"]
        missing = [field for field in required_fields if not credentials.get(field)]
        if missing:
            return {"valid": False, "error": f"Missing required fields: {', '.join(missing)}"}

    elif connector_type == "vercel":
        required_fields = ["vercel_token", "vercel_project_id"]
        missing = [field for field in required_fields if not credentials.get(field)]
        if missing:
            return {"valid": False, "error": f"Missing required fields: {', '.join(missing)}"}

    elif connector_type == "azure":
        required_fields = [
            "azure_tenant_id",
            "azure_client_id",
            "azure_client_secret",
            "azure_subscription_id",
        ]
        missing = [field for field in required_fields if not credentials.get(field)]
        if missing:
            return {"valid": False, "error": f"Missing required fields: {', '.join(missing)}"}
    else:
        return {"valid": False, "error": f"Unknown connector type: {connector_type}"}

    return {"valid": True, "message": "Basic validation passed"}


def validate_connector_credentials(connector_type, credentials):
    """Validate connector credentials by attempting to use them"""
    try:
        if connector_type == "github":
            return _validate_github_credentials(credentials)
        elif connector_type == "jira":
            return _validate_jira_credentials(credentials)
        elif connector_type == "aws":
            return _validate_aws_credentials(credentials)
        elif connector_type == "openai":
            return _validate_openai_credentials(credentials)
        elif connector_type == "railway":
            return _validate_railway_credentials(credentials)
        elif connector_type == "vercel":
            return _validate_vercel_credentials(credentials)
        elif connector_type == "azure":
            return _validate_azure_credentials(credentials)
        else:
            return {"valid": False, "error": f"Unknown connector type: {connector_type}"}
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"}


def _validate_github_credentials(credentials):
    """Test GitHub credentials"""
    token = credentials.get("github_token")
    if not token:
        return {"valid": False, "error": "GitHub token is required"}

    try:
        import requests

        headers = {"Authorization": f"token {token}", "User-Agent": "CTO-Dashboard"}
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)

        if response.status_code == 200:
            user_data = response.json()
            return {
                "valid": True,
                "user": user_data.get("login"),
                "name": user_data.get("name"),
                "scopes": response.headers.get("x-oauth-scopes", "").split(", ")
                if response.headers.get("x-oauth-scopes")
                else [],
            }
        elif response.status_code == 401:
            return {"valid": False, "error": "Invalid GitHub token or expired"}
        elif response.status_code == 403:
            return {"valid": False, "error": "GitHub token lacks required permissions"}
        else:
            return {"valid": False, "error": f"GitHub API error: {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {
            "valid": False,
            "error": "Cannot connect to GitHub API - check internet connection",
        }
    except requests.exceptions.Timeout:
        return {"valid": False, "error": "GitHub API request timed out"}
    except Exception as e:
        return {"valid": False, "error": f"GitHub connection failed: {str(e)}"}


def _validate_jira_credentials(credentials):
    """Test Jira credentials"""
    return test_jira_connection(
        credentials.get("jira_url"),
        credentials.get("jira_email"),
        credentials.get("jira_token"),
    )


def _validate_aws_credentials(credentials):
    """Test AWS credentials"""
    access_key = credentials.get("aws_access_key")
    secret_key = credentials.get("aws_secret_key")
    region = credentials.get("aws_region", "us-east-1")

    if not access_key:
        return {"valid": False, "error": "AWS access key is required"}
    if not secret_key:
        return {"valid": False, "error": "AWS secret key is required"}

    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        # Test credentials by calling STS get-caller-identity
        client = boto3.client(
            "sts",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

        response = client.get_caller_identity()
        return {
            "valid": True,
            "account": response.get("Account"),
            "arn": response.get("Arn"),
            "userId": response.get("UserId"),
            "region": region,
        }
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "InvalidUserID.NotFound":
            return {"valid": False, "error": "Invalid AWS access key"}
        elif error_code == "SignatureDoesNotMatch":
            return {"valid": False, "error": "Invalid AWS secret key"}
        elif error_code == "TokenRefreshRequired":
            return {"valid": False, "error": "AWS credentials expired"}
        else:
            return {"valid": False, "error": f"AWS authentication failed: {error_code}"}
    except NoCredentialsError:
        return {"valid": False, "error": "AWS credentials not provided correctly"}
    except Exception as e:
        return {"valid": False, "error": f"AWS connection failed: {str(e)}"}


def _validate_openai_credentials(credentials):
    """Test OpenAI credentials using modular connector"""
    try:
        return ConnectorRegistry.validate_credentials("openai", credentials)
    except Exception as e:
        return {"valid": False, "error": f"OpenAI validation failed: {str(e)}"}


def _validate_railway_credentials(credentials):
    """Test Railway API token via GraphQL me query."""
    token = credentials.get("railway_token")
    if not token:
        return {"valid": False, "error": "Railway token is required"}

    try:
        import requests

        response = requests.post(
            "https://backboard.railway.app/graphql",
            json={"query": "query { me { id email } }"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 401:
            return {"valid": False, "error": "Invalid Railway token"}
        if response.status_code != 200:
            return {"valid": False, "error": f"Railway API error: {response.status_code}"}
        data = response.json()
        if data.get("errors"):
            return {"valid": False, "error": "Railway token validation failed"}
        me = (data.get("data") or {}).get("me") or {}
        if not me.get("id"):
            return {"valid": False, "error": "Railway token could not be verified"}
        return {"valid": True, "user_id": me.get("id"), "email": me.get("email")}
    except requests.exceptions.Timeout:
        return {"valid": False, "error": "Railway API request timed out"}
    except Exception as e:
        return {"valid": False, "error": f"Railway connection failed: {str(e)}"}


def _validate_vercel_credentials(credentials):
    """Test Vercel API token."""
    token = credentials.get("vercel_token")
    if not token:
        return {"valid": False, "error": "Vercel token is required"}

    try:
        import requests

        headers = {"Authorization": f"Bearer {token}"}
        team_id = credentials.get("vercel_team_id")
        url = "https://api.vercel.com/v2/user"
        if team_id:
            url = f"https://api.vercel.com/v2/teams/{team_id}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 401:
            return {"valid": False, "error": "Invalid Vercel token"}
        if response.status_code == 404 and team_id:
            return {"valid": False, "error": "Vercel team not found"}
        if response.status_code != 200:
            return {"valid": False, "error": f"Vercel API error: {response.status_code}"}
        payload = response.json()
        if team_id:
            team = payload
            return {"valid": True, "team_id": team.get("id"), "team_name": team.get("name")}
        user = payload.get("user") or payload
        return {"valid": True, "username": user.get("username"), "email": user.get("email")}
    except requests.exceptions.Timeout:
        return {"valid": False, "error": "Vercel API request timed out"}
    except Exception as e:
        return {"valid": False, "error": f"Vercel connection failed: {str(e)}"}


def _validate_azure_credentials(credentials):
    """Test Azure service principal credentials."""
    from services.embedded.azure_metrics import AZURE_MGMT_BASE, fetch_azure_access_token

    tenant_id = credentials.get("azure_tenant_id")
    client_id = credentials.get("azure_client_id")
    client_secret = credentials.get("azure_client_secret")
    subscription_id = credentials.get("azure_subscription_id")

    token, auth_error = fetch_azure_access_token(tenant_id, client_id, client_secret)
    if auth_error:
        return {"valid": False, "error": auth_error}

    try:
        import requests

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{AZURE_MGMT_BASE}/subscriptions/{subscription_id}?api-version=2020-01-01",
            headers=headers,
            timeout=15,
        )
        if response.status_code == 404:
            return {"valid": False, "error": "Azure subscription not found"}
        if response.status_code == 403:
            return {
                "valid": False,
                "error": "Azure credentials valid but subscription access denied",
            }
        if response.status_code != 200:
            return {"valid": False, "error": f"Azure API error: {response.status_code}"}
        sub = response.json()
        return {
            "valid": True,
            "subscription_id": sub.get("subscriptionId"),
            "display_name": sub.get("displayName"),
            "state": sub.get("state"),
        }
    except requests.exceptions.Timeout:
        return {"valid": False, "error": "Azure API request timed out"}
    except Exception as e:
        return {"valid": False, "error": f"Azure connection failed: {str(e)}"}
