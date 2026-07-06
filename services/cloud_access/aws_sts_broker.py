"""AWS STS AssumeRole broker for customer cross-account IAM roles."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from services.cloud_access.base import CloudAccessBroker
from services.cloud_access.session import CloudAccessSession

logger = logging.getLogger(__name__)

AWS_ASSUME_ROLE_AUTH = "aws_assume_role"
AWS_ACCESS_KEY_AUTH = "aws_access_key"

_SESSION_CACHE: Dict[str, Tuple[CloudAccessSession, float]] = {}


class AWSAssumeRoleError(Exception):
    """Failed to assume customer IAM role."""


def aws_auth_method(stored: Dict[str, Any]) -> str:
    explicit = (stored.get("auth_method") or "").strip().lower()
    if explicit in (AWS_ASSUME_ROLE_AUTH, "assume_role"):
        return AWS_ASSUME_ROLE_AUTH
    if stored.get("aws_role_arn"):
        return AWS_ASSUME_ROLE_AUTH
    return AWS_ACCESS_KEY_AUTH


def aws_role_config_ready(stored: Dict[str, Any]) -> bool:
    return bool(
        stored.get("aws_role_arn")
        and stored.get("aws_account_id")
        and (stored.get("aws_external_id") or stored.get("external_id"))
    )


def aws_access_key_config_ready(stored: Dict[str, Any]) -> bool:
    return bool(
        (stored.get("aws_access_key") or stored.get("access_key"))
        and (stored.get("aws_secret_key") or stored.get("secret_key"))
    )


def aws_credentials_ready(stored: Dict[str, Any]) -> bool:
    if aws_auth_method(stored) == AWS_ASSUME_ROLE_AUTH:
        return aws_role_config_ready(stored)
    return aws_access_key_config_ready(stored)


def suggested_external_id(workspace_id: str, assignment_id: str) -> str:
    prefix = (os.getenv("CTOLENS_AWS_EXTERNAL_ID_PREFIX") or "ctolens").strip()
    return f"{prefix}-{workspace_id}-{assignment_id}"


def _platform_sts_client(region: str):
    """STS client using CTOLens platform credentials (not customer keys)."""
    key = os.getenv("CTOLENS_AWS_ACCESS_KEY_ID")
    secret = os.getenv("CTOLENS_AWS_SECRET_ACCESS_KEY")
    if key and secret:
        return boto3.client(
            "sts",
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name=region,
        )
    return boto3.client("sts", region_name=region)


def _cache_key(workspace_id: str, assignment_id: str, role_arn: str) -> str:
    return f"{workspace_id}:{assignment_id}:{role_arn}"


class AWSStsBroker(CloudAccessBroker):
    """Assume customer IAM roles via STS; cache sessions in memory only."""

    provider = "aws"

    def get_session(
        self,
        *,
        workspace_id: str,
        assignment_id: str,
        stored: Dict[str, Any],
        region: Optional[str] = None,
    ) -> CloudAccessSession:
        role_arn = (stored.get("aws_role_arn") or "").strip()
        external_id = (stored.get("aws_external_id") or stored.get("external_id") or "").strip()
        account_id = (stored.get("aws_account_id") or "").strip()
        aws_region = region or stored.get("aws_region") or "us-east-1"

        if not role_arn:
            raise AWSAssumeRoleError("aws_role_arn is required")
        if not external_id:
            raise AWSAssumeRoleError("aws_external_id is required for cross-account AssumeRole")

        cache_key = _cache_key(workspace_id, assignment_id, role_arn)
        cached = _SESSION_CACHE.get(cache_key)
        if cached and cached[1] > time.time() + 60:
            return cached[0]

        sts = _platform_sts_client(aws_region)
        try:
            response = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=f"ctolens-{workspace_id[:8]}-{assignment_id[:8]}",
                ExternalId=external_id,
                DurationSeconds=3600,
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            logger.warning(
                "AWS AssumeRole failed workspace=%s assignment=%s role=%s code=%s",
                workspace_id,
                assignment_id,
                role_arn,
                code,
            )
            raise AWSAssumeRoleError(f"AssumeRole failed: {code}") from exc

        creds = response.get("Credentials") or {}
        access_key = creds.get("AccessKeyId")
        secret_key = creds.get("SecretAccessKey")
        session_token = creds.get("SessionToken")
        expiration = creds.get("Expiration")
        if not access_key or not secret_key or not session_token:
            raise AWSAssumeRoleError("AssumeRole returned incomplete credentials")

        expiry_ts = time.time() + 3300
        if expiration is not None:
            try:
                expiry_ts = expiration.timestamp()
            except AttributeError:
                pass

        session = CloudAccessSession(
            provider="aws",
            access_key_id=access_key,
            secret_access_key=secret_key,
            session_token=session_token,
            region=aws_region,
            expires_at=expiry_ts,
            auth_method=AWS_ASSUME_ROLE_AUTH,
            account_id=account_id or None,
            role_arn=role_arn,
        )
        _SESSION_CACHE[cache_key] = (session, expiry_ts)
        logger.info(
            "AWS AssumeRole succeeded workspace=%s assignment=%s account=%s role=%s",
            workspace_id,
            assignment_id,
            account_id or "unknown",
            role_arn,
        )
        return session


def validate_assumed_role(
    *,
    workspace_id: str,
    assignment_id: str,
    stored: Dict[str, Any],
) -> Dict[str, Any]:
    """Test AssumeRole and return caller identity (no token persistence)."""
    try:
        session = AWSStsBroker().get_session(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            stored=stored,
        )
        sts = boto3.client(
            "sts",
            aws_access_key_id=session.access_key_id,
            aws_secret_access_key=session.secret_access_key,
            aws_session_token=session.session_token,
            region_name=session.region,
        )
        identity = sts.get_caller_identity()
        return {
            "valid": True,
            "auth_method": AWS_ASSUME_ROLE_AUTH,
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "userId": identity.get("UserId"),
            "region": session.region,
            "role_arn": session.role_arn,
        }
    except AWSAssumeRoleError as exc:
        return {"valid": False, "error": str(exc)}
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        return {"valid": False, "error": f"AWS API error after AssumeRole: {code}"}
    except Exception as exc:
        return {"valid": False, "error": f"AWS role validation failed: {str(exc)}"}


_broker: Optional[AWSStsBroker] = None


def get_aws_sts_broker() -> AWSStsBroker:
    global _broker
    if _broker is None:
        _broker = AWSStsBroker()
    return _broker
