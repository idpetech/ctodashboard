#!/usr/bin/env python3
"""
Test script for the CTO Dashboard Chatbot

This script tests the chatbot functionality to ensure it's working correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from chatbot_service import chatbot_service

async def test_chatbot():
    """Test the chatbot with various questions"""
    
    test_questions = [
        "How many assignments do we have?",
        "What's our total monthly burn rate?",
        "Show me AWS costs",
        "What's our team size?",
        "What technologies are we using?",
        "Are our services healthy?",
        "Show me GitHub activity",
        "What's the status of our Jira projects?",
        "Give me cost optimization recommendations",
        "What's the health status of our services?"
    ]
    
    print("🤖 Testing CTO Dashboard Chatbot")
    print("=" * 50)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Question: {question}")
        print("-" * 30)
        
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
    
    print("=" * 50)
    print("✅ Chatbot testing completed!")

def test_conversation_history():
    """Test conversation history functionality"""
    
    print("\n📚 Testing Conversation History")
    print("=" * 30)
    
    # Get history
    history = chatbot_service.get_conversation_history()
    print(f"Total conversations: {len(history)}")
    
    if history:
        print("\nRecent conversations:")
        for conv in history[-3:]:  # Show last 3
            print(f"- {conv['question'][:50]}... -> {conv['response'][:50]}...")
    
    # Clear history
    chatbot_service.clear_conversation_history()
    print("\n🧹 History cleared")
    
    # Verify it's cleared
    history_after = chatbot_service.get_conversation_history()
    print(f"Conversations after clear: {len(history_after)}")

if __name__ == "__main__":
    # Run async test
    asyncio.run(test_chatbot())
    
    # Run sync test
    test_conversation_history()

