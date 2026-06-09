"""
Signal rule evaluators — one function per SignalType.

Each evaluator returns zero or one Signal. Descriptions are factual only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from services.signals.config import rule_confidence, rule_enabled
from services.signals.context import ProjectContext, SignalEvaluationContext
from services.signals.models import (
    Signal,
    SignalCategory,
    SignalSeverity,
    SignalType,
    build_signal,
)
from services.signals.opportunity_evaluators import (
    OPPORTUNITY_EVALUATORS,
    evaluate_blocked_work_increase,
    evaluate_build_failure_trend,
    evaluate_dependency_concentration,
    evaluate_high_performing_project,
    evaluate_high_reopen_rate,
    evaluate_high_service_coupling,
    evaluate_low_throughput_project,
    evaluate_momentum_acceleration,
    evaluate_pr_review_bottleneck,
    evaluate_release_instability,
    evaluate_slow_delivery_trend,
    evaluate_stalled_project,
    evaluate_tech_debt_accumulation,
    evaluate_under_budget,
    evaluate_unused_capacity,
)

Evaluator = Callable[[SignalEvaluationContext, ProjectContext, Dict[str, Dict[str, Any]]], Optional[Signal]]


def _emit(
    project: ProjectContext,
    signal_type: SignalType,
    *,
    severity: SignalSeverity,
    confidence: float,
    title: str,
    description: str,
    metric_value: Optional[float],
    threshold: Optional[float],
    generated_at: datetime,
) -> Signal:
    return build_signal(
        project,
        signal_type,
        severity=severity,
        confidence=confidence,
        title=title,
        description=description,
        metric_value=metric_value,
        threshold=threshold,
        generated_at=generated_at,
    )


def evaluate_over_budget(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.OVER_BUDGET.value):
        return None
    if project.variance_pct is None or project.variance_pct <= 0:
        return None

    cfg = rules[SignalType.OVER_BUDGET.value]
    critical_at = float(cfg["critical_threshold_pct"])
    warn_at = float(cfg["warn_threshold_pct"])
    pct = float(project.variance_pct)

    if pct >= critical_at:
        severity = SignalSeverity.CRITICAL
        threshold = critical_at
    elif pct >= warn_at:
        severity = SignalSeverity.WARNING
        threshold = warn_at
    else:
        return None

    return _emit(
        project,
        SignalType.OVER_BUDGET,
        severity=severity,
        confidence=rule_confidence(rules, SignalType.OVER_BUDGET.value),
        title="Over budget",
        description=(
            f"Monthly burn {project.monthly_burn or 0:.0f} exceeds target "
            f"{project.target_burn or 0:.0f} by {pct:.1f}%."
        ),
        metric_value=pct,
        threshold=threshold,
        generated_at=ctx.evaluated_at,
    )


def evaluate_cost_spike(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.COST_SPIKE.value):
        return None
    if project.monthly_burn is None or project.previous_monthly_burn is None:
        return None
    if project.previous_monthly_burn <= 0:
        return None

    spike_threshold = float(rules[SignalType.COST_SPIKE.value]["spike_threshold_pct"])
    change_pct = (
        (project.monthly_burn - project.previous_monthly_burn)
        / project.previous_monthly_burn
        * 100.0
    )
    if change_pct < spike_threshold:
        return None

    return _emit(
        project,
        SignalType.COST_SPIKE,
        severity=SignalSeverity.WARNING if change_pct < spike_threshold * 1.5 else SignalSeverity.CRITICAL,
        confidence=rule_confidence(rules, SignalType.COST_SPIKE.value),
        title="Cost spike",
        description=(
            f"Monthly burn increased from {project.previous_monthly_burn:.0f} "
            f"to {project.monthly_burn:.0f} ({change_pct:.1f}% change)."
        ),
        metric_value=round(change_pct, 2),
        threshold=spike_threshold,
        generated_at=ctx.evaluated_at,
    )


def evaluate_no_commits_7_days(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.NO_COMMITS_7_DAYS.value):
        return None
    if not project.github_enabled or project.commits_last_7_days is None:
        return None
    if project.commits_last_7_days > 0:
        return None

    return _emit(
        project,
        SignalType.NO_COMMITS_7_DAYS,
        severity=SignalSeverity.WARNING,
        confidence=rule_confidence(rules, SignalType.NO_COMMITS_7_DAYS.value),
        title="No commits in 7 days",
        description="GitHub reported 0 commits in the last 7 days.",
        metric_value=0.0,
        threshold=1.0,
        generated_at=ctx.evaluated_at,
    )


def evaluate_no_commits_14_days(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.NO_COMMITS_14_DAYS.value):
        return None
    if not project.github_enabled or project.commits_last_14_days is None:
        return None
    if project.commits_last_14_days > 0:
        return None

    return _emit(
        project,
        SignalType.NO_COMMITS_14_DAYS,
        severity=SignalSeverity.CRITICAL,
        confidence=rule_confidence(rules, SignalType.NO_COMMITS_14_DAYS.value),
        title="No commits in 14 days",
        description="GitHub reported 0 commits in the last 14 days.",
        metric_value=0.0,
        threshold=1.0,
        generated_at=ctx.evaluated_at,
    )


def evaluate_velocity_drop(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.VELOCITY_DROP.value):
        return None
    if not project.github_enabled:
        return None
    if project.commits_last_7_days is None or project.commits_prior_7_days is None:
        return None
    if project.commits_prior_7_days <= 0:
        return None

    drop_threshold = float(rules[SignalType.VELOCITY_DROP.value]["drop_threshold_pct"])
    drop_pct = (
        (project.commits_prior_7_days - project.commits_last_7_days)
        / project.commits_prior_7_days
        * 100.0
    )
    if drop_pct < drop_threshold:
        return None

    return _emit(
        project,
        SignalType.VELOCITY_DROP,
        severity=SignalSeverity.WARNING,
        confidence=rule_confidence(rules, SignalType.VELOCITY_DROP.value),
        title="Velocity drop",
        description=(
            f"Commits fell from {project.commits_prior_7_days} to "
            f"{project.commits_last_7_days} week-over-week ({drop_pct:.1f}% decrease)."
        ),
        metric_value=round(drop_pct, 2),
        threshold=drop_threshold,
        generated_at=ctx.evaluated_at,
    )


def evaluate_no_jira_activity(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.NO_JIRA_ACTIVITY.value):
        return None
    if not project.jira_enabled or project.jira_issues_last_7_days is None:
        return None
    if project.jira_issues_last_7_days > 0:
        return None

    lookback = int(rules[SignalType.NO_JIRA_ACTIVITY.value].get("lookback_days", 7))
    return _emit(
        project,
        SignalType.NO_JIRA_ACTIVITY,
        severity=SignalSeverity.WARNING,
        confidence=rule_confidence(rules, SignalType.NO_JIRA_ACTIVITY.value),
        title="No Jira activity",
        description=f"Jira reported 0 issue updates in the last {lookback} days.",
        metric_value=0.0,
        threshold=1.0,
        generated_at=ctx.evaluated_at,
    )


def evaluate_connector_failure(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.CONNECTOR_FAILURE.value):
        return None
    if not project.connector_failures:
        return None

    failures = ", ".join(sorted(project.connector_failures))
    return _emit(
        project,
        SignalType.CONNECTOR_FAILURE,
        severity=SignalSeverity.CRITICAL,
        confidence=rule_confidence(rules, SignalType.CONNECTOR_FAILURE.value),
        title="Connector failure",
        description=f"Connector fetch failed for: {failures}.",
        metric_value=float(len(project.connector_failures)),
        threshold=0.0,
        generated_at=ctx.evaluated_at,
    )


def evaluate_stale_data(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.STALE_DATA.value):
        return None
    if not project.enabled_connectors or project.connector_last_success_at is None:
        return None

    stale_hours = float(rules[SignalType.STALE_DATA.value]["stale_hours"])
    age_hours = (ctx.evaluated_at - project.connector_last_success_at).total_seconds() / 3600.0
    if age_hours < stale_hours:
        return None

    return _emit(
        project,
        SignalType.STALE_DATA,
        severity=SignalSeverity.WARNING,
        confidence=rule_confidence(rules, SignalType.STALE_DATA.value),
        title="Stale connector data",
        description=f"Last successful connector sync was {age_hours:.1f} hours ago.",
        metric_value=round(age_hours, 2),
        threshold=stale_hours,
        generated_at=ctx.evaluated_at,
    )


def evaluate_missing_owner(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.MISSING_OWNER.value):
        return None
    if project.owner:
        return None

    return _emit(
        project,
        SignalType.MISSING_OWNER,
        severity=SignalSeverity.INFO,
        confidence=rule_confidence(rules, SignalType.MISSING_OWNER.value),
        title="Missing owner",
        description="Project has no assigned owner field.",
        metric_value=0.0,
        threshold=1.0,
        generated_at=ctx.evaluated_at,
    )


def evaluate_resource_imbalance(
    ctx: SignalEvaluationContext,
    project: ProjectContext,
    rules: Dict[str, Dict[str, Any]],
) -> Optional[Signal]:
    if not rule_enabled(rules, SignalType.RESOURCE_IMBALANCE.value):
        return None
    cfg = rules[SignalType.RESOURCE_IMBALANCE.value]
    ratio_threshold = float(cfg["imbalance_ratio"])
    min_team = int(cfg["min_team_size"])

    active_teams = [p.team_size for p in ctx.projects if p.team_size and p.team_size > 0]
    if len(active_teams) < 2 or not project.team_size or project.team_size < min_team:
        return None

    avg_team = sum(active_teams) / len(active_teams)
    if avg_team <= 0:
        return None

    project_ratio = project.team_size / avg_team
    if project_ratio < ratio_threshold:
        return None

    return _emit(
        project,
        SignalType.RESOURCE_IMBALANCE,
        severity=SignalSeverity.WARNING,
        confidence=rule_confidence(rules, SignalType.RESOURCE_IMBALANCE.value),
        title="Resource imbalance",
        description=(
            f"Team size {project.team_size} is {project_ratio:.1f}x the portfolio "
            f"average of {avg_team:.1f}."
        ),
        metric_value=round(project_ratio, 2),
        threshold=ratio_threshold,
        generated_at=ctx.evaluated_at,
    )


PROJECT_EVALUATORS: List[Evaluator] = [
    evaluate_over_budget,
    evaluate_cost_spike,
    evaluate_no_commits_7_days,
    evaluate_no_commits_14_days,
    evaluate_velocity_drop,
    evaluate_no_jira_activity,
    evaluate_connector_failure,
    evaluate_stale_data,
    evaluate_missing_owner,
    evaluate_resource_imbalance,
] + OPPORTUNITY_EVALUATORS
