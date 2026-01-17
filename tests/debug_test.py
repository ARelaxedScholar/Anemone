#!/usr/bin/env python3
"""Debug test for memory retrieval."""
import asyncio
import sys
sys.path.insert(0, '.')

from orchestration import my_async_flow

async def test():
    shared = {
        "history": [
            {"role": "user", "content": "What is your function?"}
        ],
        "loop_count": 0
    }
    
    print("Starting flow...")
    try:
        result = await asyncio.wait_for(
            my_async_flow.run_async(shared),
            timeout=15.0
        )
        print(f"Flow completed: {result}")
        print(f"History: {shared['history']}")
        return True
    except asyncio.TimeoutError:
        print("TIMEOUT!")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test())