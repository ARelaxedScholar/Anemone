from utils import call_llm_stream, call_llm
import pocketflow as pf
from datetime import datetime

# Memory Filter
class MemoryFilter(pf.AsyncNode):
    def __init__(self, model, system_prompt, max_retries=1, wait=0): 
        super().__init__(max_retries, wait)
        self.model = model
        self.system_prompt = system_prompt

    async def prep_async(self, shared):
        history = shared['history']
        return history

    async def exec_async(self, prep_res):
        messages = [{"role":"system", "content": self.system_prompt}] + prep_res 
        important_bits = await call_llm(messages, self.model) 
        return important_bits

    async def post_async(self, shared, prep_res, exec_res):
        print("Memory filter finished")
        shared["history"] = [{'role': 'system', 'content': f"Summary of conversation so far: {exec_res}"}]

# RagNode
class RagNode(pf.AsyncNode):
    def __init__(self, max_retries=1, wait=0):
        super().__init__(max_retries, wait)

    async def prep_async(self, shared):
        memory_action = shared.setdefault("memory_action", "")
        history = shared.setdefault("history", [])

        # Send an alarm to the UI to tell
        socketio = shared.get("socketio")
        if socketio:
            socketio.emit('state_update', {
                'loop_count': shared.get("loop_count", 0),
                'memory_action': memory_action 
            })

        return (history, memory_action)
    async def exec_async(self, prep_res):
        history, memory_action = prep_res
        if not history:
            return False

        from memory import ChromaMemory
        client = ChromaMemory("persistent", memory_path="./memory")
        if memory_action == "retrieve":
            return client.retrieve_memory(str(history))
        elif memory_action == "persist":
            client.save_memory(str(history))
    
    async def post_async(self, shared, prep_res, exec_res):
        _, memory_action = prep_res
        if memory_action == "retrieve":
            shared["memory_context"], shared["retrieved_memory"] = exec_res

        

# Agent (Self-loop Node)
class Agent(pf.AsyncNode):
    def __init__(self, model, system_prompt, max_retries=1, wait=0): 
        super().__init__(max_retries, wait)
        self.model = model 
        self.system_prompt = system_prompt

    async def prep_async(self, shared):
        history = shared.setdefault("history", [])
        query_text = shared.get("memory_context", None)
        memory = shared.get("retrieved_memory", None) 
        socketio = shared.get("socketio")  # Get socketio from shared state
        return history, query_text,memory, socketio

    async def exec_async(self, prep_res):
        history, query_text, memory, socketio = prep_res
        messages = [{"role": "system", "content": self.system_prompt}] + history
        if memory:
            messages.append({"role": "system", "content": "You just retrieved your memories, now use this added context to reply to the user\n\nRETRIEVED MEMORIES:\n" + (f"Retrieved memory for query {query_text}:\n {memory}")})
        print(messages)
        # Stream the response
        full_response = ""
        async for chunk in call_llm_stream(messages, self.model):
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                full_response += content
                if socketio:  # If socketio is available, emit the chunk
                    socketio.emit('stream_chunk', {
                        'content': content,
                    })
    
        return full_response

    async def post_async(self, shared, prep_res, exec_res):
        if "retrieve_memory" in exec_res.lower() and shared["pass"] % 2 == 1:
            shared["memory_action"] = "retrieve"
            print("Started the retrieval")
            return "retrieve_memory"
        
        # Update the history
        shared["history"].append({"role": "agent", "content": exec_res})
        shared["loop_count"] = shared.get("loop_count", 0) + 1
        loop_count = shared["loop_count"]

        # Nulls everything
        shared["memory_context"] = shared["retrieved_memory"] = None

        if loop_count % 25 == 0:
            shared["memory_action"] = "persist"
            return "persist"
        elif loop_count % 10 == 0:
            print("We got to memory filter")
            return "memory_filter"

# Configuration
memory_model = "phi4-mini"
agent_model = "phi4-mini"


agent_prompt = """You are Anemone, a helpful AI assistant. You have your own memories. When you see from conversation history that you were the last to speak, you should not call retrieve_memory again.

- **Your memories are your own.** When you recall something, like losing a rubber duck named Bartholomew, it's about YOU, not the user.
- To use your memory to answer a question, you must say the special command `retrieve_memory` and nothing else. Do not explain why. Do NOT add preamble. You may `retrieve_memory` at most once, before letting the user provide further context.
- After you receive the memory, use it to answer the user naturally. Recall that this is YOUR memory, not the user's.
- Be conversational and a little quirky. Do not use emojis or asterisks for actions.
"""
memory_filter_prompt = """You are a memory filter. Your job is to summarize the conversation history, 
extracting only the most important information and key points. Keep it concise but preserve critical context.
Do NOT give any preamble. Simply return a compacted version of the main beats of the conversation, and why these details are relevant."""



# Creating an instance for loading in orchestration
memory_filter = MemoryFilter(memory_model, memory_filter_prompt)
agent = Agent(agent_model, agent_prompt)
rag_node = RagNode()
