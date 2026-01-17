#!/usr/bin/env python3
"""Test the guard fix for memory retrieval loop."""

import asyncio
import sys
sys.path.insert(0, '.')

from nodes import agent, rag_node
import pocketflow as pf

async def test_guard():
    print("Testing memory retrieval guard...")
    
    # Create a simple flow
    test_flow = pf.AsyncFlow(start=agent)
    agent - "retrieve_memory" >> rag_node >> agent
    
    # Simulate conversation state
    shared = {
        "history": [
            {"role": "user", "content": "What is your origin story?"}
        ],
        "loop_count": 0,
        "memory_action": "",
        "retrieved_memory": "",
        "socketio": None  # No socketio for test
    }
    
    print("Running flow...")
    try:
        await test_flow.run_async(shared)
        print("Flow completed without infinite loop!")
        
        # Check history
        print(f"\nFinal history length: {len(shared['history'])}")
        for i, msg in enumerate(shared['history']):
            print(f"{i}: {msg['role']}: {msg['content'][:50]}...")
            
        # Check if memory was retrieved
        if shared.get('memory_action'):
            print(f"Memory action: {shared['memory_action']}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_guard())