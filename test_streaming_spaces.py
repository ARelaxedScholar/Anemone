#!/usr/bin/env python3
"""Test streaming spaces with mock socketio."""
import asyncio
import sys
sys.path.insert(0, '.')

class MockSocketIO:
    def __init__(self):
        self.emitted_chunks = []
    
    def emit(self, event, data):
        if event == 'stream_chunk':
            self.emitted_chunks.append(data['content'])
            print(f"MockSocketIO emitted chunk: repr='{repr(data['content'])}'")

async def test():
    from orchestration import my_async_flow
    
    mock_socketio = MockSocketIO()
    shared = {
        "history": [
            {"role": "user", "content": "What is your function?"}
        ],
        "loop_count": 0,
        "socketio": mock_socketio
    }
    
    print("Starting flow with mock socketio...")
    try:
        result = await asyncio.wait_for(
            my_async_flow.run_async(shared),
            timeout=30.0
        )
        print(f"Flow completed: {result}")
        print(f"Total chunks emitted: {len(mock_socketio.emitted_chunks)}")
        
        # Concatenate all chunks
        concatenated = ''.join(mock_socketio.emitted_chunks)
        print(f"Concatenated chunks ({len(concatenated)} chars): '{concatenated[:200]}...'")
        print(f"Concatenated chunks repr: {repr(concatenated[:200])}")
        
        # Compare with final agent response
        agent_msgs = [msg for msg in shared['history'] if msg['role'] == 'agent']
        if agent_msgs:
            final = agent_msgs[-1]['content']
            print(f"Final agent response ({len(final)} chars): '{final[:200]}...'")
            print(f"Final agent response repr: {repr(final[:200])}")
        
        # Check for missing spaces
        if '  ' in concatenated:
            print("WARNING: Double spaces in concatenated")
        if 'Core Directive' in concatenated:
            print("Found 'Core Directive' in concatenated")
        if 'CoreDirective' in concatenated:
            print("ERROR: 'CoreDirective' missing space!")
        
        # Show chunk details
        for i, chunk in enumerate(mock_socketio.emitted_chunks[:20]):
            print(f"Chunk {i}: repr={repr(chunk)}")
        
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