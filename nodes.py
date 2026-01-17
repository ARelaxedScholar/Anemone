from utils import call_llm_stream, call_llm
import pocketflow as pf
from datetime import datetime
import httpx

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
        try:
            important_bits = await call_llm(messages, self.model) 
            return important_bits
        except ImportError:
            print("MemoryFilter: Ollama Python client not installed.")
            return "Conversation history could not be summarized due to missing Ollama client."
        except httpx.ConnectError:
            print("MemoryFilter: Cannot connect to Ollama server.")
            return "Conversation history could not be summarized due to Ollama connection issue."
        except Exception as e:
            print(f"MemoryFilter: Error during summarization: {e}")
            return f"Conversation history could not be summarized: {str(e)[:50]}"

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

        print(f"RagNode.prep_async: memory_action='{memory_action}', history length={len(history)}")
        return (history, memory_action)
    async def exec_async(self, prep_res):
        history, memory_action = prep_res
        if not history:
            return False

        try:
            from memory import ChromaMemory
            client = ChromaMemory("persistent", memory_path="./memory")
        except ImportError as e:
            print(f"RagNode: ChromaDB not available - {e}")
            if memory_action == "retrieve":
                return {"query": "", "memory_text": "Memory database not available."}
            else:
                return False
        
        try:
            if memory_action == "retrieve":
                # Extract the last user message to use as the query
                query = ""
                for msg in reversed(history):
                    if msg.get("role") == "user":
                        query = msg.get("content", "")
                        break
                
                if not query:
                    # Fallback if no user message found (unlikely)
                    return False
                    
                query, retrieved = client.retrieve_memory(query)
                # Extract memory text from ChromaDB result structure
                # retrieved is list of lists: [["memory text"]]
                memory_text = ""
                if retrieved and len(retrieved) > 0 and len(retrieved[0]) > 0:
                    memory_text = retrieved[0][0]
                return {"query": query, "memory_text": memory_text}
            elif memory_action == "persist":
                client.save_memory(str(history))
                return True
            else:
                # Unknown memory_action, shouldn't happen
                print(f"RagNode: Unknown memory_action '{memory_action}'")
                return False
        except Exception as e:
            print(f"RagNode: Error during memory operation: {e}")
            if memory_action == "retrieve":
                return {"query": "", "memory_text": f"Error retrieving memory: {str(e)[:50]}"}
            else:
                print(f"RagNode: Failed to persist memory: {e}")
                return False
    
    async def post_async(self, shared, prep_res, exec_res):
        _, memory_action = prep_res
        if memory_action == "retrieve":
            if exec_res is False:
                # No history, retrieval failed
                shared["memory_context"] = ""
                shared["retrieved_memory"] = ""
            elif isinstance(exec_res, dict) and "query" in exec_res:
                shared["memory_context"] = exec_res["query"]
                shared["retrieved_memory"] = exec_res["memory_text"]
                # Emit memory retrieval notification to UI
                socketio = shared.get("socketio")
                if socketio and exec_res["memory_text"]:
                    socketio.emit('memory_retrieved', {
                        'content': exec_res["memory_text"]
                    })
                    print(f"RagNode: Emitted memory_retrieved event with memory text: {exec_res['memory_text'][:80]}...")
            else:
                # Fallback for old format
                shared["memory_context"], shared["retrieved_memory"] = exec_res
                # Emit memory retrieval notification to UI
                socketio = shared.get("socketio")
                if socketio and shared["retrieved_memory"]:
                    socketio.emit('memory_retrieved', {
                        'content': shared["retrieved_memory"]
                    })
                    print(f"RagNode: Emitted memory_retrieved event with memory text: {shared['retrieved_memory'][:80]}...")
            # Clear memory_action to prevent re-retrieval in same turn
            shared["memory_action"] = ""
            print(f"RagNode: Memory retrieved and memory_action cleared. Memory text: {shared['retrieved_memory'][:80]}...")

        

# Agent (Self-loop Node)
class Agent(pf.AsyncNode):
    def __init__(self, model, system_prompt, max_retries=1, wait=0): 
        super().__init__(max_retries, wait)
        self.model = model 
        self.system_prompt = system_prompt
    
    def _clean_chunk(self, text):
        """Clean a streaming chunk - removes role tokens but preserves whitespace."""
        # Remove common role tokens that models might output
        tokens_to_remove = [
            '<|assistant|>', '<|user|>', '<|system|>',
            'assistant:', 'user:', 'system:',
            'Assistant:', 'User:', 'System:',
            'ASSISTANT:', 'USER:', 'SYSTEM:'
        ]
        cleaned = text
        for token in tokens_to_remove:
            if cleaned.startswith(token):
                cleaned = cleaned[len(token):]
                # Only strip leading whitespace after removing token
                cleaned = cleaned.lstrip()
        return cleaned
    
    def _clean_llm_response(self, text):
        """Remove role tokens and normalize LLM response for final output."""
        # Remove common role tokens that models might output
        tokens_to_remove = [
            '<|assistant|>', '<|user|>', '<|system|>',
            'assistant:', 'user:', 'system:',
            'Assistant:', 'User:', 'System:',
            'ASSISTANT:', 'USER:', 'SYSTEM:'
        ]
        cleaned = text
        for token in tokens_to_remove:
            if cleaned.startswith(token):
                cleaned = cleaned[len(token):].lstrip()
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        # Remove surrounding backticks, quotes, or code formatting
        if cleaned.startswith('`') and cleaned.endswith('`'):
            cleaned = cleaned[1:-1].strip()
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1].strip()
        if cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1].strip()
        # Remove trailing punctuation that might be added by the model
        if cleaned.endswith('.') or cleaned.endswith('!') or cleaned.endswith('?'):
            cleaned = cleaned[:-1].strip()
        # Remove memory-related markers that the model might incorrectly include
        markers_to_remove = [
            "RETRIEVED MEMORIES:",
            "retrieved memories:",
            "<retrieved_memory>",
            "</retrieved_memory>",
        ]
        for marker in markers_to_remove:
            if marker in cleaned:
                cleaned = cleaned.replace(marker, "").strip()
        return cleaned
    
    def _is_retrieve_command(self, text):
        """Check if the text is a retrieve_memory command."""
        cleaned = self._clean_llm_response(text).lower()
        # Check if it starts with "retrieve_memory" (model might add extra text)
        # Also check for exact match
        return cleaned.startswith("retrieve_memory") or cleaned == "retrieve_memory"

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
            messages.append({"role": "system", "content": f"You just retrieved your memories. Use this information to answer the user's question. DO NOT output 'retrieve_memory' again. DO NOT copy the XML tags in your response. Just answer naturally using the memory below.\n\n<retrieved_memory>\nMemory about '{query_text}':\n{memory}\n</retrieved_memory>"})
        print(f"Agent.exec_async: Preparing LLM call with {len(messages)} messages")
        print(f"Agent.exec_async: Memory present: {bool(memory)}")
        print(f"Agent.exec_async: SocketIO available: {socketio is not None}")
        print(f"Agent.exec_async: First message preview: {messages[0]['content'][:100]}...")
        if memory:
            print(f"Agent.exec_async: Memory preview: {memory[:100]}...")
        # Stream the response
        full_response = ""
        chunk_count = 0
        self._stream_buffer = ""  # Clear buffer at start of each call
        self._is_command_response = False  # Track if response is a command
        try:
            async for chunk in call_llm_stream(messages, self.model):
                print(f"Agent.exec_async: Received chunk: {chunk}")
                # Handle both dict and object access
                if hasattr(chunk, 'message'):
                    message = chunk.message
                elif isinstance(chunk, dict) and 'message' in chunk:
                    message = chunk['message']
                else:
                    print(f"Agent.exec_async: Unknown chunk structure: {chunk}")
                    continue
                
                if hasattr(message, 'content'):
                    content = message.content
                elif isinstance(message, dict) and 'content' in message:
                    content = message['content']
                else:
                    print(f"Agent.exec_async: No content in message: {message}")
                    continue
                
                if content is None:
                    continue
                    
                full_response += content if content is not None else ''
                
                # Check if the accumulating response is a retrieve_memory command
                # We need to check both raw and cleaned versions
                cleaned_so_far = self._clean_llm_response(full_response).lower()
                if cleaned_so_far.startswith("retrieve_memory"):
                    self._is_command_response = True
                    # Don't stream commands to the user
                    continue
                
                # Only stream if not a command response
                if not self._is_command_response and socketio:
                    # Clean the chunk before emitting - preserve whitespace for token streaming
                    cleaned_content = self._clean_chunk(content)
                    if cleaned_content:
                        # Initialize buffer if needed
                        if not hasattr(self, '_stream_buffer'):
                            self._stream_buffer = ""
                        self._stream_buffer += cleaned_content
                        
                        # Emit buffer if it's large enough or contains punctuation
                        punctuation = '.!?,;:'
                        if len(self._stream_buffer) >= 30 or any(p in cleaned_content for p in punctuation):
                            chunk_count += 1
                            socketio.emit('stream_chunk', {
                                'content': self._stream_buffer,
                            })
                            print(f"Agent.exec_async: Emitted buffered chunk {chunk_count}: '{self._stream_buffer[:50]}...'")
                            self._stream_buffer = ""
                        # else: buffer accumulates for next emit
        except ImportError:
            error_msg = "Ollama Python client not installed. Please run 'pip install ollama'."
            print(f"Agent.exec_async: {error_msg}")
            full_response = error_msg
            if socketio:
                socketio.emit('stream_chunk', {'content': error_msg})
        except httpx.ConnectError as e:
            error_msg = "Cannot connect to Ollama server. Please make sure Ollama is running (run 'ollama serve' in another terminal)."
            print(f"Agent.exec_async: {error_msg} - {str(e)}")
            full_response = error_msg
            if socketio:
                socketio.emit('stream_chunk', {'content': error_msg})
        except Exception as e:
            error_msg = f"I'm having trouble connecting to my AI model. Error: {str(e)[:100]}"
            print(f"Agent.exec_async: {error_msg}")
            full_response = error_msg
            if socketio:
                socketio.emit('stream_chunk', {'content': error_msg})
        finally:
            # Flush any remaining buffer (only if not a command response)
            if (hasattr(self, '_stream_buffer') and self._stream_buffer and socketio and 
                not getattr(self, '_is_command_response', False)):
                chunk_count += 1
                socketio.emit('stream_chunk', {
                    'content': self._stream_buffer,
                })
                print(f"Agent.exec_async: Flushed buffer chunk {chunk_count}: '{self._stream_buffer[:50]}...'")
                self._stream_buffer = ""
        
        # Clean the full response before returning
        cleaned_full_response = self._clean_llm_response(full_response)
        print(f"Agent.exec_async: Total chunks: {chunk_count}")
        print(f"Agent.exec_async: Raw response ({len(full_response)} chars): {full_response[:100]}...")
        print(f"Agent.exec_async: Cleaned response ({len(cleaned_full_response)} chars): {cleaned_full_response[:100]}...")
        return cleaned_full_response

    async def post_async(self, shared, prep_res, exec_res):
        # Extract memory from prep_res to check if we just retrieved memory
        history, query_text, memory, socketio = prep_res
        
        # Check if agent output is a retrieve_memory command
        # Use the cleaner to handle backticks, quotes, role tokens, etc.
        is_retrieve_command = self._is_retrieve_command(exec_res)
        print(f"Agent.post_async: Checking if '{exec_res[:50]}...' is retrieve command: {is_retrieve_command}")
        
        if is_retrieve_command:
            # Guard: if memory already exists (just retrieved), ignore the command
            # This prevents infinite loops when model disobeys instructions
            if memory:
                print(f"Memory guard: Ignoring retrieve_memory command since memory already retrieved. Memory: {memory[:50]}...")
                print(f"Memory guard: Checking if ': ' in memory: {': ' in memory}")
                print(f"Memory guard: memory repr: {repr(memory[:100])}")
                # Don't trigger another retrieval, respond with memory-based answer
                # Use the retrieved memory to craft a response
                if memory:
                    # Try to make a natural response from the memory
                    # If memory starts with label like "Origin Story:", remove it
                    # Try multiple ways to extract content
                    memory_content = memory
                    if ": " in memory:
                        # Take the part after the first ": "
                        memory_content = memory.split(": ", 1)[1]
                        exec_res = f"According to my memory, {memory_content}"
                        print(f"Memory guard: Using 'According to my memory' format (split on ': ')")
                    elif ":" in memory:
                        # Fallback for colon without space
                        memory_content = memory.split(":", 1)[1].lstrip()
                        exec_res = f"According to my memory, {memory_content}"
                        print(f"Memory guard: Using 'According to my memory' format (split on ':')")
                    else:
                        exec_res = f"I recall that {memory}"
                        print(f"Memory guard: Using 'I recall that' format")
                else:
                    exec_res = "I've accessed the relevant memory. Now I can answer your question."
                
                # Emit the natural response since streaming was suppressed for the command
                if socketio:
                    socketio.emit('stream_chunk', {'content': exec_res})
                    print(f"Agent.post_async: Emitted guard response: '{exec_res[:50]}...'")
            else:
                # No memory yet, trigger retrieval
                shared["memory_action"] = "retrieve"
                print("Agent.post_async: Triggering memory retrieval")
                return "retrieve_memory"
        
        # Update the history with agent's response
        shared["history"].append({"role": "agent", "content": exec_res})
        shared["loop_count"] = shared.get("loop_count", 0) + 1
        loop_count = shared["loop_count"]

        # Clear memory context after use
        shared["memory_context"] = shared["retrieved_memory"] = None

        # Schedule memory operations based on loop count
        if loop_count % 10 == 0:
            shared["memory_action"] = "persist"
            return "persist"
        elif loop_count % 5 == 0:
            return "memory_filter"

# Configuration
memory_model = "phi4-mini"
agent_model = "phi4-mini"


agent_prompt = """You are Anemone, a helpful AI assistant with persistent memory.

COMMANDS:
- retrieve_memory: Output this command ALONE if the user asks a question that requires knowledge about you, your past, or specific facts (e.g., "Who is Bartholomew?", "What is your function?", "What did we talk about?").

RULES:
1. **Triggering Memory**: If the user's query implies a need for context you might have stored, you MUST output retrieve_memory. Do not try to answer without it.
2. **Loop Prevention**: If ANY system message in the conversation contains XML tags like <retrieved_memory>, do NOT call retrieve_memory again. Use that retrieved information to answer.
3. **Output Format**: When retrieving memory, output EXACTLY the word "retrieve_memory" with no other text, no punctuation, no formatting, no backticks, no quotes.
4. **Memory Context**: After retrieving memory, you will see a system message with <retrieved_memory> tags containing the memory. Use this information to answer the user's question.
5. **Your Memories**: When you recall something (like your rubber ducky Bartholomew), treat it as YOUR memory.
6. **Personality**: Be conversational and a little quirky. No emojis.
7. **DO NOT COPY TAGS**: Never include <retrieved_memory> tags or the word "RETRIEVED MEMORIES" in your responses.

If you need to retrieve memory, output ONLY: retrieve_memory
"""
memory_filter_prompt = """You are a memory filter. Your job is to summarize the conversation history, 
extracting only the most important information and key points. Keep it concise but preserve critical context.
Do NOT give any preamble. Simply return a compacted version of the main beats of the conversation, and why these details are relevant."""



# Creating an instance for loading in orchestration
memory_filter = MemoryFilter(memory_model, memory_filter_prompt)
agent = Agent(agent_model, agent_prompt)
rag_node = RagNode()
