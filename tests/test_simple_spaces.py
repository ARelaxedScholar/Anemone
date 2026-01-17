#!/usr/bin/env python3
"""Simple test for spacing with a greeting."""
import asyncio
import sys
sys.path.insert(0, '.')

class MockSocketIO:
    def __init__(self):
        self.emitted_chunks = []
    
    def emit(self, event, data):
        if event == 'stream_chunk':
            self.emitted_chunks.append(data['content'])

async def test():
    from orchestration import my_async_flow
    
    mock_socketio = MockSocketIO()
    shared = {
        "history": [
            {"role": "user", "content": "Hello"}
        ],
        "loop_count": 0,
        "socketio": mock_socketio
    }
    
    print("Testing simple greeting...")
    try:
        result = await asyncio.wait_for(
            my_async_flow.run_async(shared),
            timeout=15.0
        )
        
        concatenated = ''.join(mock_socketio.emitted_chunks)
        print(f"Total chunks: {len(mock_socketio.emitted_chunks)}")
        print(f"Concatenated length: {len(concatenated)}")
        print(f"Concatenated text: '{concatenated}'")
        print(f"Concatenated repr: {repr(concatenated)}")
        
        # Show first 10 chunks
        for i, chunk in enumerate(mock_socketio.emitted_chunks[:10]):
            print(f"Chunk {i}: repr={repr(chunk)}")
        
        # Check for obvious missing spaces
        if 'Hello' in concatenated:
            print("Contains 'Hello'")
        if '  ' in concatenated:
            print("Contains double spaces")
        
        # Look for run-together words
        import re
        words = re.findall(r'[a-zA-Z]{2,}', concatenated)
        for word in words[:20]:
            print(f"Word: {word}")
        
        return True
        
    except asyncio.TimeoutError:
        print("TIMEOUT")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test())