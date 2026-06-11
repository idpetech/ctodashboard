"""
Evaluation context — normalized inputs for signal rules.

Built from assignment rows plus optional delivery/connector metric overlays.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.portfolio_service import budget_variance


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_active(assignment: Dict[str, Any]) -> bool:
    return (assignment.get("status") or "active") == "active"


def _project_id(assignment: Dict[str, Any]) -> str:
    return str(assignment.get("id") or assignment.get("assignment_id") or "")


def _project_name(assignment: Dict[str, Any]) -> str:
    pid = _project_id(assignment)
    return str(assignment.get("name") or pid or "unknown")


def _owner(assignment: Dict[str, Any]) -> Optional[str]:
    for key in ("owner", "project_owner", "lead", "owner_name"):
        val = assignment.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return None


def _enabled_connectors(assignment: Dict[str, Any]) -> List[str]:
    cfg = assignment.get("metrics_config") or {}
    enabled = []
    for name, section in cfg.items():
        if isinstance(section, dict) and section.get("enabled"):
            enabled.append(str(name))
    return enabled


@dataclass
class ProjectContext:
    project_id: str
    project_name: str
    status: str
    monthly_burn: Optional[float]
    target_burn: Optional[float]
    variance_pct: Optional[float]
    variance_amount: Optional[float]
    team_size: Optional[int]
    owner: Optional[str]
    previous_monthly_burn: Optional[float]
    enabled_connectors: List[str]
    commits_last_7_days: Optional[int] = None
    commits_last_14_days: Optional[int] = None
    commits_prior_7_days: Optional[int] = None
    jira_issues_last_7_days: Optional[int] = None
    connector_failures: List[str] = field(default_factory=list)
    connector_last_success_at: Optional[datetime] = None
    github_enabled: bool = False
    jira_enabled: bool = False
    blocked_work_count: Optional[int] = None
    blocked_work_prior_count: Optional[int] = None
    open_pull_requests: Optional[int] = None
    pr_review_wait_hours: Optional[float] = None
    issue_reopen_count_7d: Optional[int] = None
    issue_closed_count_7d: Optional[int] = None
    build_failure_count_7d: Optional[int] = None
    build_failure_count_prior_7d: Optional[int] = None
    release_count_7d: Optional[int] = None
    release_failure_count_7d: Optional[int] = None
    dependency_count: Optional[int] = None
    top_dependency_share_pct: Optional[float] = None


@dataclass
class SignalEvaluationContext:
    evaluated_at: datetime
    projects: List[ProjectContext]
    portfolio_team_total: int = 0


def build_context_from_assignments(
    assignments: List[Dict[str, Any]],
    *,
    delivery_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
    connector_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
    evaluated_at: Optional[datetime] = None,
) -> SignalEvaluationContext:
    """
    Build evaluation context from assignment dicts.

    delivery_metrics: {project_id: {commits_last_7_days, commits_last_14_days,
                      commits_prior_7_days, jira_issues_last_7_days}}
    connector_metrics: {project_id: {failures: [...], last_success_at: ISO str}}
    """
    evaluated_at = evaluated_at or datetime.utcnow()
    delivery_metrics = delivery_metrics or {}
    connector_metrics = connector_metrics or {}

    budget = budget_variance(assignments or [])
    variance_by_id = {row["assignment_id"]: row for row in budget.get("assignments", [])}

    projects: List[ProjectContext] = []
    team_total = 0

    for assignment in assignments or []:
        if not _is_active(assignment):
            continue
        pid = _project_id(assignment)
        if not pid:
            continue

        row = variance_by_id.get(pid)
        team_raw = _to_float(assignment.get("team_size"))
        team_size = int(team_raw) if team_raw is not None else None
        if team_size:
            team_total += team_size

        delivery = delivery_metrics.get(pid, {})
        connector = connector_metrics.get(pid, {})
        enabled = _enabled_connectors(assignment)

        last_success = connector.get("last_success_at")
        last_success_dt = None
        if last_success:
            try:
                last_success_dt = datetime.fromisoformat(str(last_success).replace("Z", "+00:00"))
                if last_success_dt.tzinfo:
                    last_success_dt = last_success_dt.replace(tzinfo=None)
            except (TypeError, ValueError):
                last_success_dt = None

        projects.append(
            ProjectContext(
                project_id=pid,
                project_name=_project_name(assignment),
                status=str(assignment.get("status") or "active"),
                monthly_burn=_to_float(assignment.get("monthly_burn_rate")),
                target_burn=_to_float(assignment.get("target_monthly_burn")),
                variance_pct=row["variance_pct"] if row else None,
                variance_amount=row["variance"] if row else None,
                team_size=team_size,
                owner=_owner(assignment),
                previous_monthly_burn=_to_float(assignment.get("previous_monthly_burn")),
                enabled_connectors=enabled,
                commits_last_7_days=_optional_int(delivery.get("commits_last_7_days")),
                commits_last_14_days=_optional_int(delivery.get("commits_last_14_days")),
                commits_prior_7_days=_optional_int(delivery.get("commits_prior_7_days")),
                jira_issues_last_7_days=_optional_int(delivery.get("jira_issues_last_7_days")),
                connector_failures=list(connector.get("failures") or []),
                connector_last_success_at=last_success_dt,
                github_enabled="github" in enabled,
                jira_enabled="jira" in enabled,
                blocked_work_count=_optional_int(delivery.get("blocked_work_count")),
                blocked_work_prior_count=_optional_int(delivery.get("blocked_work_prior_count")),
                open_pull_requests=_optional_int(delivery.get("open_pull_requests")),
                pr_review_wait_hours=_to_float(delivery.get("pr_review_wait_hours")),
                issue_reopen_count_7d=_optional_int(delivery.get("issue_reopen_count_7d")),
                issue_closed_count_7d=_optional_int(delivery.get("issue_closed_count_7d")),
                build_failure_count_7d=_optional_int(delivery.get("build_failure_count_7d")),
                build_failure_count_prior_7d=_optional_int(
                    delivery.get("build_failure_count_prior_7d")
                ),
                release_count_7d=_optional_int(delivery.get("release_count_7d")),
                release_failure_count_7d=_optional_int(delivery.get("release_failure_count_7d")),
                dependency_count=_optional_int(delivery.get("dependency_count")),
                top_dependency_share_pct=_to_float(delivery.get("top_dependency_share_pct")),
            )
        )

    return SignalEvaluationContext(
        evaluated_at=evaluated_at,
        projects=projects,
        portfolio_team_total=team_total,
    )


def _optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
