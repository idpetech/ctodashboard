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
            },
        }

        from services.security.secure_database import secure_db

        for assignment in assignments.get("assignments", []):
            assignment_id = assignment.get("id")
            configured = secure_db.list_assignment_credentials(workspace_id, assignment_id)
            for connector_type in ["github", "jira", "aws", "openai"]:
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
