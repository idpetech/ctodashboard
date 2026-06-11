"""
Executive Briefing Generator — deterministic facts + optional LLM summarization.

The LLM never calculates metrics or creates recommendations.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from services.executive_briefing.assembler import (
    build_briefing_input,
    pre_sort_facts,
)
from services.executive_briefing.prompts import SYSTEM_PROMPT, build_user_prompt
from services.executive_briefing.schema import (
    ActionItem,
    BriefingInput,
    ConfidenceAssessment,
    ExecutiveBriefingOutput,
    ExecutiveFocus,
    OpportunityItem,
    ProjectAttentionItem,
    RiskItem,
)
from services.recommendations.engine import RecommendationEngine
from services.signals.engine import SignalEngine

logger = get_logger(__name__)

try:
    from langchain.schema import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False


def is_ai_briefing_enabled() -> bool:
    return os.getenv("ENABLE_AI_EXECUTIVE_BRIEFING", "false").lower() == "true"


class ExecutiveBriefingGenerator:
    """Transform signals + recommendations into a daily executive briefing."""

    def __init__(self, *, model: str | None = None):
        self._model = model or os.getenv("EXECUTIVE_BRIEFING_MODEL", "gpt-4o-mini")

    def generate_from_assignments(
        self,
        assignments: List[Dict[str, Any]],
        *,
        delivery_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
        connector_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
        use_ai: Optional[bool] = None,
    ) -> ExecutiveBriefingOutput:
        signals = SignalEngine().evaluate_assignments(
            assignments,
            delivery_metrics=delivery_metrics,
            connector_metrics=connector_metrics,
        )
        recommendations = RecommendationEngine().recommend(signals)
        briefing_input = build_briefing_input(
            assignments,
            [s.to_dict() for s in signals],
            [r.to_dict() for r in recommendations],
        )
        return self.generate(briefing_input, use_ai=use_ai)

    def generate(
        self,
        briefing_input: BriefingInput,
        *,
        use_ai: Optional[bool] = None,
    ) -> ExecutiveBriefingOutput:
        pre_sorted = pre_sort_facts(briefing_input)
        use_ai = is_ai_briefing_enabled() if use_ai is None else use_ai

        if use_ai and _LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                return self._generate_with_llm(briefing_input, pre_sorted)
            except Exception as exc:
                logger.warning("AI briefing failed, using deterministic fallback: %s", exc)

        return self._generate_deterministic(briefing_input, pre_sorted)

    def _generate_deterministic(
        self,
        briefing_input: BriefingInput,
        pre_sorted: Dict[str, Any],
    ) -> ExecutiveBriefingOutput:
        completeness = briefing_input.data_completeness
        health = briefing_input.portfolio_metrics.get("health_score") or {}
        score = health.get("overall_score")
        band = health.get("band") or "unknown"
        active = (briefing_input.portfolio_metrics.get("summary") or {}).get(
            "active_assignments", 0
        )
        risk_count = len(pre_sorted.get("top_risks") or [])
        opp_count = len(pre_sorted.get("opportunities") or [])

        summary_parts = [
            f"The portfolio includes {active} active project(s)",
        ]
        if score is not None:
            summary_parts.append(f"with an overall health score of {score}/100 ({band})")
        summary_parts.append(
            f"Based on supplied signals, {risk_count} risk item(s) and "
            f"{opp_count} opportunity item(s) warrant executive review."
        )
        if completeness.get("overall_level") == "low":
            summary_parts.append(
                "Confidence in this view is limited due to incomplete connector data."
            )

        confidence_narrative = _confidence_narrative(completeness)

        return ExecutiveBriefingOutput(
            executive_summary=" ".join(summary_parts),
            executive_focus=ExecutiveFocus(**(pre_sorted.get("executive_focus") or {})),
            top_risks=[RiskItem(**item) for item in pre_sorted.get("top_risks") or []],
            opportunities=[
                OpportunityItem(**item) for item in pre_sorted.get("opportunities") or []
            ],
            recommended_actions=[
                ActionItem(**item) for item in pre_sorted.get("recommended_actions") or []
            ],
            projects_requiring_attention=[
                ProjectAttentionItem(**item)
                for item in pre_sorted.get("projects_requiring_attention") or []
            ],
            confidence_assessment=ConfidenceAssessment(
                overall_level=str(completeness.get("overall_level") or "medium"),
                connector_readiness_pct=completeness.get("connector_readiness_pct"),
                low_confidence_signal_count=int(
                    completeness.get("low_confidence_signal_count") or 0
                ),
                narrative=confidence_narrative,
            ),
            generated_at=_utc_now(),
            generation_mode="deterministic",
        )

    def _generate_with_llm(
        self,
        briefing_input: BriefingInput,
        pre_sorted: Dict[str, Any],
    ) -> ExecutiveBriefingOutput:
        payload = {
            "portfolio_metrics": briefing_input.portfolio_metrics,
            "data_completeness": briefing_input.data_completeness,
            "pre_sorted": pre_sorted,
        }
        llm = ChatOpenAI(
            model=self._model,
            temperature=0.2,
            model_kwargs={"response_format": {"type": "json_object"}},
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        response = llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=build_user_prompt(payload)),
            ]
        )
        raw = json.loads(response.content)
        raw["generated_at"] = _utc_now()
        raw["generation_mode"] = "ai"
        out = ExecutiveBriefingOutput.model_validate(raw)
        return _apply_deterministic_truth(out, pre_sorted)


def _apply_deterministic_truth(
    out: ExecutiveBriefingOutput,
    pre_sorted: Dict[str, Any],
) -> ExecutiveBriefingOutput:
    """Keep LLM narrative polish; restore ranked actions and focus from rules engine."""
    focus_data = pre_sorted.get("executive_focus") or {}
    return out.model_copy(
        update={
            "executive_focus": ExecutiveFocus(**focus_data),
            "recommended_actions": [
                ActionItem(**item) for item in pre_sorted.get("recommended_actions") or []
            ],
            "top_risks": [RiskItem(**item) for item in pre_sorted.get("top_risks") or []],
            "opportunities": [
                OpportunityItem(**item) for item in pre_sorted.get("opportunities") or []
            ],
            "projects_requiring_attention": [
                ProjectAttentionItem(**item)
                for item in pre_sorted.get("projects_requiring_attention") or []
            ],
        }
    )


def _confidence_narrative(completeness: Dict[str, Any]) -> str:
    level = completeness.get("overall_level") or "medium"
    readiness = completeness.get("connector_readiness_pct")
    low_conf = completeness.get("low_confidence_signal_count") or 0
    parts = [f"Overall data confidence is {level}."]
    if readiness is not None:
        parts.append(f"Connector readiness is {readiness}%.")
    if low_conf:
        parts.append(f"{low_conf} supplied signal(s) have confidence below 0.75.")
    if level == "low":
        parts.append("Treat findings as directional until connector coverage improves.")
    return " ".join(parts)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
