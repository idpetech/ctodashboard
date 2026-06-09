"""
CTOLens Signal Engine — structured portfolio signals (no NL in this layer).

Architecture: docs/CTO-BRIEFING-FLOW.md
Configuration: config/signal_rules.json
"""

from services.signals.context import SignalEvaluationContext, build_context_from_assignments
from services.signals.engine import SignalEngine
from services.signals.models import Signal, SignalCategory, SignalSeverity, SignalType

__all__ = [
    "Signal",
    "SignalCategory",
    "SignalEngine",
    "SignalEvaluationContext",
    "SignalSeverity",
    "SignalType",
    "build_context_from_assignments",
]
