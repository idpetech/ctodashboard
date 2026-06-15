"""Delivery / activity rule-based analyzer."""

from __future__ import annotations

from typing import Any, List, Mapping

from analysis.constants import (
    BUS_FACTOR_THRESHOLD,
    HIGH_CHURN_COMMITS_30D_THRESHOLD,
    HIGH_CHURN_MAX_FILES_PER_COMMIT,
    STALE_COMMITS_30D_THRESHOLD,
    STALE_MIN_FILE_COUNT,
)
from analysis.models import Finding, PipelineInput


class DeliveryAnalyzer:
    """Detect bus factor, stale activity, and churn instability signals."""

    def analyze(self, pipeline_input: PipelineInput) -> List[Finding]:
        findings: List[Finding] = []
        metrics = pipeline_input.metrics
        snapshot = pipeline_input.snapshot

        findings.extend(self._bus_factor_risk(metrics))
        findings.extend(self._stale_module_risk(metrics))
        findings.extend(self._high_churn_indicator(metrics, snapshot))
        findings.sort(key=lambda finding: finding.id)
        return findings

    def _bus_factor_risk(self, metrics: Mapping[str, Any]) -> List[Finding]:
        contributors = metrics.get("contributors") or {}
        per_contributor = contributors.get("commits_per_contributor") or []
        if not isinstance(per_contributor, list) or not per_contributor:
            return []

        counts = sorted(
            int(row.get("commit_count") or 0)
            for row in per_contributor
            if isinstance(row, Mapping)
        )
        total = sum(counts)
        if total <= 0:
            return []

        top_share = counts[-1] / total
        if top_share <= BUS_FACTOR_THRESHOLD:
            return []

        top_author = ""
        for row in per_contributor:
            if isinstance(row, Mapping) and int(row.get("commit_count") or 0) == counts[-1]:
                top_author = str(row.get("author") or "unknown")
                break

        return [
            Finding(
                id="delivery.bus_factor",
                category="delivery",
                severity="high",
                title="Bus factor risk",
                evidence=(
                    f"Top contributor '{top_author}' authored {counts[-1]} of {total} commits "
                    f"({top_share:.1%}, threshold {BUS_FACTOR_THRESHOLD:.0%})."
                ),
                confidence=0.92,
                impact="Knowledge and delivery capacity are concentrated in one contributor.",
                recommendation="Spread ownership via pairing, reviews, and shared runbooks.",
            )
        ]

    def _stale_module_risk(self, metrics: Mapping[str, Any]) -> List[Finding]:
        activity = metrics.get("activity") or {}
        repo_size = metrics.get("repo_size") or {}
        commits_30d = int(activity.get("commits_last_30_days") or 0)
        total_files = int(repo_size.get("total_files") or 0)

        if commits_30d >= STALE_COMMITS_30D_THRESHOLD or total_files < STALE_MIN_FILE_COUNT:
            return []

        return [
            Finding(
                id="delivery.stale_activity",
                category="delivery",
                severity="medium",
                title="Stale repository activity",
                evidence=(
                    f"No commits in the last 30 days ({commits_30d}) across "
                    f"{total_files} tracked files."
                ),
                confidence=0.75,
                impact="Modules may lack recent validation and drift from active standards.",
                recommendation="Schedule maintenance work or archive unused areas explicitly.",
            )
        ]

    def _high_churn_indicator(
        self,
        metrics: Mapping[str, Any],
        snapshot: Mapping[str, Any],
    ) -> List[Finding]:
        activity = metrics.get("activity") or {}
        repo_size = metrics.get("repo_size") or {}
        commits_30d = int(activity.get("commits_last_30_days") or 0)
        churn = float(activity.get("churn_rate_files_per_commit") or 0.0)
        total_loc = int(repo_size.get("total_loc") or 0)

        if commits_30d < HIGH_CHURN_COMMITS_30D_THRESHOLD:
            return []
        if churn > HIGH_CHURN_MAX_FILES_PER_COMMIT:
            return []
        if total_loc <= 0:
            return []

        commit_count = len(snapshot.get("commits") or [])
        return [
            Finding(
                id="delivery.high_churn_stable_loc",
                category="delivery",
                severity="medium",
                title="High commit frequency with low per-commit churn",
                evidence=(
                    f"{commits_30d} commits in 30 days with churn "
                    f"{churn:.2f} files/commit (max {HIGH_CHURN_MAX_FILES_PER_COMMIT}) "
                    f"and total LOC {total_loc} across {commit_count} sampled commits."
                ),
                confidence=0.7,
                impact="Frequent commits with small file churn may indicate instability or noise.",
                recommendation="Review commit practices and batch meaningful changes where appropriate.",
            )
        ]
