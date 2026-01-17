#!/usr/bin/env python3
"""
Mock integration test for memory retrieval loop fix.
Mocks LLM calls to test flow logic without requiring Ollama.
"""
import asyncio
import sys
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, '.')

async def test_memory_retrieval_guard():
    """Test that memory guard prevents infinite retrieval loops."""
    print("=== Mock Test: Memory Retrieval Guard ===")
    
    # Mock the LLM calls
    with patch('nodes.call_llm_stream') as mock_stream, \
         patch('nodes.call_llm') as mock_call, \
         patch('memory.ChromaMemory') as mock_memory:
        
        # Setup mock memory
        mock_memory_instance = MagicMock()
        mock_memory.return_value = mock_memory_instance
        mock_memory_instance.retrieve_memory.return_value = (
            "What is your function?", 
            [["Origin Story: I am named Anemone after the sea anemone, a creature that forms symbiotic relationships with others. My function is to be a helpful AI assistant with persistent memory."]]
        )
        mock_memory_instance.save_memory = MagicMock()
        
        # Mock streaming response that returns "retrieve_memory"
        async def mock_stream_generator_retrieve(messages, model):
            # Simulate a chunk containing "retrieve_memory"
            mock_chunk = MagicMock()
            mock_message = MagicMock()
            mock_message.content = "retrieve_memory"
            mock_chunk.message = mock_message
            yield mock_chunk
        
        # Mock streaming response that returns a normal answer
        async def mock_stream_generator_answer(messages, model):
            mock_chunk = MagicMock()
            mock_message = MagicMock()
            # Check if there's a memory context in messages
            has_memory = any("RETRIEVED MEMORIES:" in str(msg.get('content', '')) for msg in messages)
            if has_memory:
                mock_message.content = "I am named Anemone after the sea anemone, a creature that forms symbiotic relationships."
            else:
                mock_message.content = "Let me retrieve my memory to answer that."
            mock_chunk.message = mock_message
            yield mock_chunk
        
        # First test: Query triggers retrieval, then agent responds with memory
        print("\nTest 1: Normal memory retrieval flow")
        mock_stream.side_effect = mock_stream_generator_retrieve
        
        from orchestration import my_async_flow
        
        shared = {
            "history": [
                {"role": "user", "content": "What is your function?"}
            ],
            "loop_count": 0
        }
        
        try:
            result = await asyncio.wait_for(
                my_async_flow.run_async(shared),
                timeout=5.0
            )
            
            print(f"  Result: {result}")
            print(f"  Loop count: {shared.get('loop_count', 0)}")
            print(f"  Retrieved memory: {shared.get('retrieved_memory', 'None')[:50]}...")
            
            # Check that memory was retrieved
            assert mock_memory_instance.retrieve_memory.called
            print("  ✓ Memory retrieval called")
            
            # Check that memory_action was cleared
            assert shared.get('memory_action', '') == ''
            print("  ✓ Memory action cleared")
            
            # Check agent response
            agent_msgs = [msg for msg in shared['history'] if msg['role'] == 'agent']
            assert len(agent_msgs) > 0
            print(f"  ✓ Agent response generated")
            
        except asyncio.TimeoutError:
            print("  ✗ TIMEOUT - Infinite loop detected!")
            return False
        except AssertionError as e:
            print(f"  ✗ Assertion failed: {e}")
            return False
        
        # Second test: Simulate model disobeying - outputting retrieve_memory after already having memory
        print("\nTest 2: Guard against repeated retrieval")
        
        # Reset shared with existing memory
        shared = {
            "history": [
                {"role": "user", "content": "What is your function?"}
            ],
            "loop_count": 0,
            "retrieved_memory": "Existing memory about function",
            "memory_context": "What is your function?"
        }
        
        # Mock will still output retrieve_memory, but guard should intercept
        mock_stream.side_effect = mock_stream_generator_retrieve
        
        try:
            result = await asyncio.wait_for(
                my_async_flow.run_async(shared),
                timeout=5.0
            )
            
            print(f"  Result: {result}")
            print(f"  Loop count: {shared.get('loop_count', 0)}")
            
            # Check that memory retrieval was NOT called again (mock should not be called again)
            # retrieve_memory was already called once in previous test
            call_count = mock_memory_instance.retrieve_memory.call_count
            print(f"  Memory retrieval call count: {call_count}")
            
            # The guard should have intercepted and created a response from existing memory
            agent_msgs = [msg for msg in shared['history'] if msg['role'] == 'agent']
            if agent_msgs:
                last_response = agent_msgs[-1]['content']
                print(f"  Agent response: {last_response[:50]}...")
                if "retrieve_memory" in last_response.lower():
                    print("  ✗ Guard failed - retrieve_memory still in response")
                    return False
                else:
                    print("  ✓ Guard intercepted retrieve_memory command")
            
        except asyncio.TimeoutError:
            print("  ✗ TIMEOUT - Infinite loop detected!")
            return False
        
        # Third test: Normal conversation without memory retrieval
        print("\nTest 3: Conversation without memory retrieval")
        
        # Mock streaming with normal response
        async def mock_stream_generator_chat(messages, model):
            mock_chunk = MagicMock()
            mock_message = MagicMock()
            mock_message.content = "Hello! How can I help you today?"
            mock_chunk.message = mock_message
            yield mock_chunk
        
        mock_stream.side_effect = mock_stream_generator_chat
        
        shared = {
            "history": [
                {"role": "user", "content": "Hello"}
            ],
            "loop_count": 0
        }
        
        try:
            result = await asyncio.wait_for(
                my_async_flow.run_async(shared),
                timeout=5.0
            )
            
            print(f"  Result: {result}")
            print(f"  Loop count: {shared.get('loop_count', 0)}")
            
            # Memory retrieval should not be called
            assert mock_memory_instance.retrieve_memory.call_count == 1  # Only called in first test
            print("  ✓ No unnecessary memory retrieval")
            
            agent_msgs = [msg for msg in shared['history'] if msg['role'] == 'agent']
            assert len(agent_msgs) > 0
            print(f"  ✓ Normal conversation response generated")
            
        except asyncio.TimeoutError:
            print("  ✗ TIMEOUT - Infinite loop detected!")
            return False
    
    print("\n✓ All mock tests passed!")
    return True

async def main():
    """Run all mock tests."""
    success = await test_memory_retrieval_guard()
    
    if success:
        print(f"\n{'='*60}")
        print("✓ Mock integration tests passed!")
        sys.exit(0)
    else:
        print(f"\n{'='*60}")
        print("✗ Mock integration tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())