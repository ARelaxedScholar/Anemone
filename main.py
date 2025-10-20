import asyncio
from orchestration import my_async_flow

async def main():
    shared = {"history": []}
    while True:
        # User input
        user_msg = input("You: ")
        shared["history"].append({"role": "user", "content": user_msg})
    
        # Agent responds once
        result = await my_async_flow.run_async(shared)
    
        # Agent's response is already in shared["history"]
        print(f"Agent: {shared['history'][-1]['content']}")

if __name__ == "__main__":
    asyncio.run(main())
