#!/usr/bin/env python3
"""
Test the fixes for memory retrieval loop.
"""
import asyncio
import sys
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, '.')

async def test_memory_retrieval_flow():
    """Test the complete flow with mocked LLM."""
    print("=== Testing Memory Retrieval Flow Fix ===")
    
    # Mock the LLM to simulate phi4-mini's problematic behavior
    with patch('nodes.call_llm_stream') as mock_stream, \
         patch('nodes.call_llm') as mock_call, \
         patch('memory.ChromaMemory') as mock_memory:
        
        # Setup mock memory
        mock_memory_instance = MagicMock()
        mock_memory.return_value = mock_memory_instance
        mock_memory_instance.retrieve_memory.return_value = (
            "Why are you named Anemone?", 
            [["Origin Story: My name, Anemone, was chosen because I am beautiful, mysterious, and have a surprisingly potent sting if you try to debug my code without proper authorization."]]
        )
        mock_memory_instance.save_memory = MagicMock()
        
        # Track calls to see flow
        calls = []
        
        async def mock_stream_generator(messages, model):
            """Mock streaming that simulates phi4-mini's behavior."""
            calls.append(('stream', messages, model))
            
            # Check if there's memory context in messages
            has_memory = any("<retrieved_memory>" in str(msg.get('content', '')) for msg in messages)
            has_retrieve_instruction = any("retrieve_memory" in str(msg.get('content', '')) for msg in messages)
            
            print(f"Mock LLM called with {len(messages)} messages")
            print(f"  Has memory context: {has_memory}")
            print(f"  Has retrieve instruction: {has_retrieve_instruction}")
            
            if has_memory:
                # Should answer using memory
                mock_chunk = MagicMock()
                mock_message = MagicMock()
                mock_message.content = "I am named Anemone because I am beautiful, mysterious, and have a surprisingly potent sting if you try to debug my code without proper authorization."
                mock_chunk.message = mock_message
                yield mock_chunk
            else:
                # Should output retrieve_memory command (but phi4-mini might add extra)
                # Simulate phi4-mini's problematic output
                mock_chunk1 = MagicMock()
                mock_message1 = MagicMock()
                mock_message1.content = "retrieve_memory"
                mock_chunk1.message = mock_message1
                yield mock_chunk1
                
                # phi4-mini might add more
                mock_chunk2 = MagicMock()
                mock_message2 = MagicMock()
                mock_message2.content = " RETRIEVED MEMORIES: "
                mock_chunk2.message = mock_message2
                yield mock_chunk2
        
        mock_stream.side_effect = mock_stream_generator
        
        from orchestration import my_async_flow
        
        # Test 1: Query that should trigger memory retrieval
        print("\nTest 1: Query about name")
        shared = {
            "history": [
                {"role": "user", "content": "Why are you named Anemone?"}
            ],
            "loop_count": 0,
            "socketio": None  # No frontend
        }
        
        try:
            result = await asyncio.wait_for(
                my_async_flow.run_async(shared),
                timeout=10.0
            )
            
            print(f"  Flow result: {result}")
            print(f"  Loop count: {shared.get('loop_count', 0)}")
            print(f"  Memory retrieved: {shared.get('retrieved_memory', 'None')[:50]}...")
            
            # Check that memory was retrieved
            assert mock_memory_instance.retrieve_memory.called
            print("  ✓ Memory retrieval called")
            
            # Check agent response in history
            agent_msgs = [msg for msg in shared['history'] if msg['role'] == 'agent']
            user_msgs = [msg for msg in shared['history'] if msg['role'] == 'user']
            
            print(f"  User messages: {len(user_msgs)}")
            print(f"  Agent messages: {len(agent_msgs)}")
            
            if agent_msgs:
                last_response = agent_msgs[-1]['content']
                print(f"  Last agent response ({len(last_response)} chars): {last_response[:80]}...")
                
                # Should NOT contain retrieve_memory command
                if "retrieve_memory" in last_response.lower():
                    print("  ✗ Agent response still contains 'retrieve_memory'")
                    return False
                # Should contain memory content
                if "Anemone" in last_response and "beautiful" in last_response:
                    print("  ✓ Agent response uses memory content")
                else:
                    print("  ? Agent response might not use memory")
            else:
                print("  ✗ No agent response generated")
                return False
            
            return True
            
        except asyncio.TimeoutError:
            print("  ✗ TIMEOUT - Infinite loop")
            return False
        except AssertionError as e:
            print(f"  ✗ Assertion failed: {e}")
            return False

async def main():
    success = await test_memory_retrieval_flow()
    
    if success:
        print(f"\n{'='*60}")
        print("✅ Memory retrieval flow test passed!")
        print("   The fixes should prevent the infinite loop.")
        sys.exit(0)
    else:
        print(f"\n{'='*60}")
        print("❌ Test failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())