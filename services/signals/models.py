"""
CTOLens Signal Engine — domain model.

Structured signals only; no natural-language recommendations in this layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class SignalCategory(str, Enum):
    FINANCIAL = "Financial"
    DELIVERY = "Delivery"
    OPERATIONAL = "Operational"
    PORTFOLIO = "Portfolio"


class SignalType(str, Enum):
    OVER_BUDGET = "OVER_BUDGET"
    UNDER_BUDGET = "UNDER_BUDGET"
    COST_SPIKE = "COST_SPIKE"
    NO_COMMITS_7_DAYS = "NO_COMMITS_7_DAYS"
    NO_COMMITS_14_DAYS = "NO_COMMITS_14_DAYS"
    VELOCITY_DROP = "VELOCITY_DROP"
    NO_JIRA_ACTIVITY = "NO_JIRA_ACTIVITY"
    CONNECTOR_FAILURE = "CONNECTOR_FAILURE"
    STALE_DATA = "STALE_DATA"
    MISSING_OWNER = "MISSING_OWNER"
    UNUSED_CAPACITY = "UNUSED_CAPACITY"
    RESOURCE_IMBALANCE = "RESOURCE_IMBALANCE"
    HIGH_PERFORMING_PROJECT = "HIGH_PERFORMING_PROJECT"
    SLOW_DELIVERY_TREND = "SLOW_DELIVERY_TREND"
    BLOCKED_WORK_INCREASE = "BLOCKED_WORK_INCREASE"
    PR_REVIEW_BOTTLENECK = "PR_REVIEW_BOTTLENECK"
    HIGH_REOPEN_RATE = "HIGH_REOPEN_RATE"
    BUILD_FAILURE_TREND = "BUILD_FAILURE_TREND"
    RELEASE_INSTABILITY = "RELEASE_INSTABILITY"
    DEPENDENCY_CONCENTRATION = "DEPENDENCY_CONCENTRATION"
    HIGH_SERVICE_COUPLING = "HIGH_SERVICE_COUPLING"
    TECH_DEBT_ACCUMULATION = "TECH_DEBT_ACCUMULATION"
    LOW_THROUGHPUT_PROJECT = "LOW_THROUGHPUT_PROJECT"
    STALLED_PROJECT = "STALLED_PROJECT"
    MOMENTUM_ACCELERATION = "MOMENTUM_ACCELERATION"


SIGNAL_CATEGORY: Dict[SignalType, SignalCategory] = {
    SignalType.OVER_BUDGET: SignalCategory.FINANCIAL,
    SignalType.UNDER_BUDGET: SignalCategory.FINANCIAL,
    SignalType.COST_SPIKE: SignalCategory.FINANCIAL,
    SignalType.NO_COMMITS_7_DAYS: SignalCategory.DELIVERY,
    SignalType.NO_COMMITS_14_DAYS: SignalCategory.DELIVERY,
    SignalType.VELOCITY_DROP: SignalCategory.DELIVERY,
    SignalType.NO_JIRA_ACTIVITY: SignalCategory.DELIVERY,
    SignalType.CONNECTOR_FAILURE: SignalCategory.OPERATIONAL,
    SignalType.STALE_DATA: SignalCategory.OPERATIONAL,
    SignalType.MISSING_OWNER: SignalCategory.OPERATIONAL,
    SignalType.UNUSED_CAPACITY: SignalCategory.PORTFOLIO,
    SignalType.RESOURCE_IMBALANCE: SignalCategory.PORTFOLIO,
    SignalType.HIGH_PERFORMING_PROJECT: SignalCategory.PORTFOLIO,
    SignalType.SLOW_DELIVERY_TREND: SignalCategory.DELIVERY,
    SignalType.BLOCKED_WORK_INCREASE: SignalCategory.DELIVERY,
    SignalType.PR_REVIEW_BOTTLENECK: SignalCategory.DELIVERY,
    SignalType.HIGH_REOPEN_RATE: SignalCategory.DELIVERY,
    SignalType.BUILD_FAILURE_TREND: SignalCategory.OPERATIONAL,
    SignalType.RELEASE_INSTABILITY: SignalCategory.OPERATIONAL,
    SignalType.DEPENDENCY_CONCENTRATION: SignalCategory.PORTFOLIO,
    SignalType.HIGH_SERVICE_COUPLING: SignalCategory.PORTFOLIO,
    SignalType.TECH_DEBT_ACCUMULATION: SignalCategory.DELIVERY,
    SignalType.LOW_THROUGHPUT_PROJECT: SignalCategory.PORTFOLIO,
    SignalType.STALLED_PROJECT: SignalCategory.DELIVERY,
    SignalType.MOMENTUM_ACCELERATION: SignalCategory.DELIVERY,
}


class SignalSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Signal:
    signal_id: str
    category: SignalCategory
    severity: SignalSeverity
    confidence: float
    project_id: str
    project_name: str
    title: str
    description: str
    metric_value: Optional[float]
    threshold: Optional[float]
    generated_at: str
    signal_type: SignalType = field(repr=False)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        data["signal_type"] = self.signal_type.value
        return data

    @staticmethod
    def make_id(project_id: str, signal_type: SignalType) -> str:
        return f"{project_id}:{signal_type.value}"


def build_signal(
    project: Any,
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
    """Construct a Signal from evaluated project facts."""
    return Signal(
        signal_id=Signal.make_id(project.project_id, signal_type),
        category=SIGNAL_CATEGORY[signal_type],
        severity=severity,
        confidence=confidence,
        project_id=project.project_id,
        project_name=project.project_name,
        title=title,
        description=description,
        metric_value=metric_value,
        threshold=threshold,
        generated_at=generated_at.isoformat() + "Z",
        signal_type=signal_type,
    )
