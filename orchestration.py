import pocketflow as pf 
import asyncio
from nodes import agent, memory_filter, rag_node

my_async_flow = pf.AsyncFlow(start=agent)

# Actual orchestration logic
agent - "retrieve_memory" >> rag_node >> agent
agent - "persist" >> memory_filter >> rag_node
agent - "memory_filter" >> memory_filter 

