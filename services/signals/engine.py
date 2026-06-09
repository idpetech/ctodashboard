"""
CTOLens Signal Engine — deterministic rule evaluation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from services.signals.config import load_signal_rules
from services.signals.context import SignalEvaluationContext, build_context_from_assignments
from services.signals.evaluators import PROJECT_EVALUATORS
from services.signals.models import Signal, SignalSeverity


class SignalEngine:
    """Evaluate configured rules against a normalized context."""

    def __init__(self, config_path: str | Path | None = None):
        self._rules = load_signal_rules(config_path)

    @property
    def rules(self) -> Dict[str, dict]:
        return self._rules

    def evaluate(self, context: SignalEvaluationContext) -> List[Signal]:
        signals: List[Signal] = []
        for project in context.projects:
            for evaluator in PROJECT_EVALUATORS:
                signal = evaluator(context, project, self._rules)
                if signal is not None:
                    signals.append(signal)
        return self._sort_signals(signals)

    def evaluate_assignments(
        self,
        assignments: List[dict],
        *,
        delivery_metrics: Optional[Dict[str, Dict]] = None,
        connector_metrics: Optional[Dict[str, Dict]] = None,
    ) -> List[Signal]:
        context = build_context_from_assignments(
            assignments,
            delivery_metrics=delivery_metrics,
            connector_metrics=connector_metrics,
        )
        return self.evaluate(context)

    @staticmethod
    def _sort_signals(signals: List[Signal]) -> List[Signal]:
        rank = {
            SignalSeverity.CRITICAL: 0,
            SignalSeverity.WARNING: 1,
            SignalSeverity.INFO: 2,
        }
        return sorted(
            signals,
            key=lambda s: (
                rank.get(s.severity, 9),
                s.category.value,
                s.project_name,
                s.signal_type.value,
            ),
        )
