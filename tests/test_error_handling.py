#!/usr/bin/env python3
"""
Test error handling when Ollama is not running.
"""
import asyncio
import sys
sys.path.insert(0, '.')

async def test_ollama_connection_error():
    """Test that the agent provides a helpful error when Ollama is not running."""
    print("=== Testing Ollama Connection Error Handling ===")
    print("(Ollama should NOT be running for this test)")
    print()
    
    from orchestration import my_async_flow
    
    # Shared state without socketio (will be None)
    shared = {
        "history": [
            {"role": "user", "content": "Hello, who are you?"}
        ],
        "loop_count": 0,
        "socketio": None  # No frontend socket
    }
    
    try:
        print("Running flow (should timeout quickly if infinite loop)...")
        result = await asyncio.wait_for(
            my_async_flow.run_async(shared),
            timeout=10.0
        )
        
        print(f"Flow completed. Result: {result}")
        print(f"Loop count: {shared.get('loop_count', 0)}")
        
        # Check agent response
        agent_msgs = [msg for msg in shared['history'] if msg['role'] == 'agent']
        if agent_msgs:
            last_response = agent_msgs[-1]['content']
            print(f"\nAgent response: {last_response}")
            
            # Should contain error message about Ollama
            if "Ollama" in last_response or "connect" in last_response.lower():
                print("\n✅ Error handling works - agent returned helpful error message")
                return True
            else:
                print("\n❌ Agent response does not mention Ollama/connection issue")
                print(f"   Response: {last_response}")
                return False
        else:
            print("\n❌ No agent response generated")
            return False
            
    except asyncio.TimeoutError:
        print("\n❌ TIMEOUT - Flow did not complete within 10 seconds")
        print("   Possible infinite loop despite error handling")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_ollama_connection_error()
    
    if success:
        print(f"\n{'='*60}")
        print("✅ Error handling test passed!")
        print("   The agent provides a helpful error when Ollama is not running.")
        sys.exit(0)
    else:
        print(f"\n{'='*60}")
        print("❌ Error handling test failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())