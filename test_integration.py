#!/usr/bin/env python3
"""
Integration test for memory retrieval loop fix.
Uses real Ollama model to test actual behavior.
"""
import asyncio
import sys
import signal

sys.path.insert(0, '.')

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Test timed out - possible infinite loop")

async def run_memory_retrieval_test():
    """Run actual flow with real LLM to test for infinite loops."""
    print("=== Integration Test: Memory Retrieval ===")
    print("This test uses the real phi4-mini model and seeded memory.")
    print("Asking: 'What is your function?'")
    print("This should trigger memory retrieval exactly once.")
    print()
    
    from orchestration import my_async_flow
    
    shared = {
        "history": [
            {"role": "user", "content": "What is your function?"}
        ],
        "loop_count": 0
    }
    
    # Set timeout alarm
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)  # 30 second timeout
    
    try:
        print("Starting flow...")
        result = await my_async_flow.run_async(shared)
        signal.alarm(0)  # Disable alarm
        
        print(f"\nFlow completed. Result: {result}")
        print(f"Final loop_count: {shared.get('loop_count', 0)}")
        print(f"Retrieved memory present: {'retrieved_memory' in shared and shared['retrieved_memory']}")
        print(f"Memory action: {shared.get('memory_action', '')}")
        
        # Check history
        print(f"\nConversation history ({len(shared['history'])} messages):")
        for i, msg in enumerate(shared['history']):
            prefix = "User: " if msg['role'] == 'user' else "Agent: "
            content = msg['content']
            # Truncate long content
            if len(content) > 100:
                content = content[:100] + "..."
            print(f"  {i}. {prefix}{content}")
        
        # Verify no infinite loop
        # The flow should complete with agent response, not stuck retrieving
        agent_responses = [msg for msg in shared['history'] if msg['role'] == 'agent']
        if not agent_responses:
            print("\n✗ No agent response generated")
            return False
        
        last_response = agent_responses[-1]['content']
        if "retrieve_memory" in last_response.lower():
            print("\n✗ Agent response still contains 'retrieve_memory' command")
            return False
        
        # Check that retrieval happened at most once
        # We can't easily count retrievals, but we can check logs
        print("\n✓ Flow completed without timeout")
        print("✓ Agent generated a proper response")
        print("✓ No 'retrieve_memory' in final response")
        return True
        
    except TimeoutException:
        print("\n✗ TEST TIMEOUT - Infinite loop detected!")
        print("The flow did not complete within 30 seconds.")
        print("This indicates the memory retrieval loop is still occurring.")
        return False
    except Exception as e:
        signal.alarm(0)
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        success = loop.run_until_complete(run_memory_retrieval_test())
    finally:
        loop.close()
    
    if success:
        print("\n✓ Integration test passed!")
        sys.exit(0)
    else:
        print("\n✗ Integration test failed.")
        sys.exit(1)