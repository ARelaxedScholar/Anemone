def remove_system(conv_list):
    """
    Simply removes system prompts and whatnot to avoid confusing the memory agent 
    among other things:

    Args:
        conv_list : List of conversation messages

    Returns:
        Same list, but without system prompts
    """
    return [message for message in conv_list if message['role'] != 'system']

async def call_llm(messages, model="llama2"):
    """Non-streaming LLM call"""
    from ollama import AsyncClient 
    import httpx
    
    # Set timeout for connection and reads
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
    client = AsyncClient(timeout=timeout)
    
    try:
        response = await client.chat(
            model=model,
            messages=messages
        )
        # The response object from ollama is a dictionary.
        # We are interested in the 'content' of the 'message'.
        return response['message']['content']
    except ImportError:
        return "Error: Ollama Python client not installed."
    except httpx.ConnectError:
        return "Error: Cannot connect to Ollama server. Please make sure Ollama is running (run 'ollama serve')."
    except httpx.TimeoutException:
        return f"Error: Timeout connecting to Ollama server after {timeout.connect} seconds. Is Ollama running?"
    except Exception as e:
        return f"Error during LLM call: {str(e)[:100]}"

async def call_llm_stream(messages, model="llama2"):
    """Streaming LLM call"""
    from ollama import AsyncClient 
    import httpx
    
    # Set timeout for connection and reads
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
    client = AsyncClient(timeout=timeout)
    
    print(f"call_llm_stream: Calling ollama with model={model}, messages={len(messages)}")
    try:
        response = await client.chat(
            model=model,
            messages=messages,
            stream=True
        )
        print(f"call_llm_stream: Got response, iterating...")
        async for chunk in response:
            print(f"call_llm_stream: Yielding chunk type {type(chunk)}")
            yield chunk
        print(f"call_llm_stream: Finished iteration")
    except httpx.TimeoutException as e:
        print(f"call_llm_stream: Timeout connecting to Ollama - {e}")
        raise ConnectionError(f"Timeout connecting to Ollama server after {timeout.connect} seconds. Is Ollama running?") from e
    except httpx.ConnectError as e:
        print(f"call_llm_stream: Cannot connect to Ollama - {e}")
        raise
    except Exception as e:
        print(f"call_llm_stream: Error: {e}")
        import traceback
        traceback.print_exc()
        raise
