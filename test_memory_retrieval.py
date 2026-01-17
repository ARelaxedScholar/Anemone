#!/usr/bin/env python3
"""Test memory retrieval for specific query."""
import asyncio
import sys
sys.path.insert(0, '.')

from orchestration import my_async_flow

async def test_query(query):
    """Test a specific query that should trigger memory retrieval."""
    print(f"=== Testing query: '{query}' ===")
    
    shared = {
        "history": [
            {"role": "user", "content": query}
        ],
        "loop_count": 0
    }
    
    try:
        print("Running flow...")
        result = await asyncio.wait_for(
            my_async_flow.run_async(shared),
            timeout=30.0
        )
        
        print(f"Flow completed. Result: {result}")
        print(f"Loop count: {shared.get('loop_count', 0)}")
        
        # Check if memory was retrieved
        retrieved = shared.get('retrieved_memory')
        if retrieved:
            print(f"Memory was retrieved: {retrieved[:100]}...")
        else:
            print("No memory was retrieved (or was cleared)")
        
        # Check agent response
        agent_msgs = [msg for msg in shared['history'] if msg['role'] == 'agent']
        if agent_msgs:
            last_response = agent_msgs[-1]['content']
            print(f"Agent response ({len(last_response)} chars): {last_response[:150]}...")
            if "retrieve_memory" in last_response.lower():
                print("WARNING: Agent response still contains 'retrieve_memory' command")
            if "<|assistant|>" in last_response:
                print("WARNING: Agent response contains '<|assistant|>' token")
        else:
            print("No agent response generated")
        
        return True
        
    except asyncio.TimeoutError:
        print("TIMEOUT - Possible infinite loop")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run tests for different queries."""
    queries = [
        "Why are you named Anemone?",
        "What is your function?",
        "Who is Bartholomew?",
        "Tell me a joke"
    ]
    
    all_passed = True
    for query in queries:
        print(f"\n{'='*60}")
        if not await test_query(query):
            all_passed = False
    
    if all_passed:
        print(f"\n{'='*60}")
        print("All tests passed!")
        sys.exit(0)
    else:
        print(f"\n{'='*60}")
        print("Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())