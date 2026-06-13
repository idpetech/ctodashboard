"""
Workspace Validation Framework - Phase 0 Foundation
Pure addition for ensuring system integrity during workspace migration

This validation framework ensures existing functionality remains intact
throughout the workspace implementation phases.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests


class SystemValidator:
    """
    Validation framework to ensure workspace changes don't break existing functionality.

    Phase 0: Foundation validation for legacy system
    Future phases will add workspace-specific validations
    """

    def __init__(self):
        self.assignments_dir = Path("config/assignments")
        self.validation_results = {}

    def validate_all(self) -> Dict[str, Any]:
        """Run complete system validation suite"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "pass",
            "validations": {},
        }

        # Run all validation checks
        validations = [
            ("assignment_files", self.validate_assignment_files),
            ("assignment_service", self.validate_assignment_service_compatibility),
            ("api_endpoints", self.validate_api_endpoints),
            ("github_service", self.validate_github_service),
            ("metrics_config", self.validate_metrics_configurations),
            ("environment_vars", self.validate_environment_variables),
        ]

        for validation_name, validation_func in validations:
            try:
                results["validations"][validation_name] = validation_func()
            except Exception as e:
                results["validations"][validation_name] = {
                    "status": "error",
                    "message": f"Validation failed with exception: {str(e)}",
                    "details": {},
                }
                results["overall_status"] = "fail"

        # Check if any validations failed
        for validation_result in results["validations"].values():
            if validation_result.get("status") != "pass":
                results["overall_status"] = "fail"
                break

        return results

    def validate_assignment_files(self) -> Dict[str, Any]:
        """Validate assignment JSON files are readable and well-formed"""
        result = {
            "status": "pass",
            "message": "Assignment files validation",
            "details": {"files_checked": 0, "files_valid": 0, "files_with_errors": 0, "errors": []},
        }

        if not self.assignments_dir.exists():
            result["status"] = "fail"
            result["message"] = f"Assignments directory {self.assignments_dir} does not exist"
            return result

        assignment_files = list(self.assignments_dir.glob("*.json"))
        result["details"]["files_checked"] = len(assignment_files)

        for assignment_file in assignment_files:
            try:
                with open(assignment_file, "r") as f:
                    assignment_data = json.load(f)

                # Validate required fields
                required_fields = ["id", "name", "status"]
                missing_fields = [
                    field for field in required_fields if field not in assignment_data
                ]

                if missing_fields:
                    result["details"]["files_with_errors"] += 1
                    result["details"]["errors"].append(
                        f"File {assignment_file.name}: Missing required fields {missing_fields}"
                    )
                    result["status"] = "fail"
                else:
                    result["details"]["files_valid"] += 1

            except json.JSONDecodeError as e:
                result["details"]["files_with_errors"] += 1
                result["details"]["errors"].append(
                    f"File {assignment_file.name}: Invalid JSON - {str(e)}"
                )
                result["status"] = "fail"
            except Exception as e:
                result["details"]["files_with_errors"] += 1
                result["details"]["errors"].append(
                    f"File {assignment_file.name}: Error reading file - {str(e)}"
                )
                result["status"] = "fail"

        return result

    def validate_assignment_service_compatibility(self) -> Dict[str, Any]:
        """Validate that AssignmentService can still load assignments"""
        result = {
            "status": "pass",
            "message": "AssignmentService compatibility validation",
            "details": {"service_importable": False, "assignments_loadable": 0, "load_errors": []},
        }

        try:
            # Test import
            from services.assignment_service import AssignmentService

            result["details"]["service_importable"] = True

            # Test assignment loading
            assignment_service = AssignmentService()
            assignments = assignment_service.get_all_assignments()
            result["details"]["assignments_loadable"] = len(assignments)

            # Test individual assignment loading
            for assignment in assignments:
                assignment_id = assignment.get("id")
                if assignment_id:
                    try:
                        individual_assignment = assignment_service.get_assignment(assignment_id)
                        if not individual_assignment:
                            result["details"]["load_errors"].append(
                                f"Assignment {assignment_id} returned None from get_assignment()"
                            )
                            result["status"] = "fail"
                    except Exception as e:
                        result["details"]["load_errors"].append(
                            f"Error loading assignment {assignment_id}: {str(e)}"
                        )
                        result["status"] = "fail"

        except ImportError as e:
            result["status"] = "fail"
            result["message"] = f"Cannot import AssignmentService: {str(e)}"
        except Exception as e:
            result["status"] = "fail"
            result["message"] = f"AssignmentService validation failed: {str(e)}"

        return result

    def validate_api_endpoints(self) -> Dict[str, Any]:
        """Validate key API endpoints are accessible (if server is running)"""
        result = {
            "status": "pass",
            "message": "API endpoints validation",
            "details": {
                "server_running": False,
                "endpoints_tested": 0,
                "endpoints_working": 0,
                "endpoint_results": {},
            },
        }

        # Test if server is running on default port
        try:
            base_url = "http://localhost:5000"
            test_endpoints = ["/health", "/api/assignments", "/api/feature-flags"]

            # Quick health check to see if server is running
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                result["details"]["server_running"] = True

                # Test other endpoints
                for endpoint in test_endpoints:
                    try:
                        resp = requests.get(f"{base_url}{endpoint}", timeout=2)
                        result["details"]["endpoints_tested"] += 1
                        result["details"]["endpoint_results"][endpoint] = {
                            "status_code": resp.status_code,
                            "success": resp.status_code < 400,
                        }
                        if resp.status_code < 400:
                            result["details"]["endpoints_working"] += 1
                    except Exception as e:
                        result["details"]["endpoint_results"][endpoint] = {
                            "error": str(e),
                            "success": False,
                        }

            else:
                result["details"]["server_running"] = False
                result["message"] = "Server not running or health check failed"

        except Exception as e:
            result["details"]["server_running"] = False
            result["message"] = f"Cannot connect to server: {str(e)}"

        return result

    def validate_github_service(self) -> Dict[str, Any]:
        """Validate GitHub service functionality"""
        result = {
            "status": "pass",
            "message": "GitHub service validation",
            "details": {
                "service_importable": False,
                "token_configured": False,
                "token_valid": False,
                "validation_details": {},
            },
        }

        try:
            from services.embedded.github_metrics import EmbeddedGitHubMetrics

            result["details"]["service_importable"] = True

            github_service = EmbeddedGitHubMetrics()

            # Check token configuration
            if github_service.token and github_service.token != "test_token":
                result["details"]["token_configured"] = True

                # Validate token
                validation_result = github_service.validate_token()
                result["details"]["validation_details"] = validation_result
                result["details"]["token_valid"] = validation_result.get("valid", False)
            else:
                result["details"]["token_configured"] = False
                result["details"]["validation_details"] = {"message": "No valid token configured"}

        except ImportError as e:
            result["status"] = "fail"
            result["message"] = f"Cannot import GitHub service: {str(e)}"
        except Exception as e:
            result["status"] = "fail"
            result["message"] = f"GitHub service validation failed: {str(e)}"

        return result

    def validate_metrics_configurations(self) -> Dict[str, Any]:
        """Validate metrics configurations in assignments"""
        result = {
            "status": "pass",
            "message": "Metrics configurations validation",
            "details": {
                "assignments_with_metrics": 0,
                "connector_types_found": set(),
                "configuration_issues": [],
            },
        }

        try:
            from services.assignment_service import AssignmentService

            assignment_service = AssignmentService()
            assignments = assignment_service.get_all_assignments()

            for assignment in assignments:
                assignment_id = assignment.get("id", "unknown")
                metrics_config = assignment.get("metrics_config", {})

                if metrics_config:
                    result["details"]["assignments_with_metrics"] += 1

                    for connector_type, config in metrics_config.items():
                        result["details"]["connector_types_found"].add(connector_type)

                        # Validate connector configuration
                        if not isinstance(config, dict):
                            result["details"]["configuration_issues"].append(
                                f"Assignment {assignment_id}: {connector_type} config is not a dictionary"
                            )
                            result["status"] = "fail"
                            continue

                        if config.get("enabled", False):
                            # Check required fields for each connector type
                            required_fields = self._get_required_fields_for_connector(
                                connector_type
                            )
                            missing_fields = [
                                field for field in required_fields if field not in config
                            ]

                            if missing_fields:
                                result["details"]["configuration_issues"].append(
                                    f"Assignment {assignment_id}: {connector_type} missing required fields {missing_fields}"
                                )
                                result["status"] = "fail"

            # Convert set to list for JSON serialization
            result["details"]["connector_types_found"] = list(
                result["details"]["connector_types_found"]
            )

        except Exception as e:
            result["status"] = "fail"
            result["message"] = f"Metrics configuration validation failed: {str(e)}"

        return result

    def validate_environment_variables(self) -> Dict[str, Any]:
        """Validate required environment variables"""
        result = {
            "status": "pass",
            "message": "Environment variables validation",
            "details": {
                "required_vars_set": 0,
                "optional_vars_set": 0,
                "missing_required": [],
                "missing_optional": [],
            },
        }

        # Required variables for basic functionality
        required_vars = []  # None strictly required for basic operation

        # Optional but commonly used variables
        optional_vars = [
            "GITHUB_TOKEN",
            "JIRA_TOKEN",
            "JIRA_URL",
            "JIRA_EMAIL",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "RAILWAY_TOKEN",
            "OPENAI_API_KEY",
        ]

        # Check required variables
        for var in required_vars:
            if os.getenv(var):
                result["details"]["required_vars_set"] += 1
            else:
                result["details"]["missing_required"].append(var)
                result["status"] = "fail"

        # Check optional variables
        for var in optional_vars:
            if os.getenv(var):
                result["details"]["optional_vars_set"] += 1
            else:
                result["details"]["missing_optional"].append(var)

        return result

    def _get_required_fields_for_connector(self, connector_type: str) -> List[str]:
        """Get required fields for each connector type"""
        required_fields_map = {
            "github": ["org", "repos"],
            "jira": ["project_key"],
            "aws": [],  # Uses environment variables
            "railway": ["project_id"],
            "vercel": ["project_id"],
            "azure": ["subscription_id"],
            "openai": [],  # Uses environment variables
        }

        return required_fields_map.get(connector_type, [])

    def generate_validation_report(self) -> str:
        """Generate a human-readable validation report"""
        results = self.validate_all()

        report = []
        report.append("=== SYSTEM VALIDATION REPORT ===")
        report.append(f"Timestamp: {results['timestamp']}")
        report.append(f"Overall Status: {results['overall_status'].upper()}")
        report.append("")

        for validation_name, validation_result in results["validations"].items():
            status = validation_result.get("status", "unknown").upper()
            message = validation_result.get("message", "No message")

            report.append(f"[{status}] {validation_name.replace('_', ' ').title()}")
            report.append(f"  {message}")

            # Add details if validation failed
            if status != "PASS":
                details = validation_result.get("details", {})
                for key, value in details.items():
                    if isinstance(value, list) and value:
                        report.append(f"  {key}:")
                        for item in value:
                            report.append(f"    - {item}")
                    elif value and not isinstance(value, (dict, list)):
                        report.append(f"  {key}: {value}")

            report.append("")

        return "\n".join(report)
