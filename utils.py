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
    response = await AsyncClient().chat(
        model=model,
        messages=messages
    )
    # The response object from ollama is a dictionary.
    # We are interested in the 'content' of the 'message'.
    return response['message']['content']

async def call_llm_stream(messages, model="llama2"):
    """Streaming LLM call"""
    from ollama import AsyncClient 
    client = AsyncClient()
    async for chunk in await client.chat(
        model=model,
        messages=messages,
        stream=True
    ):
        yield chunk
