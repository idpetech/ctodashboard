"""
AI Chatbot Service - Integrated for Routes
Provides intelligent responses using LangChain and OpenAI
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage, SystemMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Import metrics services
import sys
sys.path.insert(0, '.')
from services.embedded.aws_metrics import EmbeddedAWSMetrics
from services.embedded.github_metrics import EmbeddedGitHubMetrics
from services.embedded.jira_metrics import EmbeddedJiraMetrics
from services.embedded.openai_metrics import OpenAIMetrics

# Initialize metrics services
aws_metrics = EmbeddedAWSMetrics()
github_metrics = EmbeddedGitHubMetrics()
jira_metrics = EmbeddedJiraMetrics()
openai_metrics = OpenAIMetrics()

# Conversation history storage
conversation_history = {}

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
    """Load assignment data with REAL metrics"""
    assignments_dir = "backend/assignments"
    assignments = []
    
    if os.path.exists(assignments_dir):
        for filename in os.listdir(assignments_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(assignments_dir, filename), 'r') as f:
                        assignment = json.load(f)
                        assignment['id'] = filename[:-5]
                        
                        # Fetch REAL metrics
                        metrics = {}
                        config = assignment.get('metrics_config', {})
                        
                        # AWS
                        if config.get('aws', {}).get('enabled'):
                            try:
                                metrics['aws'] = aws_metrics.get_metrics()
                            except Exception as e:
                                metrics['aws'] = {'error': str(e)}
                        
                        # GitHub
                        if config.get('github', {}).get('enabled'):
                            try:
                                metrics['github'] = github_metrics.get_metrics(config['github'])
                            except Exception as e:
                                metrics['github'] = {'error': str(e)}
                        
                        # Jira
                        if config.get('jira', {}).get('enabled'):
                            try:
                                metrics['jira'] = jira_metrics.get_metrics(config['jira'])
                            except Exception as e:
                                metrics['jira'] = {'error': str(e)}
                        
                        # OpenAI
                        if config.get('openai', {}).get('enabled'):
                            try:
                                metrics['openai'] = openai_metrics.get_usage_metrics(config['openai'])
                            except Exception as e:
                                metrics['openai'] = {'error': str(e)}
                        
                        assignment['live_metrics'] = metrics
                        assignments.append(assignment)
                        
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
    
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
            print(f"AI processing failed: {e}")
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
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Build context
    context = get_system_context()
    context += f"\n\nCurrent Assignment Data:\n{json.dumps(assignment_data, indent=2)}"
    
    # Get conversation history
    history = conversation_history.get(user_id, [])
    
    # Build messages
    messages = [SystemMessage(content=context)]
    
    # Add history
    for msg in history[-10:]:  # Last 10 messages
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['content']))
        else:
            messages.append(AIMessage(content=msg['content']))
    
    # Add current question
    messages.append(HumanMessage(content=question))
    
    # Get response (non-streaming for now, streaming endpoint below)
    response = llm.invoke(messages)
    response_text = response.content
    
    # Store in history
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    conversation_history[user_id].append({
        'role': 'user',
        'content': question,
        'timestamp': datetime.now().isoformat()
    })
    
    conversation_history[user_id].append({
        'role': 'assistant',
        'content': response_text,
        'timestamp': datetime.now().isoformat()
    })
    
    return {
        "response": response_text,
        "confidence": 0.9,
        "question_type": "ai_powered",
        "data_used": ["assignments", "metrics"],
        "sources": ["OpenAI GPT-4o-mini", "Assignment Data"],
        "timestamp": datetime.now().isoformat()
    }

def _process_rule_based(question: str, assignment_data: Dict) -> Dict[str, Any]:
    """Fallback rule-based response"""
    
    question_lower = question.lower()
    assignments = assignment_data.get("assignments", [])
    
    # Simple keyword matching
    if "team size" in question_lower or "how many" in question_lower:
        ideptech = next((a for a in assignments if a['id'] == 'ideptech'), None)
        if ideptech:
            response = f"IdepTech has a team size of {ideptech.get('team_size', 'unknown')} member(s)."
        else:
            response = "I couldn't find team size information."
    
    elif "cost" in question_lower or "aws" in question_lower:
        response = "For cost information, I can help you analyze AWS costs. Please check the AWS metrics section in the dashboard."
    
    elif "assignment" in question_lower or "project" in question_lower:
        names = [a['name'] for a in assignments]
        response = f"I'm tracking {len(assignments)} assignment(s): {', '.join(names)}."
    
    else:
        response = f"I can help you with questions about:\n• Assignments and projects\n• Metrics and costs\n• Team information\n• Technology stacks\n• Service status\n\nPlease ask me a specific question about your managed services!"
    
    return {
        "response": response,
        "confidence": 0.7,
        "question_type": "rule_based",
        "data_used": ["assignments"],
        "sources": ["Rule-based matcher", "Assignment files"],
        "timestamp": datetime.now().isoformat()
    }

def get_conversation_history(user_id: str = "default", limit: int = 20) -> List[Dict]:
    """Get conversation history for a user"""
    history = conversation_history.get(user_id, [])
    return history[-limit:] if limit else history



def process_question_stream(question: str, user_id: str = "default"):
    """Process question with streaming response (generator)"""
    
    # Get assignment data for context
    assignment_data = get_assignment_data()
    
    # Only use streaming if AI is available
    if not (LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY")):
        # Fallback to non-streaming
        result = _process_rule_based(question, assignment_data)
        yield f"data: {json.dumps(result)}\n\n"
        return
    
    try:
        # Initialize LLM with streaming
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            streaming=True,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Build context
        context = get_system_context()
        context += f"\n\nCurrent Assignment Data:\n{json.dumps(assignment_data, indent=2)}"
        
        # Get conversation history
        history = conversation_history.get(user_id, [])
        
        # Build messages
        messages = [SystemMessage(content=context)]
        
        # Add history
        for msg in history[-10:]:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            else:
                messages.append(AIMessage(content=msg['content']))
        
        # Add current question
        messages.append(HumanMessage(content=question))
        
        # Stream response
        full_response = ""
        # Emit initial event so client clears placeholders
        yield f"data: {json.dumps({'init': True})}\n\n"
        for chunk in llm.stream(messages):
            token = None
            try:
                # LangChain chunks can expose .content or .delta or .message.content
                if hasattr(chunk, 'content') and chunk.content:
                    token = chunk.content
                elif hasattr(chunk, 'delta') and getattr(chunk, 'delta'):
                    token = chunk.delta
                elif hasattr(chunk, 'message') and getattr(chunk, 'message') and getattr(chunk.message,'content', None):
                    token = chunk.message.content
            except Exception as _e:
                token = None
            if token:
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        
        # Store in history
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        conversation_history[user_id].append({
            'role': 'user',
            'content': question,
            'timestamp': datetime.now().isoformat()
        })
        
        conversation_history[user_id].append({
            'role': 'assistant',
            'content': full_response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Send completion event (ensure full_response present)
        yield f"data: {json.dumps({'done': True, 'full_response': full_response})}\n\n"
        
    except Exception as e:
        print(f"❌ Streaming failed: {e}")
        import traceback
        traceback.print_exc()
        # Return error
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

def clear_conversation_history(user_id: str = "default") -> None:
    """Clear conversation history for a user"""
    if user_id in conversation_history:
        del conversation_history[user_id]
