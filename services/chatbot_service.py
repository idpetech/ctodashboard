"""
AI Chatbot Service - Integrated for Routes
Provides intelligent responses using LangChain and OpenAI
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# LangChain imports
try:
    from langchain.schema import AIMessage, HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Import metrics services
import sys

sys.path.insert(0, ".")
from connectors.registry import ConnectorRegistry
from services.embedded.aws_metrics import EmbeddedAWSMetrics
from services.embedded.github_metrics import EmbeddedGitHubMetrics
from services.embedded.jira_metrics import EmbeddedJiraMetrics

# Initialize metrics services
aws_metrics = EmbeddedAWSMetrics()
github_metrics = EmbeddedGitHubMetrics()
jira_metrics = EmbeddedJiraMetrics()

# Conversation history storage
conversation_history = {}

# Short-lived cache for metrics fetched during a chat session (workspace:assignment -> metrics)
_metrics_session_cache: Dict[str, Dict] = {}

METRICS_QUESTION_KEYWORDS = (
    "cost",
    "aws",
    "metric",
    "github",
    "jira",
    "spend",
    "usage",
    "openai",
    "railway",
    "performance",
    "activity",
    "revenue",
    "expense",
)

# Stored on the assignment record — no live connector fetch required
ASSIGNMENT_METADATA_KEYWORDS = (
    "burn rate",
    "monthly burn",
    "team size",
    "target burn",
    "target monthly",
)


def _json_dumps_safe(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


def _assignment_matches(assignment: Dict, assignment_id: str) -> bool:
    if not assignment_id:
        return False
    aid = assignment_id.lower()
    return (assignment.get("id") or "").lower() == aid or (
        assignment.get("assignment_id") or ""
    ).lower() == aid


def _get_enabled_connectors(metrics_config: Dict) -> List[str]:
    return [
        name
        for name, config in (metrics_config or {}).items()
        if isinstance(config, dict) and config.get("enabled")
    ]


def _question_needs_live_metrics(question: str) -> bool:
    """True when the question needs live connector data (not assignment metadata)."""
    q = question.lower()
    if any(kw in q for kw in ASSIGNMENT_METADATA_KEYWORDS):
        return False
    return any(kw in q for kw in METRICS_QUESTION_KEYWORDS)


def _question_needs_metrics(question: str) -> bool:
    """Alias used by consent flow — live metrics only."""
    return _question_needs_live_metrics(question)


def _assignment_metadata_answer(question: str, ctx: Dict) -> Dict[str, Any]:
    """Answer burn rate / team size from assignment record without live metrics."""
    selected = ctx.get("selected_assignment")
    if not selected:
        return None

    user_q = _extract_user_question(question).lower()
    name = selected.get("name", selected.get("id", "Unknown"))

    if "burn rate" in user_q or "monthly burn" in user_q:
        burn = selected.get("monthly_burn_rate")
        target = selected.get("target_monthly_burn")
        if burn is not None:
            response = f"**{name}** monthly burn rate is **${burn:,}**."
            if target is not None:
                response += f" Target monthly burn: **${target:,}**."
            return {
                "response": response,
                "confidence": 1.0,
                "question_type": "assignment_metadata",
                "workspace_context": {
                    "workspace_id": ctx["workspace_id"],
                    "workspace_name": ctx["workspace_name"],
                    "assignment_id": ctx.get("assignment_id"),
                },
                "timestamp": datetime.now().isoformat(),
            }

    if "team size" in user_q:
        team_size = selected.get("team_size")
        if team_size is not None:
            return {
                "response": f"**{name}** has a team size of **{team_size}** member(s).",
                "confidence": 1.0,
                "question_type": "assignment_metadata",
                "workspace_context": {
                    "workspace_id": ctx["workspace_id"],
                    "workspace_name": ctx["workspace_name"],
                    "assignment_id": ctx.get("assignment_id"),
                },
                "timestamp": datetime.now().isoformat(),
            }

    return None


def _metrics_has_data(live_metrics: Dict) -> bool:
    if not live_metrics:
        return False
    for _service, data in live_metrics.items():
        if not data:
            continue
        if isinstance(data, dict):
            if data.get("error"):
                continue
            if data.get("cost_analysis", {}).get("error"):
                continue
            if len(data) > 0:
                return True
        elif isinstance(data, list) and len(data) > 0:
            if not any(isinstance(item, dict) and item.get("error") for item in data):
                return True
    return False


def _fetch_assignment_metrics(workspace_id: str, assignment_id: str, assignment: Dict) -> Dict:
    """Lazy import to avoid circular dependency with api_routes."""
    from routes.api_routes import collect_assignment_metrics

    return collect_assignment_metrics(workspace_id, assignment_id, assignment)


def _find_assignment(assignments: List[Dict], assignment_id: str) -> Dict:
    return next((a for a in assignments if _assignment_matches(a, assignment_id)), None)


def build_workspace_context(
    workspace_id: str,
    assignment_id: str = None,
    fetch_metrics: bool = False,
) -> Dict[str, Any]:
    """Build scoped workspace/assignment context for chatbot prompts."""
    from services.workspace.workspace_service import WorkspaceService

    workspace_service = WorkspaceService()
    workspace_data = workspace_service.get_workspace(workspace_id)
    workspace_name = (
        workspace_data.get("name", workspace_id) if "error" not in workspace_data else workspace_id
    )

    assignments_result = workspace_service.get_workspace_assignments(workspace_id)
    all_assignments = assignments_result.get("assignments", [])
    selected = _find_assignment(all_assignments, assignment_id) if assignment_id else None

    context_parts = [f"Current Workspace: {workspace_name} (ID: {workspace_id})"]

    if all_assignments:
        context_parts.append(f"Workspace Assignments ({len(all_assignments)} total):")
        for a in all_assignments:
            context_parts.append(
                f"- {a.get('name', a.get('id', 'Unknown'))} (Status: {a.get('status', 'active')})"
            )
    else:
        context_parts.append("No assignments found in this workspace")

    scoped_assignments = all_assignments
    live_metrics = None
    enabled_connectors = []
    cache_key = f"{workspace_id}:{assignment_id}" if assignment_id else None

    if selected:
        selected = dict(selected)
        enabled_connectors = _get_enabled_connectors(selected.get("metrics_config", {}))
        context_parts.append(
            f"\nCurrently Selected Assignment: {selected.get('name', assignment_id)} (ID: {assignment_id})"
        )

        if cache_key and cache_key in _metrics_session_cache:
            live_metrics = _metrics_session_cache[cache_key]
            selected["live_metrics"] = live_metrics

        if fetch_metrics and enabled_connectors:
            aid = selected.get("id") or selected.get("assignment_id") or assignment_id
            live_metrics = _fetch_assignment_metrics(workspace_id, aid, selected)
            _metrics_session_cache[cache_key] = live_metrics
            selected["live_metrics"] = live_metrics
            context_parts.append("Live Metrics: loaded for this session")
            if live_metrics:
                for svc, data in live_metrics.items():
                    status = "available" if _metrics_has_data({svc: data}) else "error or empty"
                    context_parts.append(f"- {svc.upper()}: {status}")
        elif live_metrics:
            context_parts.append("Live Metrics: loaded from session cache")
        elif enabled_connectors:
            context_parts.append(
                f"Configured Connectors (not loaded): {', '.join(enabled_connectors)}"
            )

        scoped_assignments = [selected]

    workspace_context = "\n".join(context_parts)
    return {
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "assignment_id": assignment_id,
        "enabled_connectors": enabled_connectors,
        "selected_assignment": selected,
        "context_parts": context_parts,
        "workspace_context": workspace_context,
        "assignment_data": {"assignments": scoped_assignments},
    }


def _metrics_consent_response(ctx: Dict, question: str) -> Dict[str, Any]:
    selected = ctx.get("selected_assignment") or {}
    name = selected.get("name", ctx.get("assignment_id", "this assignment"))
    connectors = ", ".join(ctx.get("enabled_connectors") or []) or "none"
    response = (
        f"Metrics aren't loaded yet for **{name}**.\n\n"
        f"Configured connectors: {connectors}.\n\n"
        "Should I fetch live metrics now? This usually takes **90 seconds or more**.\n"
        "Use **Yes** to load metrics, or **No** to answer with assignment details only."
    )
    return {
        "response": response,
        "metrics_action_required": "confirm_fetch",
        "pending_question": question,
        "confidence": 1.0,
        "question_type": "metrics_consent",
        "workspace_context": {
            "workspace_id": ctx["workspace_id"],
            "workspace_name": ctx["workspace_name"],
            "assignment_id": ctx.get("assignment_id"),
        },
        "timestamp": datetime.now().isoformat(),
    }


def _connectors_not_configured_response(ctx: Dict) -> Dict[str, Any]:
    name = (ctx.get("selected_assignment") or {}).get("name", ctx.get("assignment_id"))
    response = (
        f"No metrics connectors are enabled for **{name}**.\n\n"
        "Please configure connectors (AWS, GitHub, Jira, etc.) in the assignment setup tab, "
        "then ask again or use **Load All Metrics** on the assignment page."
    )
    return {
        "response": response,
        "confidence": 1.0,
        "question_type": "metrics_not_configured",
        "workspace_context": {
            "workspace_id": ctx["workspace_id"],
            "workspace_name": ctx["workspace_name"],
            "assignment_id": ctx.get("assignment_id"),
        },
        "timestamp": datetime.now().isoformat(),
    }


def _extract_user_question(text: str) -> str:
    """Return only the user's message when prompt includes WORKSPACE CONTEXT."""
    marker = "USER QUESTION:"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text.strip()


def _select_assignment_prompt(ctx: Dict) -> Dict[str, Any]:
    return {
        "response": (
            "Please open a specific **assignment tab** (or select an assignment) "
            "before asking about metrics or costs — I need to know which project to look at."
        ),
        "confidence": 1.0,
        "question_type": "select_assignment",
        "workspace_context": {
            "workspace_id": ctx["workspace_id"],
            "workspace_name": ctx["workspace_name"],
            "assignment_id": None,
        },
        "timestamp": datetime.now().isoformat(),
    }


def prepare_workspace_chat(
    question: str,
    workspace_id: str,
    assignment_id: str = None,
    fetch_metrics: bool = False,
    skip_metrics_fetch: bool = False,
) -> Dict[str, Any]:
    """Prepare question + data; may short-circuit for metrics consent."""
    ctx = build_workspace_context(workspace_id, assignment_id, fetch_metrics=fetch_metrics)
    enhanced_question = (
        f"WORKSPACE CONTEXT:\n{ctx['workspace_context']}\n\nUSER QUESTION: {question}"
    )

    metadata_answer = _assignment_metadata_answer(question, ctx)
    if metadata_answer:
        return {"short_circuit": metadata_answer, "ctx": ctx}

    if (
        _question_needs_live_metrics(question)
        and not assignment_id
        and not fetch_metrics
        and not skip_metrics_fetch
    ):
        return {"short_circuit": _select_assignment_prompt(ctx), "ctx": ctx}

    if (
        assignment_id
        and _question_needs_live_metrics(question)
        and not fetch_metrics
        and not skip_metrics_fetch
    ):
        selected = ctx.get("selected_assignment")
        if selected:
            enabled = ctx.get("enabled_connectors") or []
            has_metrics = _metrics_has_data(selected.get("live_metrics") or {})
            if not enabled:
                return {"short_circuit": _connectors_not_configured_response(ctx), "ctx": ctx}
            if not has_metrics:
                return {"short_circuit": _metrics_consent_response(ctx, question), "ctx": ctx}

    return {
        "enhanced_question": enhanced_question,
        "assignment_data": ctx["assignment_data"],
        "ctx": ctx,
    }


def get_system_context() -> str:
    """Get system context about available data"""
    return """You are a helpful CTO Dashboard Assistant. You help CTOs analyze their:
- Project assignments and metrics
- AWS costs and infrastructure
- GitHub repository activity
- Jira project management
- Team information and technology stacks
- Service status and configurations

Provide concise, actionable insights. When asked about specific data, reference the actual metrics provided."""


def get_assignment_data() -> Dict[str, Any]:
    """Load assignment data from workspace store with REAL metrics"""
    from .workspace.workspace_service import WorkspaceService

    workspace_service = WorkspaceService()
    assignments = []

    # Load assignments from all workspaces (PostgreSQL-backed)
    try:
        # Get all workspaces first
        workspaces_result = workspace_service.list_workspaces()
        if "workspaces" in workspaces_result:
            for workspace in workspaces_result["workspaces"]:
                workspace_id = workspace.get("id")
                if workspace_id:
                    result = workspace_service.get_workspace_assignments(workspace_id)
                    if "assignments" in result:
                        for assignment in result["assignments"]:
                            assignment["workspace_id"] = workspace_id
                            metrics = {}
                            config = assignment.get("metrics_config", {})
                            assignment_id = assignment.get("id")

                            if assignment_id:
                                from .embedded.aws_metrics import EmbeddedAWSMetrics
                                from .embedded.github_metrics import EmbeddedGitHubMetrics
                                from .embedded.jira_metrics import EmbeddedJiraMetrics

                                workspace_connectors = {
                                    "aws": EmbeddedAWSMetrics(
                                        workspace_id=workspace_id, assignment_id=assignment_id
                                    ),
                                    "github": EmbeddedGitHubMetrics(
                                        workspace_id=workspace_id, assignment_id=assignment_id
                                    ),
                                    "jira": EmbeddedJiraMetrics(
                                        workspace_id=workspace_id, assignment_id=assignment_id
                                    ),
                                }

                                if config.get("aws", {}).get("enabled"):
                                    try:
                                        metrics["aws"] = workspace_connectors["aws"].get_metrics()
                                    except Exception as e:
                                        metrics["aws"] = {"error": str(e)}

                                if config.get("github", {}).get("enabled"):
                                    try:
                                        github_metrics_config = {
                                            "org": config["github"]
                                            .get("auth_instance", {})
                                            .get("credentials", {})
                                            .get("github_org", ""),
                                            "repos": config["github"]
                                            .get("auth_instance", {})
                                            .get("credentials", {})
                                            .get("github_repos", "")
                                            .split(",")
                                            if config["github"]
                                            .get("auth_instance", {})
                                            .get("credentials", {})
                                            .get("github_repos")
                                            else [],
                                        }
                                        github_metrics_config["repos"] = [
                                            repo.strip()
                                            for repo in github_metrics_config["repos"]
                                            if repo.strip()
                                        ]
                                        metrics["github"] = workspace_connectors[
                                            "github"
                                        ].get_metrics(github_metrics_config)
                                    except Exception as e:
                                        metrics["github"] = {"error": str(e)}

                                if config.get("jira", {}).get("enabled"):
                                    try:
                                        metrics["jira"] = workspace_connectors["jira"].get_metrics(
                                            config["jira"]
                                        )
                                    except Exception as e:
                                        metrics["jira"] = {"error": str(e)}

                                if config.get("openai", {}).get("enabled"):
                                    try:
                                        openai_connector = ConnectorRegistry.get_connector("openai")
                                        metrics["openai"] = openai_connector.get_metrics(
                                            config["openai"]
                                        )
                                    except Exception as e:
                                        metrics["openai"] = {"error": str(e)}

                            assignment["live_metrics"] = metrics
                            assignments.append(assignment)
    except Exception as e:
        logger.error("Error loading workspace assignments: %s", e, exc_info=True)

    return {"assignments": assignments}


def process_question(question: str, user_id: str = "default") -> Dict[str, Any]:
    """Process a question using AI or fallback to rule-based response"""

    # Get assignment data for context
    assignment_data = get_assignment_data()

    # Try AI response first
    if LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        try:
            return _process_with_ai(question, user_id, assignment_data)
        except Exception as e:
            logger.error("AI processing failed: %s", e, exc_info=True)
            # Fall through to rule-based

    # Fallback to rule-based response
    return _process_rule_based(question, assignment_data)


def _process_with_ai(question: str, user_id: str, assignment_data: Dict) -> Dict[str, Any]:
    """Process question using AI with streaming support"""

    # Initialize LLM with streaming enabled
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        streaming=True,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Build context
    context = get_system_context()
    context += f"\n\nCurrent Assignment Data:\n{_json_dumps_safe(assignment_data)}"

    # Get conversation history
    history = conversation_history.get(user_id, [])

    # Build messages
    messages = [SystemMessage(content=context)]

    # Add history
    for msg in history[-10:]:  # Last 10 messages
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    # Add current question
    messages.append(HumanMessage(content=question))

    # Get response (non-streaming for now, streaming endpoint below)
    response = llm.invoke(messages)
    response_text = response.content

    # Store in history
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append(
        {"role": "user", "content": question, "timestamp": datetime.now().isoformat()}
    )

    conversation_history[user_id].append(
        {"role": "assistant", "content": response_text, "timestamp": datetime.now().isoformat()}
    )

    return {
        "response": response_text,
        "confidence": 0.9,
        "question_type": "ai_powered",
        "data_used": ["assignments", "metrics"],
        "sources": ["OpenAI GPT-4o-mini", "Assignment Data"],
        "timestamp": datetime.now().isoformat(),
    }


def _process_rule_based(question: str, assignment_data: Dict) -> Dict[str, Any]:
    """Fallback rule-based response with workspace and assignment context awareness"""

    user_question = _extract_user_question(question)
    user_q_lower = user_question.lower()
    full_lower = question.lower()
    assignments = assignment_data.get("assignments", [])

    # Extract workspace and assignment context from the full prompt
    current_workspace = None
    selected_assignment = None

    if "workspace context:" in full_lower:
        lines = question.split("\n")
        for line in lines:
            if "current workspace:" in line.lower():
                current_workspace = line.split("(")[0].replace("Current Workspace:", "").strip()
            elif "currently selected assignment:" in line.lower():
                selected_assignment = line.replace("Currently Selected Assignment:", "").strip()
                if " (ID:" in selected_assignment:
                    selected_assignment = selected_assignment.split(" (ID:")[0].strip()

    # Match assignment names only in the user's actual question (not workspace context block)
    assignment_names_in_question = []
    for assignment in assignments:
        assignment_name = assignment.get("name", assignment.get("id", ""))
        assignment_id = assignment.get("id", "")
        if assignment_name.lower() in user_q_lower or assignment_id.lower() in user_q_lower:
            assignment_names_in_question.append(assignment)

    # Burn rate / team size from selected assignment (stored metadata)
    if selected_assignment and ("burn rate" in user_q_lower or "monthly burn" in user_q_lower):
        selected_assign_obj = next(
            (
                a
                for a in assignments
                if a.get("name", "").lower() in selected_assignment.lower()
                or a.get("id", "").lower() in selected_assignment.lower()
            ),
            None,
        )
        if selected_assign_obj:
            name = selected_assign_obj.get("name", selected_assign_obj.get("id", "Unknown"))
            burn = selected_assign_obj.get("monthly_burn_rate")
            target = selected_assign_obj.get("target_monthly_burn")
            if burn is not None:
                response = f"**{name}** monthly burn rate is **${burn:,}**."
                if target is not None:
                    response += f" Target monthly burn: **${target:,}**."
            else:
                response = f"No monthly burn rate is recorded for **{name}**."
            return {
                "response": response,
                "confidence": 0.9,
                "question_type": "rule_based",
                "data_used": ["assignments"],
                "sources": ["Assignment metadata"],
                "timestamp": datetime.now().isoformat(),
            }

    # Live connector metrics — do not fall through to status listing
    if _question_needs_live_metrics(user_question):
        if len(assignments) == 1:
            name = assignments[0].get("name", assignments[0].get("id", "this assignment"))
            response = (
                f"Live metrics are not loaded for **{name}** yet. "
                "Use the **Yes, fetch metrics** button when prompted, or click **Load All Metrics** on the assignment tab."
            )
        else:
            response = (
                "Open a specific assignment tab and ask again — "
                "I'll prompt you to fetch live metrics (takes 90+ seconds) before answering cost/AWS questions."
            )
        return {
            "response": response,
            "confidence": 0.8,
            "question_type": "rule_based_metrics_hint",
            "data_used": ["assignments"],
            "sources": ["Rule-based matcher"],
            "timestamp": datetime.now().isoformat(),
        }

    # If we have a selected assignment and asking about status (not burn/cost)
    if selected_assignment and "status" in user_q_lower:
        selected_assign_obj = next(
            (
                a
                for a in assignments
                if a.get("name", "").lower() in selected_assignment.lower()
                or a.get("id", "").lower() in selected_assignment.lower()
            ),
            None,
        )
        if selected_assign_obj:
            assignment_name = selected_assign_obj.get(
                "name", selected_assign_obj.get("id", "Unknown")
            )
            status = selected_assign_obj.get("status", "active")
            team_size = selected_assign_obj.get("team_size")
            monthly_burn = selected_assign_obj.get("monthly_burn_rate")

            response_parts = [f"Assignment: {assignment_name}"]
            response_parts.append(f"Status: {status}")

            if team_size:
                response_parts.append(f"Team Size: {team_size} members")
            if monthly_burn:
                response_parts.append(f"Monthly Burn Rate: ${monthly_burn:,}")

            # Check for configured services
            metrics_config = selected_assign_obj.get("metrics_config", {})
            enabled_services = [
                service for service, config in metrics_config.items() if config.get("enabled")
            ]
            if enabled_services:
                response_parts.append(f"Configured Services: {', '.join(enabled_services)}")

            response = "\n".join(response_parts)

        else:
            response = f"I found the selected assignment '{selected_assignment}' but couldn't retrieve detailed information."

    # If asking about specific assignments mentioned in the user question (status only)
    elif assignment_names_in_question and "status" in user_q_lower:
        responses = []
        for assignment in assignment_names_in_question:
            assignment_name = assignment.get("name", assignment.get("id", "Unknown"))
            status = assignment.get("status", "active")
            responses.append(f"{assignment_name}: {status}")
        response = "Assignment Status:\n" + "\n".join(responses)

    # Generic assignment questions
    elif "how many assignments" in user_q_lower or "total assignments" in user_q_lower:
        names = [a.get("name", a.get("id", "Unknown")) for a in assignments]
        if current_workspace:
            response = f"In {current_workspace}, you have {len(assignments)} assignment(s): {', '.join(names)}."
        else:
            response = f"I'm tracking {len(assignments)} assignment(s): {', '.join(names)}."

    elif "team size" in user_q_lower:
        if assignment_names_in_question:
            # Asking about specific assignment team size
            assignment = assignment_names_in_question[0]
            assignment_name = assignment.get("name", assignment.get("id", "Unknown"))
            team_size = assignment.get("team_size")
            if team_size:
                response = f"{assignment_name} has a team size of {team_size} member(s)."
            else:
                response = f"I couldn't find team size information for {assignment_name}."
        else:
            response = "Please specify which assignment's team size you'd like to know about."

    elif "cost" in user_q_lower or "aws" in user_q_lower:
        if assignment_names_in_question:
            assignment_name = assignment_names_in_question[0].get("name", "the assignment")
            response = f"For {assignment_name} cost information, please check the AWS metrics section in the dashboard or ask for specific cost details."
        else:
            response = "For cost information, I can help you analyze AWS costs. Please check the AWS metrics section in the dashboard."

    elif "assignment" in user_q_lower or "project" in user_q_lower:
        names = [a.get("name", a.get("id", "Unknown")) for a in assignments]
        if current_workspace:
            response = f"In {current_workspace}, you have {len(assignments)} assignment(s): {', '.join(names)}."
        else:
            response = f"I'm tracking {len(assignments)} assignment(s): {', '.join(names)}."

    else:
        context_info = ""
        if current_workspace:
            context_info = f" in {current_workspace}"
        if selected_assignment:
            context_info += f" with '{selected_assignment}' selected"

        response = f"I can help you with questions about your {len(assignments)} assignment(s){context_info}:\n• Assignment status and details\n• Team information and metrics\n• Cost and resource usage\n• Technology stacks\n• Service configuration\n\nTry asking: 'What is the status?' or 'Show me assignment details'"

    return {
        "response": response,
        "confidence": 0.7,
        "question_type": "rule_based",
        "data_used": ["assignments"],
        "sources": ["Rule-based matcher", "Assignment files"],
        "timestamp": datetime.now().isoformat(),
    }


def get_conversation_history(user_id: str = "default", limit: int = 20) -> List[Dict]:
    """Get conversation history for a user"""
    history = conversation_history.get(user_id, [])
    return history[-limit:] if limit else history


def process_question_with_workspace(
    question: str,
    user_id: str,
    workspace_id: str,
    assignment_id: str = None,
    fetch_metrics: bool = False,
    skip_metrics_fetch: bool = False,
) -> Dict[str, Any]:
    """Process question with workspace/assignment context and optional metrics fetch."""
    try:
        logger.info(
            "Processing workspace-aware question",
            extra={
                "user_id": user_id,
                "workspace_id": workspace_id,
                "assignment_id": assignment_id,
                "fetch_metrics": fetch_metrics,
                "question_length": len(question),
            },
        )

        prepared = prepare_workspace_chat(
            question,
            workspace_id,
            assignment_id,
            fetch_metrics=fetch_metrics,
            skip_metrics_fetch=skip_metrics_fetch,
        )
        if prepared.get("short_circuit"):
            result = prepared["short_circuit"]
            _store_history(user_id, question, result.get("response", ""))
            return result

        enhanced_question = prepared["enhanced_question"]
        assignment_data = prepared["assignment_data"]
        ctx = prepared["ctx"]

        if LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                result = _process_with_ai(enhanced_question, user_id, assignment_data)
            except Exception as e:
                logger.error("AI processing failed: %s", e, exc_info=True)
                result = _process_rule_based(enhanced_question, assignment_data)
        else:
            result = _process_rule_based(enhanced_question, assignment_data)

        if isinstance(result, dict):
            result["workspace_context"] = {
                "workspace_id": ctx["workspace_id"],
                "workspace_name": ctx["workspace_name"],
                "assignment_id": assignment_id,
            }
        return result

    except Exception as e:
        logger.error(
            "Workspace-aware question processing failed",
            extra={
                "user_id": user_id,
                "workspace_id": workspace_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return process_question(question, user_id)


def _store_history(user_id: str, question: str, response: str) -> None:
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append(
        {
            "role": "user",
            "content": question,
            "timestamp": datetime.now().isoformat(),
        }
    )
    conversation_history[user_id].append(
        {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat(),
        }
    )


def _stream_ai_response(
    question: str, user_id: str, assignment_data: Dict, extra_done: Dict = None
):
    """Core streaming generator shared by global and workspace-aware paths."""
    if not (LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY")):
        result = _process_rule_based(question, assignment_data)
        yield f"data: {json.dumps(result, default=str)}\n\n"
        return

    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            streaming=True,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        context = get_system_context()
        context += f"\n\nCurrent Assignment Data:\n{_json_dumps_safe(assignment_data)}"
        history = conversation_history.get(user_id, [])
        messages = [SystemMessage(content=context)]
        for msg in history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=question))

        full_response = ""
        yield f"data: {json.dumps({'init': True})}\n\n"
        for chunk in llm.stream(messages):
            token = None
            try:
                if hasattr(chunk, "content") and chunk.content:
                    token = chunk.content
                elif hasattr(chunk, "delta") and getattr(chunk, "delta"):
                    token = chunk.delta
                elif (
                    hasattr(chunk, "message")
                    and getattr(chunk, "message")
                    and getattr(chunk.message, "content", None)
                ):
                    token = chunk.message.content
            except Exception:
                token = None
            if token:
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

        _store_history(user_id, question, full_response)
        done_payload = {"done": True, "full_response": full_response}
        if extra_done:
            done_payload.update(extra_done)
        yield f"data: {json.dumps(done_payload, default=str)}\n\n"

    except Exception as e:
        logger.error("Streaming failed: %s", e, exc_info=True)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def process_question_stream(question: str, user_id: str = "default"):
    """Process question with streaming response (generator)."""
    assignment_data = get_assignment_data()
    yield from _stream_ai_response(question, user_id, assignment_data)


def process_question_stream_with_workspace(
    question: str,
    user_id: str,
    workspace_id: str,
    assignment_id: str = None,
    fetch_metrics: bool = False,
    skip_metrics_fetch: bool = False,
):
    """Stream response with workspace/assignment context and metrics consent."""
    try:
        if fetch_metrics:
            yield f"data: {json.dumps({'status': 'fetching_metrics', 'message': 'Loading metrics — this may take 90+ seconds...'})}\n\n"

        prepared = prepare_workspace_chat(
            question,
            workspace_id,
            assignment_id,
            fetch_metrics=fetch_metrics,
            skip_metrics_fetch=skip_metrics_fetch,
        )

        if prepared.get("short_circuit"):
            sc = prepared["short_circuit"]
            _store_history(user_id, question, sc.get("response", ""))
            yield f"data: {json.dumps({'init': True})}\n\n"
            done_payload = {
                "done": True,
                "full_response": sc.get("response", ""),
                "metrics_action_required": sc.get("metrics_action_required"),
                "pending_question": sc.get("pending_question"),
                "question_type": sc.get("question_type"),
            }
            yield f"data: {json.dumps(done_payload, default=str)}\n\n"
            return

        enhanced_question = prepared["enhanced_question"]
        assignment_data = prepared["assignment_data"]
        yield from _stream_ai_response(enhanced_question, user_id, assignment_data)

    except Exception as e:
        logger.error("Workspace streaming failed: %s", e, exc_info=True)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


def clear_conversation_history(user_id: str = "default") -> None:
    """Clear conversation history for a user"""
    if user_id in conversation_history:
        del conversation_history[user_id]
