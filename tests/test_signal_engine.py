"""Unit tests for CTOLens Signal Engine rule evaluators."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from services.signals.config import load_signal_rules
from services.signals.context import ProjectContext, SignalEvaluationContext
from services.signals.engine import SignalEngine
from services.signals.evaluators import (
    evaluate_blocked_work_increase,
    evaluate_build_failure_trend,
    evaluate_connector_failure,
    evaluate_cost_spike,
    evaluate_dependency_concentration,
    evaluate_high_performing_project,
    evaluate_high_reopen_rate,
    evaluate_high_service_coupling,
    evaluate_low_throughput_project,
    evaluate_missing_owner,
    evaluate_momentum_acceleration,
    evaluate_no_commits_7_days,
    evaluate_no_commits_14_days,
    evaluate_no_jira_activity,
    evaluate_over_budget,
    evaluate_pr_review_bottleneck,
    evaluate_release_instability,
    evaluate_resource_imbalance,
    evaluate_slow_delivery_trend,
    evaluate_stale_data,
    evaluate_stalled_project,
    evaluate_tech_debt_accumulation,
    evaluate_under_budget,
    evaluate_unused_capacity,
    evaluate_velocity_drop,
)
from services.signals.models import SignalCategory, SignalSeverity, SignalType

RULES = load_signal_rules()
FIXED_TIME = datetime(2026, 6, 7, 12, 0, 0)


def _project(**overrides) -> ProjectContext:
    base = dict(
        project_id="P1",
        project_name="Project One",
        status="active",
        monthly_burn=50000.0,
        target_burn=40000.0,
        variance_pct=25.0,
        variance_amount=10000.0,
        team_size=5,
        owner="owner@example.com",
        previous_monthly_burn=40000.0,
        enabled_connectors=["github"],
        github_enabled=True,
        jira_enabled=False,
    )
    base.update(overrides)
    return ProjectContext(**base)


def _ctx(projects, evaluated_at=FIXED_TIME) -> SignalEvaluationContext:
    return SignalEvaluationContext(
        evaluated_at=evaluated_at,
        projects=projects,
        portfolio_team_total=sum(p.team_size or 0 for p in projects),
    )


class TestFinancialSignals:
    def test_over_budget_warning(self):
        project = _project(variance_pct=12.0)
        signal = evaluate_over_budget(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.OVER_BUDGET
        assert signal.category == SignalCategory.FINANCIAL
        assert signal.severity == SignalSeverity.WARNING

    def test_over_budget_critical(self):
        project = _project(variance_pct=25.0)
        signal = evaluate_over_budget(_ctx([project]), project, RULES)
        assert signal.severity == SignalSeverity.CRITICAL

    def test_under_budget(self):
        project = _project(
            monthly_burn=15000.0,
            target_burn=20000.0,
            variance_pct=-25.0,
            variance_amount=-5000.0,
        )
        signal = evaluate_under_budget(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.UNDER_BUDGET

    def test_cost_spike(self):
        project = _project(monthly_burn=50000.0, previous_monthly_burn=35000.0)
        signal = evaluate_cost_spike(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.COST_SPIKE


class TestDeliverySignals:
    def test_no_commits_7_days(self):
        project = _project(commits_last_7_days=0, github_enabled=True)
        assert evaluate_no_commits_7_days(_ctx([project]), project, RULES) is not None

    def test_no_commits_14_days(self):
        project = _project(commits_last_14_days=0, github_enabled=True)
        signal = evaluate_no_commits_14_days(_ctx([project]), project, RULES)
        assert signal.severity == SignalSeverity.CRITICAL

    def test_velocity_drop(self):
        project = _project(
            commits_last_7_days=3,
            commits_prior_7_days=10,
            github_enabled=True,
        )
        signal = evaluate_velocity_drop(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.metric_value == 70.0

    def test_no_jira_activity(self):
        project = _project(
            jira_enabled=True,
            jira_issues_last_7_days=0,
            enabled_connectors=["jira"],
        )
        assert evaluate_no_jira_activity(_ctx([project]), project, RULES) is not None


class TestOperationalSignals:
    def test_connector_failure(self):
        project = _project(connector_failures=["github"])
        assert evaluate_connector_failure(_ctx([project]), project, RULES) is not None

    def test_stale_data(self):
        project = _project(
            enabled_connectors=["github"],
            connector_last_success_at=FIXED_TIME - timedelta(hours=72),
        )
        assert evaluate_stale_data(_ctx([project]), project, RULES) is not None

    def test_missing_owner(self):
        project = _project(owner=None)
        assert evaluate_missing_owner(_ctx([project]), project, RULES) is not None


class TestPortfolioSignals:
    def test_unused_capacity(self):
        project = _project(
            monthly_burn=12000.0,
            target_burn=20000.0,
            variance_pct=-40.0,
            team_size=4,
        )
        assert evaluate_unused_capacity(_ctx([project]), project, RULES) is not None

    def test_resource_imbalance(self):
        small = _project(project_id="S", project_name="Small", team_size=2, variance_pct=0.0)
        mid = _project(project_id="M", project_name="Mid", team_size=3, variance_pct=0.0)
        large = _project(project_id="L", project_name="Large", team_size=25, variance_pct=5.0)
        assert evaluate_resource_imbalance(_ctx([small, mid, large]), large, RULES) is not None

    def test_high_performing_project(self):
        project = _project(
            monthly_burn=9000.0,
            target_burn=10000.0,
            variance_pct=-10.0,
            commits_last_7_days=6,
            github_enabled=True,
        )
        assert evaluate_high_performing_project(_ctx([project]), project, RULES) is not None


class TestSignalEngine:
    def test_engine_evaluates_assignments(self):
        assignments = [
            {
                "id": "A",
                "name": "A",
                "status": "active",
                "monthly_burn_rate": 50000,
                "target_monthly_burn": 40000,
                "team_size": 2,
            },
            {
                "id": "B",
                "name": "B",
                "status": "active",
                "monthly_burn_rate": 10000,
                "target_monthly_burn": 20000,
                "team_size": 2,
            },
        ]
        signals = SignalEngine().evaluate_assignments(assignments)
        types = {s.signal_type for s in signals}
        assert SignalType.OVER_BUDGET in types
        assert SignalType.UNDER_BUDGET in types
        assert all("recommend" not in s.description.lower() for s in signals)

    def test_sample_fixture(self):
        sample_path = (
            Path(__file__).resolve().parents[1] / "samples" / "signals" / "input_context.json"
        )
        payload = json.loads(sample_path.read_text(encoding="utf-8"))
        signals = SignalEngine().evaluate_assignments(
            payload["assignments"],
            delivery_metrics=payload.get("delivery_metrics"),
            connector_metrics=payload.get("connector_metrics"),
        )
        types = {s.signal_type.value for s in signals}
        assert "OVER_BUDGET" in types
        assert "UNDER_BUDGET" in types
        assert "NO_JIRA_ACTIVITY" in types
        assert "CONNECTOR_FAILURE" in types
        assert "MISSING_OWNER" in types

    def test_disabled_rule(self, tmp_path):
        config_file = tmp_path / "rules.json"
        config_file.write_text(
            json.dumps({"rules": {"OVER_BUDGET": {"enabled": False}}}),
            encoding="utf-8",
        )
        engine = SignalEngine(config_file)
        signals = engine.evaluate_assignments(
            [
                {
                    "id": "A",
                    "name": "A",
                    "status": "active",
                    "monthly_burn_rate": 50000,
                    "target_monthly_burn": 40000,
                }
            ]
        )
        assert all(s.signal_type != SignalType.OVER_BUDGET for s in signals)


class TestOpportunityOperationalSignals:
    def test_slow_delivery_trend(self):
        project = _project(
            commits_last_7_days=7,
            commits_prior_7_days=10,
            github_enabled=True,
        )
        signal = evaluate_slow_delivery_trend(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.SLOW_DELIVERY_TREND

    def test_momentum_acceleration(self):
        project = _project(
            commits_last_7_days=8,
            commits_prior_7_days=4,
            github_enabled=True,
        )
        signal = evaluate_momentum_acceleration(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.MOMENTUM_ACCELERATION

    def test_low_throughput_project(self):
        project = _project(
            monthly_burn=9000.0,
            target_burn=10000.0,
            variance_pct=-10.0,
            team_size=5,
            commits_last_7_days=3,
            github_enabled=True,
        )
        signal = evaluate_low_throughput_project(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.LOW_THROUGHPUT_PROJECT

    def test_stalled_project(self):
        project = _project(
            monthly_burn=9000.0,
            target_burn=10000.0,
            variance_pct=-10.0,
            team_size=3,
            commits_last_14_days=0,
            github_enabled=True,
            owner="owner@example.com",
        )
        signal = evaluate_stalled_project(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.STALLED_PROJECT

    def test_tech_debt_accumulation(self):
        project = _project(
            jira_enabled=True,
            enabled_connectors=["jira"],
            jira_issues_last_7_days=12,
            commits_last_7_days=2,
            github_enabled=True,
        )
        signal = evaluate_tech_debt_accumulation(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.TECH_DEBT_ACCUMULATION

    def test_dependency_concentration_single_connector(self):
        project = _project(enabled_connectors=["github"], team_size=3)
        signal = evaluate_dependency_concentration(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.DEPENDENCY_CONCENTRATION

    def test_high_service_coupling(self):
        project = _project(
            enabled_connectors=["github", "jira", "railway", "aws"],
            github_enabled=True,
            jira_enabled=True,
        )
        signal = evaluate_high_service_coupling(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.HIGH_SERVICE_COUPLING

    def test_blocked_work_increase(self):
        project = _project(blocked_work_count=8, blocked_work_prior_count=3)
        signal = evaluate_blocked_work_increase(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.BLOCKED_WORK_INCREASE

    def test_pr_review_bottleneck(self):
        project = _project(open_pull_requests=4, pr_review_wait_hours=36.0)
        signal = evaluate_pr_review_bottleneck(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.PR_REVIEW_BOTTLENECK

    def test_high_reopen_rate(self):
        project = _project(issue_reopen_count_7d=3, issue_closed_count_7d=10)
        signal = evaluate_high_reopen_rate(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.HIGH_REOPEN_RATE

    def test_build_failure_trend(self):
        project = _project(build_failure_count_7d=6, build_failure_count_prior_7d=2)
        signal = evaluate_build_failure_trend(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.BUILD_FAILURE_TREND

    def test_release_instability(self):
        project = _project(release_count_7d=4, release_failure_count_7d=2)
        signal = evaluate_release_instability(_ctx([project]), project, RULES)
        assert signal is not None
        assert signal.signal_type == SignalType.RELEASE_INSTABILITY

    def test_missing_overlay_metrics_skip(self):
        project = _project()
        ctx = _ctx([project])
        assert evaluate_blocked_work_increase(ctx, project, RULES) is None
        assert evaluate_pr_review_bottleneck(ctx, project, RULES) is None
        assert evaluate_build_failure_trend(ctx, project, RULES) is None
