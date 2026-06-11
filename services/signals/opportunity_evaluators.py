"""
Opportunity signal evaluators — one class per opportunity SignalType.

Each class decides which thresholds come from config vs inline logic.
Risk and delivery-warning rules remain function-based in evaluators.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type

from services.signals.config import rule_confidence, rule_enabled
from services.signals.context import ProjectContext, SignalEvaluationContext
from services.signals.models import Signal, SignalSeverity, SignalType, build_signal

Evaluator = Callable[
    [SignalEvaluationContext, ProjectContext, Dict[str, Dict[str, Any]]], Optional[Signal]
]


class OpportunityEvaluator(ABC):
    """Base interface for CTO opportunity signals (severity INFO by default)."""

    signal_type: ClassVar[SignalType]
    default_severity: ClassVar[SignalSeverity] = SignalSeverity.INFO

    def evaluate(
        self,
        ctx: SignalEvaluationContext,
        project: ProjectContext,
        rules: Dict[str, Dict[str, Any]],
    ) -> Optional[Signal]:
        if not rule_enabled(rules, self.signal_type.value):
            return None
        return self.check(ctx, project, rules)

    @abstractmethod
    def check(
        self,
        ctx: SignalEvaluationContext,
        project: ProjectContext,
        rules: Dict[str, Dict[str, Any]],
    ) -> Optional[Signal]:
        """Return a signal when opportunity conditions are met, else None."""

    def cfg(self, rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        return rules[self.signal_type.value]

    def confidence(self, rules: Dict[str, Dict[str, Any]]) -> float:
        return rule_confidence(rules, self.signal_type.value)

    def emit(
        self,
        project: ProjectContext,
        ctx: SignalEvaluationContext,
        rules: Dict[str, Dict[str, Any]],
        *,
        title: str,
        description: str,
        metric_value: Optional[float],
        threshold: Optional[float],
        severity: Optional[SignalSeverity] = None,
    ) -> Signal:
        return build_signal(
            project,
            self.signal_type,
            severity=severity or self.default_severity,
            confidence=self.confidence(rules),
            title=title,
            description=description,
            metric_value=metric_value,
            threshold=threshold,
            generated_at=ctx.evaluated_at,
        )


class UnderBudgetEvaluator(OpportunityEvaluator):
    signal_type = SignalType.UNDER_BUDGET

    def check(self, ctx, project, rules):
        if project.variance_pct is None or project.variance_pct >= 0:
            return None
        min_under = float(self.cfg(rules)["min_under_pct"])
        pct = float(project.variance_pct)
        if pct > -min_under:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Under budget",
            description=(
                f"Monthly burn {project.monthly_burn or 0:.0f} is below target "
                f"{project.target_burn or 0:.0f} by {abs(pct):.1f}%."
            ),
            metric_value=pct,
            threshold=-min_under,
        )


class UnusedCapacityEvaluator(OpportunityEvaluator):
    signal_type = SignalType.UNUSED_CAPACITY

    def check(self, ctx, project, rules):
        cfg = self.cfg(rules)
        min_under = float(cfg["min_under_pct"])
        min_team = int(cfg["min_team_size"])
        if project.variance_pct is None or project.variance_pct > -min_under:
            return None
        if not project.team_size or project.team_size < min_team:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Unused capacity",
            description=(
                f"Project is {abs(project.variance_pct):.1f}% under budget with "
                f"team size {project.team_size}."
            ),
            metric_value=float(project.variance_pct),
            threshold=-min_under,
        )


class HighPerformingProjectEvaluator(OpportunityEvaluator):
    signal_type = SignalType.HIGH_PERFORMING_PROJECT

    def check(self, ctx, project, rules):
        cfg = self.cfg(rules)
        min_under = float(cfg["min_under_pct"])
        min_commits = int(cfg["min_commits_7d"])
        if project.variance_pct is None or project.variance_pct > -min_under:
            return None
        if not project.github_enabled or project.commits_last_7_days is None:
            return None
        if project.commits_last_7_days < min_commits:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="High performing project",
            description=(
                f"Project is {abs(project.variance_pct):.1f}% under budget with "
                f"{project.commits_last_7_days} commits in the last 7 days."
            ),
            metric_value=float(project.commits_last_7_days),
            threshold=float(min_commits),
        )


class SlowDeliveryTrendEvaluator(OpportunityEvaluator):
    signal_type = SignalType.SLOW_DELIVERY_TREND

    def check(self, ctx, project, rules):
        if not project.github_enabled:
            return None
        if project.commits_last_7_days is None or project.commits_prior_7_days is None:
            return None
        if project.commits_prior_7_days <= 0:
            return None
        cfg = self.cfg(rules)
        min_drop = float(cfg["min_drop_pct"])
        max_drop = float(cfg["max_drop_pct"])
        drop_pct = (
            (project.commits_prior_7_days - project.commits_last_7_days)
            / project.commits_prior_7_days
            * 100.0
        )
        if drop_pct < min_drop or drop_pct >= max_drop:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Slow delivery trend",
            description=(
                f"Commits fell from {project.commits_prior_7_days} to "
                f"{project.commits_last_7_days} week-over-week ({drop_pct:.1f}% decrease)."
            ),
            metric_value=round(drop_pct, 2),
            threshold=min_drop,
        )


class MomentumAccelerationEvaluator(OpportunityEvaluator):
    signal_type = SignalType.MOMENTUM_ACCELERATION

    def check(self, ctx, project, rules):
        if not project.github_enabled:
            return None
        if project.commits_last_7_days is None or project.commits_prior_7_days is None:
            return None
        cfg = self.cfg(rules)
        min_increase = float(cfg["min_increase_pct"])
        min_prior = int(cfg["min_prior_commits"])
        min_last = int(cfg["min_last_commits"])
        if project.commits_prior_7_days < min_prior or project.commits_last_7_days < min_last:
            return None
        if project.commits_last_7_days <= project.commits_prior_7_days:
            return None
        increase_pct = (
            (project.commits_last_7_days - project.commits_prior_7_days)
            / project.commits_prior_7_days
            * 100.0
        )
        if increase_pct < min_increase:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Momentum acceleration",
            description=(
                f"Commits rose from {project.commits_prior_7_days} to "
                f"{project.commits_last_7_days} week-over-week ({increase_pct:.1f}% increase)."
            ),
            metric_value=round(increase_pct, 2),
            threshold=min_increase,
        )


class LowThroughputProjectEvaluator(OpportunityEvaluator):
    signal_type = SignalType.LOW_THROUGHPUT_PROJECT

    def check(self, ctx, project, rules):
        cfg = self.cfg(rules)
        min_under = float(cfg["min_under_pct"])
        min_team = int(cfg["min_team_size"])
        max_per_person = float(cfg["max_commits_per_person_7d"])
        if project.variance_pct is None or project.variance_pct > -min_under:
            return None
        if not project.team_size or project.team_size < min_team:
            return None
        if not project.github_enabled or project.commits_last_7_days is None:
            return None
        if project.commits_last_7_days <= 0:
            return None
        throughput = project.commits_last_7_days / project.team_size
        if throughput >= max_per_person:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Low throughput project",
            description=(
                f"Project is {abs(project.variance_pct):.1f}% under budget with "
                f"{throughput:.1f} commits per person in the last 7 days."
            ),
            metric_value=round(throughput, 2),
            threshold=max_per_person,
        )


class StalledProjectEvaluator(OpportunityEvaluator):
    signal_type = SignalType.STALLED_PROJECT

    def check(self, ctx, project, rules):
        cfg = self.cfg(rules)
        min_under = float(cfg["min_under_pct"])
        min_team = int(cfg["min_team_size"])
        if not project.github_enabled or project.commits_last_14_days is None:
            return None
        if project.commits_last_14_days > 0:
            return None
        if project.variance_pct is None or project.variance_pct > -min_under:
            return None
        if not project.team_size or project.team_size < min_team:
            return None
        if not project.owner:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Stalled project",
            description=(
                f"No commits in 14 days while {abs(project.variance_pct):.1f}% under budget "
                f"with team size {project.team_size}."
            ),
            metric_value=float(project.commits_last_14_days),
            threshold=0.0,
        )


class TechDebtAccumulationEvaluator(OpportunityEvaluator):
    signal_type = SignalType.TECH_DEBT_ACCUMULATION

    def check(self, ctx, project, rules):
        if not project.jira_enabled:
            return None
        if project.jira_issues_last_7_days is None or project.commits_last_7_days is None:
            return None
        cfg = self.cfg(rules)
        min_issues = int(cfg["min_jira_issues_7d"])
        max_commits = int(cfg["max_commits_7d"])
        min_ratio = float(cfg["min_issue_to_commit_ratio"])
        issues = project.jira_issues_last_7_days
        commits = project.commits_last_7_days
        if issues < min_issues or commits > max_commits:
            return None
        ratio = issues / max(commits, 1)
        if ratio < min_ratio:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Tech debt accumulation",
            description=(
                f"{issues} Jira issues in the last 7 days vs {commits} commits (ratio {ratio:.1f})."
            ),
            metric_value=round(ratio, 2),
            threshold=min_ratio,
        )


class DependencyConcentrationEvaluator(OpportunityEvaluator):
    signal_type = SignalType.DEPENDENCY_CONCENTRATION

    def check(self, ctx, project, rules):
        cfg = self.cfg(rules)
        share_threshold = float(cfg["top_share_threshold_pct"])
        min_team = int(cfg["min_team_size"])

        if project.top_dependency_share_pct is not None:
            if project.top_dependency_share_pct < share_threshold:
                return None
            metric = project.top_dependency_share_pct
            detail = f"Top dependency accounts for {metric:.1f}% of usage."
        elif (
            project.dependency_count is not None
            and project.dependency_count == 1
            and project.team_size
            and project.team_size >= min_team
        ):
            metric = 100.0
            detail = "Project relies on a single tracked dependency."
        elif (
            len(project.enabled_connectors) == 1
            and project.team_size
            and project.team_size >= min_team
        ):
            metric = 100.0
            detail = f"Project depends on a single connector ({project.enabled_connectors[0]})."
        else:
            return None

        return self.emit(
            project,
            ctx,
            rules,
            title="Dependency concentration",
            description=detail,
            metric_value=metric,
            threshold=share_threshold,
        )


class HighServiceCouplingEvaluator(OpportunityEvaluator):
    signal_type = SignalType.HIGH_SERVICE_COUPLING

    def check(self, ctx, project, rules):
        cfg = self.cfg(rules)
        min_connectors = int(cfg["min_connectors"])
        min_services = int(cfg.get("min_service_count", min_connectors))
        connector_count = len(project.enabled_connectors)
        service_count = (
            project.dependency_count if project.dependency_count is not None else connector_count
        )
        if connector_count < min_connectors and service_count < min_services:
            return None
        metric = float(max(connector_count, service_count))
        return self.emit(
            project,
            ctx,
            rules,
            title="High service coupling",
            description=(
                f"Project integrates {connector_count} connectors "
                f"across {int(service_count)} tracked services."
            ),
            metric_value=metric,
            threshold=float(min_connectors),
        )


class BlockedWorkIncreaseEvaluator(OpportunityEvaluator):
    signal_type = SignalType.BLOCKED_WORK_INCREASE

    def check(self, ctx, project, rules):
        if project.blocked_work_count is None or project.blocked_work_prior_count is None:
            return None
        min_increase = int(self.cfg(rules)["min_increase_count"])
        current = project.blocked_work_count
        prior = project.blocked_work_prior_count
        increase = current - prior
        if increase < min_increase:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Blocked work increase",
            description=f"Blocked work items rose from {prior} to {current} (+{increase}).",
            metric_value=float(increase),
            threshold=float(min_increase),
        )


class PrReviewBottleneckEvaluator(OpportunityEvaluator):
    signal_type = SignalType.PR_REVIEW_BOTTLENECK

    def check(self, ctx, project, rules):
        if project.pr_review_wait_hours is None or project.open_pull_requests is None:
            return None
        cfg = self.cfg(rules)
        wait_threshold = float(cfg["wait_hours_threshold"])
        min_open = int(cfg["min_open_prs"])
        if project.open_pull_requests < min_open:
            return None
        if project.pr_review_wait_hours < wait_threshold:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="PR review bottleneck",
            description=(
                f"{project.open_pull_requests} open PRs with average review wait "
                f"of {project.pr_review_wait_hours:.1f} hours."
            ),
            metric_value=float(project.pr_review_wait_hours),
            threshold=wait_threshold,
        )


class HighReopenRateEvaluator(OpportunityEvaluator):
    signal_type = SignalType.HIGH_REOPEN_RATE

    def check(self, ctx, project, rules):
        if project.issue_reopen_count_7d is None or project.issue_closed_count_7d is None:
            return None
        cfg = self.cfg(rules)
        rate_threshold = float(cfg["reopen_rate_threshold_pct"])
        min_closed = int(cfg["min_closed_issues_7d"])
        closed = project.issue_closed_count_7d
        reopens = project.issue_reopen_count_7d
        if closed < min_closed:
            return None
        rate = reopens / closed * 100.0
        if rate < rate_threshold:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="High reopen rate",
            description=(
                f"{reopens} reopened issues vs {closed} closed in the last 7 days "
                f"({rate:.1f}% reopen rate)."
            ),
            metric_value=round(rate, 2),
            threshold=rate_threshold,
        )


class BuildFailureTrendEvaluator(OpportunityEvaluator):
    signal_type = SignalType.BUILD_FAILURE_TREND

    def check(self, ctx, project, rules):
        if project.build_failure_count_7d is None or project.build_failure_count_prior_7d is None:
            return None
        min_increase = int(self.cfg(rules)["min_increase_count"])
        current = project.build_failure_count_7d
        prior = project.build_failure_count_prior_7d
        increase = current - prior
        if increase < min_increase:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Build failure trend",
            description=(
                f"Build failures rose from {prior} to {current} week-over-week (+{increase})."
            ),
            metric_value=float(increase),
            threshold=float(min_increase),
        )


class ReleaseInstabilityEvaluator(OpportunityEvaluator):
    signal_type = SignalType.RELEASE_INSTABILITY

    def check(self, ctx, project, rules):
        if project.release_count_7d is None or project.release_failure_count_7d is None:
            return None
        cfg = self.cfg(rules)
        failure_threshold = float(cfg["failure_rate_threshold_pct"])
        min_releases = int(cfg["min_release_count_7d"])
        releases = project.release_count_7d
        failures = project.release_failure_count_7d
        if releases < min_releases:
            return None
        rate = failures / releases * 100.0
        if rate < failure_threshold:
            return None
        return self.emit(
            project,
            ctx,
            rules,
            title="Release instability",
            description=(
                f"{failures} failed releases out of {releases} in the last 7 days "
                f"({rate:.1f}% failure rate)."
            ),
            metric_value=round(rate, 2),
            threshold=failure_threshold,
        )


OPPORTUNITY_EVALUATOR_CLASSES: List[Type[OpportunityEvaluator]] = [
    UnderBudgetEvaluator,
    UnusedCapacityEvaluator,
    HighPerformingProjectEvaluator,
    SlowDeliveryTrendEvaluator,
    MomentumAccelerationEvaluator,
    LowThroughputProjectEvaluator,
    StalledProjectEvaluator,
    TechDebtAccumulationEvaluator,
    DependencyConcentrationEvaluator,
    HighServiceCouplingEvaluator,
    BlockedWorkIncreaseEvaluator,
    PrReviewBottleneckEvaluator,
    HighReopenRateEvaluator,
    BuildFailureTrendEvaluator,
    ReleaseInstabilityEvaluator,
]

OPPORTUNITY_EVALUATORS: List[Evaluator] = [
    evaluator.evaluate for evaluator in (cls() for cls in OPPORTUNITY_EVALUATOR_CLASSES)
]

# Backward-compatible callables for tests and direct imports.
_instances = {cls.signal_type: cls() for cls in OPPORTUNITY_EVALUATOR_CLASSES}
evaluate_under_budget = _instances[SignalType.UNDER_BUDGET].evaluate
evaluate_unused_capacity = _instances[SignalType.UNUSED_CAPACITY].evaluate
evaluate_high_performing_project = _instances[SignalType.HIGH_PERFORMING_PROJECT].evaluate
evaluate_slow_delivery_trend = _instances[SignalType.SLOW_DELIVERY_TREND].evaluate
evaluate_momentum_acceleration = _instances[SignalType.MOMENTUM_ACCELERATION].evaluate
evaluate_low_throughput_project = _instances[SignalType.LOW_THROUGHPUT_PROJECT].evaluate
evaluate_stalled_project = _instances[SignalType.STALLED_PROJECT].evaluate
evaluate_tech_debt_accumulation = _instances[SignalType.TECH_DEBT_ACCUMULATION].evaluate
evaluate_dependency_concentration = _instances[SignalType.DEPENDENCY_CONCENTRATION].evaluate
evaluate_high_service_coupling = _instances[SignalType.HIGH_SERVICE_COUPLING].evaluate
evaluate_blocked_work_increase = _instances[SignalType.BLOCKED_WORK_INCREASE].evaluate
evaluate_pr_review_bottleneck = _instances[SignalType.PR_REVIEW_BOTTLENECK].evaluate
evaluate_high_reopen_rate = _instances[SignalType.HIGH_REOPEN_RATE].evaluate
evaluate_build_failure_trend = _instances[SignalType.BUILD_FAILURE_TREND].evaluate
evaluate_release_instability = _instances[SignalType.RELEASE_INSTABILITY].evaluate
