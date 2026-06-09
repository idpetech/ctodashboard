"""
Structured input/output schema for AI Executive Briefing generation.

The LLM may only populate narrative fields from supplied facts in BriefingInput.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BriefingInput(BaseModel):
    """Canonical generator input — metrics, signals, recommendations only."""

    portfolio_metrics: Dict[str, Any] = Field(default_factory=dict)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    data_completeness: Dict[str, Any] = Field(default_factory=dict)


class RiskItem(BaseModel):
    project_name: str
    signal_type: str
    severity: str
    summary: str
    confidence: float


class OpportunityItem(BaseModel):
    project_name: str
    signal_type: str
    summary: str
    confidence: float


class ActionItem(BaseModel):
    recommendation_id: str
    title: str
    description: str
    priority: str
    impact_score: int
    project_name: str
    why: str = ""
    reason: str = ""
    signal_type: str = ""
    source_signal_ids: List[str] = Field(default_factory=list)


class ExecutiveFocus(BaseModel):
    """Deterministic answers to the five executive success questions."""

    biggest_risk: str
    biggest_opportunity: str
    do_first: str
    why_first_action: str
    confidence_summary: str
    source_recommendation_id: Optional[str] = None
    source_signal_ids: List[str] = Field(default_factory=list)


class ProjectAttentionItem(BaseModel):
    project_name: str
    highest_severity: str
    signal_count: int
    summaries: List[str]


class ConfidenceAssessment(BaseModel):
    overall_level: str
    connector_readiness_pct: Optional[float] = None
    low_confidence_signal_count: int = 0
    narrative: str


class ExecutiveBriefingOutput(BaseModel):
    """Structured daily CTO briefing — six required sections plus executive focus."""

    executive_summary: str
    executive_focus: ExecutiveFocus
    top_risks: List[RiskItem]
    opportunities: List[OpportunityItem]
    recommended_actions: List[ActionItem]
    projects_requiring_attention: List[ProjectAttentionItem]
    confidence_assessment: ConfidenceAssessment
    generated_at: str
    generation_mode: str = "deterministic"

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
