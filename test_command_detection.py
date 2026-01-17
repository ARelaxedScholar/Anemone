#!/usr/bin/env python3
"""
Test command detection logic.
"""
import sys
sys.path.insert(0, '.')

from nodes import Agent

# Create agent instance (model doesn't matter for this test)
agent = Agent("test-model", "test prompt")

test_cases = [
    # (input, expected_is_command)
    ("retrieve_memory", True),
    ("retrieve_memory ", True),
    (" retrieve_memory", True),
    ("retrieve_memory\n", True),
    ("retrieve_memory RETRIEVED MEMORIES:", True),
    ("retrieve_memory\n\nRETRIEVED MEMORIES:", True),
    ("<|assistant|>retrieve_memory", True),
    ("assistant: retrieve_memory", True),
    ("retrieve_memory and then some text", True),  # starts with command
    ("I need to retrieve_memory", False),  # doesn't start with command
    ("Hello world", False),
    ("RETRIEVED MEMORIES:", False),  # just the marker, not a command
    ("", False),
    ("`retrieve_memory`", True),  # backticks should be removed
    ('"retrieve_memory"', True),  # quotes should be removed
]

print("Testing command detection...")
all_passed = True
for i, (input_text, expected) in enumerate(test_cases):
    result = agent._is_retrieve_command(input_text)
    passed = result == expected
    all_passed = all_passed and passed
    status = "✓" if passed else "✗"
    print(f"{status} Test {i+1}: '{input_text[:30]}...' -> {result} (expected {expected})")
    
print(f"\n{'='*60}")
if all_passed:
    print("✅ All command detection tests passed!")
    sys.exit(0)
else:
    print("❌ Some tests failed.")
    sys.exit(1)