#!/usr/bin/env python3
"""
Chatbot Service for CTO Dashboard

This service provides AI-powered chatbot functionality that can answer questions
about managed services, assignments, metrics, and provide insights using OpenAI LLM via LangChain.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from assignment_service import AssignmentService
from metrics_service import MetricsAggregator

# LangChain and OpenAI imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatbotService:
    """AI-powered chatbot service for CTO Dashboard"""
    
    def __init__(self):
        self.assignment_service = AssignmentService()
        self.metrics_aggregator = MetricsAggregator()
        self.conversation_history = []
        
        # Initialize OpenAI LLM
        self.llm = self._init_llm()
        self.prompt_template = self._create_prompt_template()
        self.chain = self._create_chain()
    
    def _init_llm(self) -> ChatOpenAI:
        """Initialize OpenAI LLM"""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found. Using fallback responses.")
            return None
        
        return ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            api_key=openai_api_key
        )
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create the prompt template for the LLM"""
        return ChatPromptTemplate.from_template("""
You are an AI assistant for a CTO Dashboard that helps executives understand their managed services, assignments, costs, and team metrics.

You have access to the following data about the organization:
{context_data}

Current question: {question}

Previous conversation context:
{conversation_context}

Instructions:
1. Provide clear, concise, and actionable insights
2. Use specific numbers and data when available
3. Highlight important trends or concerns
4. Suggest actionable recommendations when appropriate
5. If you don't have specific data, explain what information would be needed
6. Be professional but conversational
7. Focus on executive-level insights and strategic implications

Please provide a helpful response based on the available data.
""")
    
    def _create_chain(self):
        """Create the LangChain processing chain"""
        if not self.llm:
            return None
        
        return (
            {"context_data": RunnablePassthrough(), "question": RunnablePassthrough(), "conversation_context": RunnablePassthrough()}
            | self.prompt_template
            | self.llm
            | StrOutputParser()
        )
        
    async def process_question(self, question: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Process a user question and return an AI-generated response
        
        Args:
            question: User's question
            user_id: User identifier for conversation tracking
            
        Returns:
            Dict containing response, sources, and metadata
        """
        try:
            logger.info(f"Processing question: {question[:100]}...")
            
            # Analyze the question to determine what information is needed
            question_analysis = self._analyze_question(question)
            
            # Gather relevant data based on question analysis
            relevant_data = await self._gather_relevant_data(question_analysis)
            
            # Generate AI response using the gathered data
            response = await self._generate_response(question, relevant_data, question_analysis)
            
            # Store conversation for context
            self._store_conversation(user_id, question, response)
            
            return {
                "response": response["answer"],
                "sources": response.get("sources", []),
                "confidence": response.get("confidence", 0.8),
                "timestamp": datetime.now().isoformat(),
                "question_type": question_analysis["type"],
                "data_used": question_analysis["data_needed"]
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return {
                "response": f"I encountered an error while processing your question: {str(e)}. Please try rephrasing your question or contact support.",
                "sources": [],
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
                "question_type": "error",
                "data_used": []
            }
    
    def _analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze the question to determine what type of information is needed"""
        question_lower = question.lower()
        
        # Determine question type and data needed
        question_type = "general"
        data_needed = []
        
        # Assignment-related questions
        if any(word in question_lower for word in ["assignment", "project", "client", "engagement"]):
            question_type = "assignment"
            data_needed.append("assignments")
            
        # Metrics-related questions
        if any(word in question_lower for word in ["metric", "cost", "github", "jira", "aws", "railway", "deployment"]):
            question_type = "metrics"
            data_needed.append("metrics")
            
        # Cost-related questions
        if any(word in question_lower for word in ["cost", "budget", "spend", "expensive", "cheap", "optimize"]):
            question_type = "cost"
            data_needed.extend(["aws_insights", "cost_recommendations"])
            
        # Team-related questions
        if any(word in question_lower for word in ["team", "developer", "engineer", "staff", "people"]):
            question_type = "team"
            data_needed.append("assignments")
            
        # Technology-related questions
        if any(word in question_lower for word in ["tech", "technology", "stack", "framework", "language"]):
            question_type = "technology"
            data_needed.append("assignments")
            
        # Health/status questions
        if any(word in question_lower for word in ["status", "health", "working", "broken", "issue", "problem"]):
            question_type = "status"
            data_needed.extend(["health_status", "service_config"])
            
        return {
            "type": question_type,
            "data_needed": data_needed,
            "keywords": self._extract_keywords(question_lower)
        }
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract relevant keywords from the question"""
        keywords = []
        
        # Assignment keywords
        assignment_keywords = ["ideptech", "ilsainteractive", "assignment", "project", "client"]
        for keyword in assignment_keywords:
            if keyword in question:
                keywords.append(keyword)
        
        # Service keywords
        service_keywords = ["github", "jira", "aws", "railway", "deployment", "cost", "metric"]
        for keyword in service_keywords:
            if keyword in question:
                keywords.append(keyword)
        
        return keywords
    
    async def _gather_relevant_data(self, question_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Gather relevant data based on question analysis"""
        data = {}
        
        try:
            # Get assignments if needed
            if "assignments" in question_analysis["data_needed"]:
                assignments = self.assignment_service.get_all_assignments(include_archived=True)
                data["assignments"] = assignments
                
                # Get metrics for active assignments
                for assignment in assignments:
                    if assignment.get("status") == "active":
                        try:
                            metrics = await self.metrics_aggregator.get_all_metrics(assignment)
                            data[f"metrics_{assignment['id']}"] = metrics
                        except Exception as e:
                            logger.warning(f"Could not get metrics for {assignment['id']}: {e}")
            
            # Get AWS insights if needed
            if "aws_insights" in question_analysis["data_needed"]:
                try:
                    from metrics_service import AWSMetrics
                    aws_metrics = AWSMetrics()
                    data["aws_insights"] = aws_metrics.get_comprehensive_aws_report()
                except Exception as e:
                    logger.warning(f"Could not get AWS insights: {e}")
            
            # Get cost recommendations if needed
            if "cost_recommendations" in question_analysis["data_needed"]:
                try:
                    from metrics_service import AWSMetrics
                    aws_metrics = AWSMetrics()
                    data["cost_recommendations"] = aws_metrics._get_cost_optimization_recommendations()
                except Exception as e:
                    logger.warning(f"Could not get cost recommendations: {e}")
            
            # Get health status if needed
            if "health_status" in question_analysis["data_needed"]:
                data["health_status"] = {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "services": {
                        "github": "configured" if os.getenv("GITHUB_TOKEN") else "not_configured",
                        "jira": "configured" if os.getenv("JIRA_TOKEN") else "not_configured",
                        "aws": "configured" if os.getenv("AWS_ACCESS_KEY_ID") else "not_configured",
                        "railway": "configured" if os.getenv("RAILWAY_TOKEN") else "not_configured"
                    }
                }
            
            # Get service configuration if needed
            if "service_config" in question_analysis["data_needed"]:
                data["service_config"] = {
                    "github": {
                        "token_configured": bool(os.getenv("GITHUB_TOKEN")),
                        "org": os.getenv("GITHUB_ORG", ""),
                    },
                    "jira": {
                        "token_configured": bool(os.getenv("JIRA_TOKEN")),
                        "project_key": os.getenv("JIRA_PROJECT_KEY", ""),
                    },
                    "aws": {
                        "access_key_configured": bool(os.getenv("AWS_ACCESS_KEY_ID")),
                        "region": os.getenv("AWS_REGION", "us-east-1")
                    },
                    "railway": {
                        "token_configured": bool(os.getenv("RAILWAY_TOKEN")),
                        "project_id": os.getenv("RAILWAY_PROJECT_ID", ""),
                    }
                }
                
        except Exception as e:
            logger.error(f"Error gathering relevant data: {e}")
        
        return data
    
    async def _generate_response(self, question: str, data: Dict[str, Any], question_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI response using gathered data"""
        
        # Try to use LLM if available, otherwise fall back to rule-based
        if self.chain:
            try:
                response = await self._generate_llm_response(question, data, question_analysis)
                return response
            except Exception as e:
                logger.error(f"LLM response generation failed: {e}")
                # Fall back to rule-based response
                pass
        
        # Fallback to rule-based approach
        response = self._generate_rule_based_response(question, data, question_analysis)
        
        return {
            "answer": response["text"],
            "sources": response.get("sources", []),
            "confidence": response.get("confidence", 0.8)
        }
    
    async def _generate_llm_response(self, question: str, data: Dict[str, Any], question_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using OpenAI LLM via LangChain"""
        
        # Format context data for the LLM
        context_data = self._format_context_data(data)
        
        # Get conversation context
        conversation_context = self._get_conversation_context()
        
        # Generate response using LangChain
        response = await self.chain.ainvoke({
            "context_data": context_data,
            "question": question,
            "conversation_context": conversation_context
        })
        
        # Extract sources from the data used
        sources = self._extract_sources(data)
        
        return {
            "answer": response,
            "sources": sources,
            "confidence": 0.9  # Higher confidence for LLM responses
        }
    
    def _format_context_data(self, data: Dict[str, Any]) -> str:
        """Format the gathered data into a readable context for the LLM"""
        context_parts = []
        
        if "assignments" in data:
            assignments = data["assignments"]
            context_parts.append("ASSIGNMENTS:")
            for assignment in assignments:
                context_parts.append(f"- {assignment.get('name', 'Unknown')} (ID: {assignment.get('id', 'unknown')})")
                context_parts.append(f"  Status: {assignment.get('status', 'unknown')}")
                context_parts.append(f"  Monthly Burn Rate: ${assignment.get('monthly_burn_rate', 0):,}")
                context_parts.append(f"  Team Size: {assignment.get('team_size', 0)} people")
                context_parts.append(f"  Tech Stack: {', '.join(assignment.get('team', {}).get('tech_stack', []))}")
                context_parts.append("")
        
        if "aws_insights" in data:
            aws_data = data["aws_insights"]
            if "error" not in aws_data:
                context_parts.append("AWS COSTS & RESOURCES:")
                cost_analysis = aws_data.get("cost_analysis", {})
                if cost_analysis and "error" not in cost_analysis:
                    context_parts.append(f"- Total Cost (30 days): ${cost_analysis.get('total_cost_30_days', 0):.2f}")
                    context_parts.append(f"- Daily Average: ${cost_analysis.get('daily_average', 0):.2f}")
                    context_parts.append(f"- Cost Trend: {cost_analysis.get('weekly_trend', 'unknown')}")
                    
                    # Add service breakdown
                    service_breakdown = cost_analysis.get("service_breakdown", {})
                    if service_breakdown:
                        context_parts.append("- Top Services by Cost:")
                        for service, cost in list(service_breakdown.items())[:5]:
                            context_parts.append(f"  * {service}: ${cost:.2f}")
                
                # Add resource inventory
                for resource_type in ["lightsail_resources", "ec2_resources", "rds_resources", "route53_resources", "s3_resources"]:
                    if resource_type in aws_data:
                        resource_data = aws_data[resource_type]
                        if "error" not in resource_data:
                            context_parts.append(f"- {resource_type.replace('_', ' ').title()}: {resource_data}")
                context_parts.append("")
        
        if "cost_recommendations" in data:
            recommendations = data["cost_recommendations"]
            if recommendations:
                context_parts.append("COST OPTIMIZATION RECOMMENDATIONS:")
                for rec in recommendations[:10]:  # Limit to first 10
                    if rec.strip():
                        context_parts.append(f"- {rec}")
                context_parts.append("")
        
        # Add metrics data
        for key, value in data.items():
            if key.startswith("metrics_") and isinstance(value, dict):
                assignment_id = key.replace("metrics_", "")
                context_parts.append(f"METRICS FOR {assignment_id.upper()}:")
                
                if "github" in value:
                    github_data = value["github"]
                    if isinstance(github_data, list) and github_data:
                        total_commits = sum(repo.get("commits_last_30_days", 0) for repo in github_data)
                        context_parts.append(f"- GitHub: {total_commits} commits in last 30 days across {len(github_data)} repos")
                
                if "aws" in value:
                    aws_data = value["aws"]
                    if "error" not in aws_data:
                        cost = aws_data.get("total_cost_last_30_days", 0)
                        context_parts.append(f"- AWS: ${cost:.2f} in last 30 days")
                
                if "jira" in value:
                    jira_data = value["jira"]
                    if "error" not in jira_data:
                        issues = jira_data.get("total_issues_last_30_days", 0)
                        context_parts.append(f"- Jira: {issues} issues in last 30 days")
                
                context_parts.append("")
        
        if "health_status" in data:
            health = data["health_status"]
            context_parts.append("SERVICE HEALTH:")
            services = health.get("services", {})
            configured_services = [name for name, status in services.items() if status == "configured"]
            not_configured_services = [name for name, status in services.items() if status == "not_configured"]
            
            if configured_services:
                context_parts.append(f"- Configured: {', '.join(configured_services)}")
            if not_configured_services:
                context_parts.append(f"- Not Configured: {', '.join(not_configured_services)}")
            context_parts.append("")
        
        return "\n".join(context_parts) if context_parts else "No specific data available."
    
    def _get_conversation_context(self) -> str:
        """Get recent conversation context for the LLM"""
        if not self.conversation_history:
            return "No previous conversation."
        
        recent_conversations = self.conversation_history[-3:]  # Last 3 conversations
        context_parts = []
        
        for conv in recent_conversations:
            context_parts.append(f"Q: {conv['question']}")
            context_parts.append(f"A: {conv['response'][:200]}...")  # Truncate long responses
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _extract_sources(self, data: Dict[str, Any]) -> List[str]:
        """Extract source information from the data"""
        sources = []
        
        if "assignments" in data:
            sources.append("Assignment Service")
        
        if "aws_insights" in data:
            sources.append("AWS Cost Explorer")
        
        if "cost_recommendations" in data:
            sources.append("AWS Cost Analysis")
        
        if any(key.startswith("metrics_") for key in data.keys()):
            sources.append("Metrics Aggregator")
        
        if "health_status" in data:
            sources.append("Service Configuration")
        
        return sources
    
    def _generate_rule_based_response(self, question: str, data: Dict[str, Any], question_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using rule-based logic"""
        
        question_lower = question.lower()
        response_parts = []
        sources = []
        confidence = 0.8
        
        # Assignment-related responses
        if question_analysis["type"] == "assignment" and "assignments" in data:
            assignments = data["assignments"]
            
            if "how many" in question_lower or "count" in question_lower:
                active_count = len([a for a in assignments if a.get("status") == "active"])
                total_count = len(assignments)
                response_parts.append(f"You have {active_count} active assignments out of {total_count} total assignments.")
                sources.append("Assignment Service")
                
            elif "list" in question_lower or "show" in question_lower:
                active_assignments = [a for a in assignments if a.get("status") == "active"]
                if active_assignments:
                    response_parts.append("Here are your active assignments:")
                    for assignment in active_assignments[:5]:  # Limit to 5
                        response_parts.append(f"• {assignment['name']} (ID: {assignment['id']}) - ${assignment['monthly_burn_rate']}/month")
                    sources.append("Assignment Service")
                else:
                    response_parts.append("No active assignments found.")
                    
            elif "burn rate" in question_lower or "cost" in question_lower:
                total_burn = sum(a.get("monthly_burn_rate", 0) for a in assignments if a.get("status") == "active")
                response_parts.append(f"Total monthly burn rate across all active assignments: ${total_burn:,}")
                sources.append("Assignment Service")
        
        # Cost-related responses
        if question_analysis["type"] == "cost" and "aws_insights" in data:
            aws_data = data["aws_insights"]
            if "error" not in aws_data:
                cost_analysis = aws_data.get("cost_analysis", {})
                if cost_analysis and "error" not in cost_analysis:
                    total_cost = cost_analysis.get("total_cost_30_days", 0)
                    daily_avg = cost_analysis.get("daily_average", 0)
                    trend = cost_analysis.get("weekly_trend", "unknown")
                    
                    response_parts.append(f"AWS costs for the last 30 days: ${total_cost:.2f}")
                    response_parts.append(f"Daily average: ${daily_avg:.2f}")
                    response_parts.append(f"Cost trend: {trend}")
                    sources.append("AWS Cost Explorer")
                    
                    # Add cost optimization recommendations
                    if "cost_recommendations" in data:
                        recommendations = data["cost_recommendations"]
                        if recommendations:
                            response_parts.append("\nCost optimization recommendations:")
                            for rec in recommendations[:3]:  # Show first 3 recommendations
                                if rec.strip() and not rec.startswith("🎯"):
                                    response_parts.append(f"• {rec}")
                            sources.append("AWS Cost Analysis")
        
        # Team-related responses
        if question_analysis["type"] == "team" and "assignments" in data:
            assignments = data["assignments"]
            active_assignments = [a for a in assignments if a.get("status") == "active"]
            
            if "team size" in question_lower or "people" in question_lower:
                total_team_size = sum(a.get("team_size", 0) for a in active_assignments)
                response_parts.append(f"Total team size across all active assignments: {total_team_size} people")
                sources.append("Assignment Service")
                
            elif "roles" in question_lower:
                all_roles = set()
                for assignment in active_assignments:
                    roles = assignment.get("team", {}).get("roles", [])
                    all_roles.update(roles)
                
                if all_roles:
                    response_parts.append(f"Team roles across all assignments: {', '.join(sorted(all_roles))}")
                    sources.append("Assignment Service")
        
        # Technology-related responses
        if question_analysis["type"] == "technology" and "assignments" in data:
            assignments = data["assignments"]
            active_assignments = [a for a in assignments if a.get("status") == "active"]
            
            if "tech stack" in question_lower or "technology" in question_lower:
                all_tech = set()
                for assignment in active_assignments:
                    tech_stack = assignment.get("team", {}).get("tech_stack", [])
                    all_tech.update(tech_stack)
                
                if all_tech:
                    response_parts.append(f"Technologies used across all assignments: {', '.join(sorted(all_tech))}")
                    sources.append("Assignment Service")
        
        # Status-related responses
        if question_analysis["type"] == "status":
            if "health_status" in data:
                health = data["health_status"]
                services = health.get("services", {})
                
                configured_services = [name for name, status in services.items() if status == "configured"]
                not_configured_services = [name for name, status in services.items() if status == "not_configured"]
                
                if configured_services:
                    response_parts.append(f"Configured services: {', '.join(configured_services)}")
                if not_configured_services:
                    response_parts.append(f"Services not configured: {', '.join(not_configured_services)}")
                
                sources.append("Service Configuration")
        
        # Metrics-related responses
        if question_analysis["type"] == "metrics":
            metrics_data = {k: v for k, v in data.items() if k.startswith("metrics_")}
            
            if metrics_data:
                response_parts.append("Here's what I found about your metrics:")
                
                for assignment_id, metrics in metrics_data.items():
                    assignment_id = assignment_id.replace("metrics_", "")
                    response_parts.append(f"\n**{assignment_id}:**")
                    
                    if "github" in metrics:
                        github_data = metrics["github"]
                        if isinstance(github_data, list) and github_data:
                            total_commits = sum(repo.get("commits_last_30_days", 0) for repo in github_data)
                            response_parts.append(f"• GitHub: {total_commits} commits in last 30 days across {len(github_data)} repos")
                    
                    if "aws" in metrics:
                        aws_data = metrics["aws"]
                        if "error" not in aws_data:
                            cost = aws_data.get("total_cost_last_30_days", 0)
                            response_parts.append(f"• AWS: ${cost:.2f} in last 30 days")
                    
                    if "jira" in metrics:
                        jira_data = metrics["jira"]
                        if "error" not in jira_data:
                            issues = jira_data.get("total_issues_last_30_days", 0)
                            response_parts.append(f"• Jira: {issues} issues in last 30 days")
                
                sources.append("Metrics Aggregator")
        
        # Default response if no specific match
        if not response_parts:
            response_parts.append("I can help you with questions about:")
            response_parts.append("• Assignments and projects")
            response_parts.append("• Metrics and costs")
            response_parts.append("• Team information")
            response_parts.append("• Technology stacks")
            response_parts.append("• Service status")
            response_parts.append("\nPlease ask me a specific question about your managed services!")
            confidence = 0.6
        
        return {
            "text": "\n".join(response_parts),
            "sources": sources,
            "confidence": confidence
        }
    
    def _store_conversation(self, user_id: str, question: str, response: Dict[str, Any]):
        """Store conversation for context (simple in-memory storage)"""
        conversation_entry = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response["answer"],
            "confidence": response.get("confidence", 0.8)
        }
        
        self.conversation_history.append(conversation_entry)
        
        # Keep only last 50 conversations to prevent memory issues
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
    
    def get_conversation_history(self, user_id: str = "default", limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a user"""
        user_conversations = [
            conv for conv in self.conversation_history 
            if conv["user_id"] == user_id
        ]
        return user_conversations[-limit:] if user_conversations else []
    
    def clear_conversation_history(self, user_id: str = "default"):
        """Clear conversation history for a user"""
        self.conversation_history = [
            conv for conv in self.conversation_history 
            if conv["user_id"] != user_id
        ]

# Global chatbot service instance
chatbot_service = ChatbotService()
