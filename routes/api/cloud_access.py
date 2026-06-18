"""Cloud Access onboarding API (AWS cross-account role first)."""

from __future__ import annotations

import os
from pathlib import Path

from flask import jsonify, request, send_file

from routes.api.deps import get_require_workspace_access
from services.cloud_access.aws_sts_broker import suggested_external_id, validate_assumed_role
from services.cloud_access.flags import (
    aws_cross_account_role_enabled,
    aws_role_connector_ui_enabled,
    cloud_access_capabilities,
)


def _template_path() -> Path:
    return Path(__file__).resolve().parents[2] / "cloud" / "aws" / "ctolens-readonly-role.yaml"


def register_cloud_access_routes(app):
    """Register cloud access onboarding routes (feature-flagged)."""

    @app.route("/api/cloud-access/capabilities", methods=["GET"])
    def cloud_access_caps():
        return jsonify(cloud_access_capabilities())

    @app.route("/api/workspaces/<workspace_id>/cloud-access/aws/onboarding", methods=["GET"])
    @get_require_workspace_access()
    def aws_onboarding_info(workspace_id):
        if not aws_cross_account_role_enabled() or not aws_role_connector_ui_enabled():
            return jsonify({"error": "AWS cross-account role onboarding is disabled"}), 403

        assignment_id = request.args.get("assignment_id", "").strip()
        if not assignment_id:
            return jsonify({"error": "assignment_id is required"}), 400

        ctolens_account = (os.getenv("CTOLENS_AWS_ACCOUNT_ID") or "").strip()
        if not ctolens_account:
            return jsonify({"error": "CTOLENS_AWS_ACCOUNT_ID is not configured on this deployment"}), 503

        external_id = suggested_external_id(workspace_id, assignment_id)
        return jsonify(
            {
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "ctolens_aws_account_id": ctolens_account,
                "external_id": external_id,
                "role_name": "CTOLensReadOnlyRole",
                "cloudformation_template_url": "/api/cloud-access/aws/cloudformation-template",
                "instructions": [
                    "Deploy the CloudFormation stack in your AWS account",
                    "Use the External ID and CTOLens Account ID shown here as stack parameters",
                    "Copy the Role ARN and Account ID stack outputs into CTOLens",
                ],
            }
        )

    @app.route("/api/cloud-access/aws/cloudformation-template", methods=["GET"])
    def aws_cloudformation_template():
        if not aws_cross_account_role_enabled():
            return jsonify({"error": "AWS cross-account role onboarding is disabled"}), 403
        path = _template_path()
        if not path.is_file():
            return jsonify({"error": "CloudFormation template not found"}), 404
        return send_file(
            path,
            mimetype="text/yaml",
            as_attachment=True,
            download_name="ctolens-readonly-role.yaml",
        )

    @app.route("/api/workspaces/<workspace_id>/cloud-access/aws/validate", methods=["POST"])
    @get_require_workspace_access()
    def aws_validate_role(workspace_id):
        if not aws_cross_account_role_enabled():
            return jsonify({"error": "AWS cross-account role onboarding is disabled"}), 403

        data = request.get_json() or {}
        assignment_id = (data.get("assignment_id") or "").strip()
        credentials = data.get("credentials") or {}
        if not assignment_id:
            return jsonify({"error": "assignment_id is required"}), 400

        result = validate_assumed_role(
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            stored=credentials,
        )
        return jsonify(result)
