from flask import Flask, request, session, render_template, redirect, url_for, jsonify
from flask_session import Session
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
from redis import Redis

app = Flask(__name__)

# Enable server-side sessions storage
SESSION_TYPE = "redis"
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_REDIS = Redis.from_url(redis_url)
app.config.from_object(__name__)
Session(app)

# Enable session management
load_dotenv()
print(f"DEBUG: Dotenv loaded, API key: {os.getenv('OPENAI_API_KEY')[:10] if os.getenv('OPENAI_API_KEY') else 'NOT FOUND'}...")
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Function definitions
def prompt_system():
    prompt_files = ["sys_prompt.txt", "behaviour_guidelines.txt", "knowledge_base_techmarkt.txt"]
    content_prompts = {}
    for file_name in prompt_files:
        with open(file_name, "r") as file:
            content_prompts[file_name] = file.read().strip()
    return content_prompts

def create_openai_connector():
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"DEBUG: API key from env: {api_key[:10] if api_key else 'NONE'}...")
    print(f"DEBUG: All env vars: {list(os.environ.keys())}")
    client = OpenAI(api_key=api_key)
    return client

# Display the homepage with chat interface
@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/chat", methods=["GET", "POST"])
def chat():
    print("=== CHAT ROUTE CALLED ===")
    print(f"Request method: {request.method}")

    if request.method == "GET":
        print("GET request - redirecting")
        # If the user tries to access the chat page directly, redirect them to home
        return redirect(url_for("home"))
    elif request.method == "POST":
        print("POST request received")
        # Check if a new session exists
        print(f"Session ID: {session.get('_permanent', 'No ID')}")
        # Let's see the ACTUAL session ID being used
        print(f"Actual session ID: {session.get('_session_id', 'No ID found')}")
        print(f"Session SID: {getattr(session, 'sid', 'No SID')}")
        print(f"Session modified: {session.modified}")
        print(f"Session new: {session.new}")
        print(f"Session object type: {type(session)}")
        
        # Print session cookie for debugging
        print(f"Session cookie in request: {request.cookies.get('session', 'No cookie')}")
        print(f"Number of messages: {len(session.get('messages', []))}")

        try:
        # Get user message from request
            user_message = request.json["message"]
            print(f"User message received: {user_message}")
        except Exception as e:
            print(f"Error retrieving user message: {e}")
            return jsonify({"error": "Invalid request"}), 400
            
        # Check if session already has messages
        if "messages" in session:
            print(f"❌ REUSING EXISTING SESSION with {len(session['messages'])} messages")
        else:
            print("✅ NEW SESSION - no messages key found")
        
        # If no messages in session, initialize conversation and prompt system
        if "messages" not in session:
            try:
                # Load system prompts
                prompts = prompt_system()
                print("System prompts loaded successfully.")
                print(f"Check whether updated prompt is in use: {prompts['behaviour_guidelines.txt']}")
            except Exception as e:
                print(f"Error loading system prompts: {e}")

            # Start new conversation with system prompt and knowledge base
            session["messages"] = [
            {"role": "system", "content": prompts["sys_prompt.txt"]},
            {"role": "system", "content": prompts["behaviour_guidelines.txt"]},
            {"role": "assistant", "content": prompts["knowledge_base_techmarkt.txt"]},
            ]
            print(f"Session size before: {sys.getsizeof(str(session['messages']))}")
            print(f"Session ID: {session.sid}")
        
        # Conversation storage
        messages = session["messages"]
    
        # Add user message to conversation
        messages.append({"role": "user", "content": user_message})
    
        # Set up OpenAI 
        client = create_openai_connector()
    
        # Call OpenAI 
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_completion_tokens=1500,
            temperature=0.7,
        )
    
        ai_response = response.choices[0].message.content
    
        # Add AI response to conversation history
        messages.append({"role": "assistant", "content": ai_response})
    
        # Save updated conversation back to session
        session["messages"] = messages

        return jsonify({"response": ai_response})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)