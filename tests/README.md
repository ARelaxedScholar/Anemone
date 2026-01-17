# Anemone Test Suite

## Overview
This directory contains regression tests for the Anemone AI agent system. Tests cover memory retrieval, command detection, error handling, and UI flow.

## Running Tests
Run individual tests from the project root:

```bash
python tests/test_command_detection.py
python tests/test_fix_guard.py
python tests/test_error_handling.py
```

## Test Files

- **test_command_detection.py** – Verify `retrieve_memory` command detection logic
- **test_error_handling.py** – Test error handling for Ollama connection issues
- **test_fix.py** – Test the infinite‑loop fix for memory retrieval
- **test_fix_guard.py** – End‑to‑end test of memory retrieval guard
- **test_guard_case.py** – Test guard‑case response emission
- **test_integration.py** – Integration test with mocked components
- **test_memory_retrieval.py** – Test ChromaDB memory retrieval
- **test_mock_integration.py** – Mock integration test (no Ollama required)
- **test_ollama.py** – Test Ollama connectivity
- **test_simple_spaces.py** – Test streaming with simple spaces
- **test_streaming_spaces.py** – Test streaming with various spacing
- **test_ui_flow.py** – Test UI flow with mock SocketIO
- **debug_test.py** – Debug helper

## Notes
- Most tests require a running Ollama instance with the `phi4‑mini` model (or adjust the model in the test).
- Memory‑related tests assume a seeded ChromaDB (run `python seed_memory.py` first).
- Mock tests (`test_mock_integration.py`) run without external dependencies.