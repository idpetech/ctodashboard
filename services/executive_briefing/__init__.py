"""
AI Executive Briefing Generator — signals + recommendations → daily CTO briefing.

Optional LLM summarization via ENABLE_AI_EXECUTIVE_BRIEFING.
Feedback loop: services.executive_briefing.feedback
"""

from services.executive_briefing.assembler import build_briefing_input, pre_sort_facts
from services.executive_briefing.feedback import (
    feedback_summary,
    list_recommendation_feedback,
    record_recommendation_feedback,
)
from services.executive_briefing.generator import ExecutiveBriefingGenerator, is_ai_briefing_enabled
from services.executive_briefing.schema import BriefingInput, ExecutiveBriefingOutput

__all__ = [
    "BriefingInput",
    "ExecutiveBriefingGenerator",
    "ExecutiveBriefingOutput",
    "build_briefing_input",
    "feedback_summary",
    "is_ai_briefing_enabled",
    "list_recommendation_feedback",
    "pre_sort_facts",
    "record_recommendation_feedback",
]
