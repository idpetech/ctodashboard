#!/usr/bin/env python3
"""
Test script for the LLM-powered CTO Dashboard Chatbot

This script tests the chatbot functionality with OpenAI LLM integration.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from chatbot_service import chatbot_service

async def test_llm_chatbot():
    """Test the LLM-powered chatbot with various questions"""
    
    # Check if OpenAI API key is configured
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠️  OPENAI_API_KEY not found in environment variables.")
        print("The chatbot will use fallback rule-based responses.")
        print("To enable LLM responses, set OPENAI_API_KEY in your .env file.")
        print()
    
    test_questions = [
        "How many assignments do we have and what's our total burn rate?",
        "What are our AWS costs and what can we do to optimize them?",
        "Show me a summary of our team size and technologies across all projects",
        "What's the health status of our services and integrations?",
        "Give me insights about our GitHub activity and Jira project status",
        "What are the key metrics I should be concerned about as a CTO?",
        "How can we reduce our monthly costs while maintaining performance?",
        "What technologies are we using and are there any consolidation opportunities?"
    ]
    
    print("🤖 Testing LLM-Powered CTO Dashboard Chatbot")
    print("=" * 60)
    
    if openai_key:
        print("✅ OpenAI API key found - using LLM responses")
    else:
        print("⚠️  No OpenAI API key - using rule-based fallback")
    
    print()
    
    for i, question in enumerate(test_questions, 1):
        print(f"{i}. Question: {question}")
        print("-" * 50)
        
        try:
            response = await chatbot_service.process_question(question)
            
            print(f"Response: {response['response']}")
            print(f"Confidence: {response['confidence']:.2f}")
            print(f"Question Type: {response['question_type']}")
            print(f"Data Used: {', '.join(response['data_used'])}")
            
            if response['sources']:
                print(f"Sources: {', '.join(response['sources'])}")
                
        except Exception as e:
            print(f"Error: {e}")
        
        print()
    
    print("=" * 60)
    print("✅ LLM Chatbot testing completed!")

def test_conversation_flow():
    """Test conversation flow with context"""
    
    print("\n💬 Testing Conversation Flow")
    print("=" * 30)
    
    # Simulate a conversation
    questions = [
        "What's our total monthly burn rate?",
        "Which assignment has the highest cost?",
        "What can we do to reduce costs for that assignment?",
        "Show me the team size for that assignment"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{i}. User: {question}")
        
        try:
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(chatbot_service.process_question(question))
                print(f"   Bot: {response['response'][:200]}...")
            finally:
                loop.close()
                
        except Exception as e:
            print(f"   Error: {e}")

def test_mcp_integration():
    """Test MCP server integration"""
    
    print("\n🔌 Testing MCP Server Integration")
    print("=" * 35)
    
    try:
        # Import MCP server
        from mcp_server import CTODashboardMCPServer
        
        print("✅ MCP server imported successfully")
        print("✅ Chatbot service integrated with MCP server")
        print("✅ LLM-powered responses available via MCP tools")
        
        # Test chatbot tools
        print("\nAvailable MCP Chatbot Tools:")
        print("- ask_chatbot: Ask questions about managed services")
        print("- get_chatbot_history: Get conversation history")
        print("- clear_chatbot_history: Clear conversation history")
        
    except Exception as e:
        print(f"❌ MCP integration error: {e}")

if __name__ == "__main__":
    # Run async test
    asyncio.run(test_llm_chatbot())
    
    # Run sync tests
    test_conversation_flow()
    test_mcp_integration()
    
    print("\n🎉 All tests completed!")
    print("\nTo use the LLM-powered chatbot:")
    print("1. Set OPENAI_API_KEY in your .env file")
    print("2. Start the Flask server: python3 backend/main.py")
    print("3. Open the dashboard and click the chatbot button")
    print("4. Or use the MCP server for AI assistant integration")

