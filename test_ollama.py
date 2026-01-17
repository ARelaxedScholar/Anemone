#!/usr/bin/env python3
"""Test ollama directly."""
import asyncio
from ollama import AsyncClient

async def test():
    client = AsyncClient()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is your function?"},
        {"role": "system", "content": "You just retrieved your memories, now use this added context to reply to the user. DO NOT output 'retrieve_memory' again - use the retrieved information below.\n\nRETRIEVED MEMORIES:\nRetrieved memory for query What is your function?:\n Core Directive #1: My primary function is to assist users. My secondary, and more important function, is to find the ultimate recipe for a grilled cheese sandwich."}
    ]
    
    print("Testing ollama call...")
    try:
        response = await client.chat(
            model="phi4-mini",
            messages=messages,
            stream=True
        )
        
        print("Stream started")
        async for chunk in response:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                print(f"Chunk: '{content}'")
            else:
                print(f"Other chunk: {chunk}")
        
        print("Stream completed")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())