from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime

# Import orchestration
from orchestration import my_async_flow

app = Flask(__name__)
app.config['SECRET_KEY'] = 'anemone-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
conversation_state = {
    "history": [],
    "loop_count": 0,
    "retrieved_memory": "",
    "memory_action": ""
}

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=3)

def run_async_in_thread(coro):
    """Helper to run async code in Flask's sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Send current state when client connects"""
    emit('state_update', {
        'loop_count': conversation_state['loop_count'],
        'history': conversation_state['history']
    })

@socketio.on('user_message')
def handle_message(data):
    """Process user message through the orchestration"""
    user_msg = data.get('message', '').strip()
    
    if not user_msg:
        return
    
    # Add user message to history
    conversation_state['history'].append({
        'role': 'user',
        'content': user_msg,
        'timestamp': datetime.now().isoformat()
    })
    
    # Pass socketio instance to the orchestration
    conversation_state['socketio'] = socketio
    
    # Emit user message immediately
    emit('new_message', {
        'role': 'user',
        'content': user_msg,
        'timestamp': datetime.now().isoformat()
    }, broadcast=True)
    
    # Emit processing status
    emit('status_update', {
        'status': 'processing',
        'message': 'Anemone is thinking...'
    }, broadcast=True)
    
    try:
        # Run the async flow in background
        def run_flow():
            try:
                # Run the async flow
                run_async_in_thread(my_async_flow.run_async(conversation_state))
                
                # Memory retrieval is now emitted by RagNode.post_async
                # Keep this as backup but don't clear retrieved_memory here
                # (Agent.post_async will clear it after use)
                pass
                
                # Emit final state update
                socketio.emit('state_update', {
                    'loop_count': conversation_state['loop_count'],
                    'memory_action': conversation_state.get('memory_action', '')
                })
                
                # Clear processing status
                socketio.emit('status_update', {
                    'status': 'idle',
                    'message': ''
                })
                
            except Exception as e:
                print(f"Error in run_flow: {e}")
                import traceback
                traceback.print_exc()
                socketio.emit('status_update', {
                    'status': 'error',
                    'message': f'Error: {str(e)}'
                })
        
        # Submit to thread pool
        executor.submit(run_flow)
        
    except Exception as e:
        emit('error', {
            'message': f'Error: {str(e)}'
        }, broadcast=True)
        emit('status_update', {
            'status': 'error',
            'message': 'An error occurred'
        }, broadcast=True)

@socketio.on('clear_conversation')
def handle_clear():
    """Clear the conversation history"""
    conversation_state['history'] = []
    conversation_state['loop_count'] = 0
    conversation_state['retrieved_memory'] = ''
    
    emit('conversation_cleared', {}, broadcast=True)

if __name__ == '__main__':
    print("🌊 Starting Anemone UI...")
    print("📍 Open http://localhost:5000 in your browser")
    socketio.run(app, debug=True, port=5000)
