#!/usr/bin/env python3
"""Test the guard case where model outputs retrieve_memory after memory is already retrieved."""

import asyncio
import sys
sys.path.insert(0, '.')

from unittest.mock import AsyncMock, patch, MagicMock
from nodes import Agent

async def test_guard_response():
    print("Testing guard case response emission...")
    
    # Create agent with mock LLM
    agent = Agent("phi4-mini", "Test prompt")
    
    # Mock the call_llm_stream to return retrieve_memory
    async def mock_call_llm_stream(messages, model):
        # Simulate chunks for "retrieve_memory"
        chunks = [
            type('Chunk', (), {
                'message': type('Message', (), {
                    'content': 'retrieve',
                    'role': 'assistant'
                })()
            })(),
            type('Chunk', (), {
                'message': type('Message', (), {
                    'content': '_memory',
                    'role': 'assistant'
                })()
            })()
        ]
        for chunk in chunks:
            yield chunk
    
    # Mock socketio
    mock_socketio = MagicMock()
    
    # Test with memory present (simulating already retrieved memory)
    with patch('nodes.call_llm_stream', mock_call_llm_stream):
        # First, test exec_async with memory present
        history = [{"role": "user", "content": "What's my name?"}]
        memory = "User's name is John."
        
        # We need to test the full flow, but let's check the guard logic directly
        # Simulate what happens in post_async
        exec_res = "retrieve_memory"
        is_retrieve_command = agent._is_retrieve_command(exec_res)
        print(f"is_retrieve_command: {is_retrieve_command}")
        
        # The guard logic
        if is_retrieve_command and memory:
            print("Guard triggered: memory exists but model output retrieve_memory")
            if ": " in memory:
                memory_content = memory.split(": ", 1)[1]
                exec_res = f"According to my memory, {memory_content}"
            else:
                exec_res = f"I recall that {memory}"
            
            print(f"Generated response: {exec_res}")
            
            # Check if socketio would emit
            print("Socketio emit would be called here")
            
        print("Test completed - guard logic works")
        
        # Now test the actual post_async method
        shared = {
            "history": history.copy(),
            "loop_count": 0,
            "memory_action": "",
            "retrieved_memory": memory
        }
        
        # We need to mock prep_res
        prep_res = (history, "What's my name?", memory, mock_socketio)
        
        # Call post_async
        result = await agent.post_async(shared, prep_res, "retrieve_memory")
        print(f"post_async returned: {result}")
        print(f"History updated: {shared['history'][-1] if shared['history'] else 'empty'}")
        
        # Check if socketio.emit was called
        if mock_socketio.emit.called:
            print(f"Socketio.emit called with: {mock_socketio.emit.call_args}")
        else:
            print("Socketio.emit was NOT called (no socketio in test)")

if __name__ == "__main__":
    asyncio.run(test_guard_response())