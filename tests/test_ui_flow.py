#!/usr/bin/env python3
"""Test the UI flow with mock socketio to see what gets emitted."""

import asyncio
import sys
sys.path.insert(0, '.')

from unittest.mock import MagicMock
from nodes import agent, rag_node
import pocketflow as pf

class MockSocketIO:
    def __init__(self):
        self.emits = []
        self.emit = MagicMock(side_effect=self._emit)
    
    def _emit(self, event, data=None):
        self.emits.append((event, data))
        print(f"[SocketIO] emit: {event} -> {data}")

async def test_ui_flow():
    print("Testing UI flow with mock socketio...")
    
    # Create flow
    test_flow = pf.AsyncFlow(start=agent)
    agent - "retrieve_memory" >> rag_node >> agent
    
    # Mock socketio
    mock_socketio = MockSocketIO()
    
    # Simulate conversation state (like app.py)
    shared = {
        "history": [
            {"role": "user", "content": "What is your origin story?"}
        ],
        "loop_count": 0,
        "memory_action": "",
        "retrieved_memory": "",
        "socketio": mock_socketio,
        "memory_context": None
    }
    
    print("Running flow...")
    try:
        await test_flow.run_async(shared)
        print("Flow completed.")
        
        # Print all socketio emits
        print(f"\nTotal emits: {len(mock_socketio.emits)}")
        for i, (event, data) in enumerate(mock_socketio.emits):
            print(f"{i}: {event}: {data}")
            
        # Check what's in history
        print(f"\nFinal history length: {len(shared['history'])}")
        for i, msg in enumerate(shared['history']):
            print(f"{i}: {msg['role']}: {msg['content'][:80]}...")
            
        # Check if memory was retrieved
        if shared.get('retrieved_memory'):
            print(f"\nRetrieved memory: {shared['retrieved_memory'][:100]}...")
        else:
            print("\nNo memory retrieved.")
            
        # Check if guard emitted a stream_chunk
        stream_emits = [e for e in mock_socketio.emits if e[0] == 'stream_chunk']
        print(f"\nStream chunks emitted: {len(stream_emits)}")
        for event, data in stream_emits:
            print(f"  Content: {data.get('content', '')[:80]}...")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ui_flow())