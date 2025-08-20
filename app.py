from flask import Flask, request, session, render_template, redirect, url_for, jsonify
from flask_session import Session
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import logging
from redis import Redis
import basic_metrics
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("chatbot.log"),    # Saves to file
        logging.StreamHandler()                # Shows in terminal
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)


# Enable server-side sessions storage
SESSION_TYPE = "redis"
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_REDIS = Redis.from_url(redis_url)
app.config.from_object(__name__)
Session(app)
basic_metrics.initialize_metrics(SESSION_REDIS)  # Initialize Redis client for metrics tracking

# Load environment variables
load_dotenv()

# Validate critical components before starting the app
def startup_validation():
    validate_environment_vars()
    check_template_file()  
    logger.info("✅ Application validation successful")

# Check if Redis is working for session storage
def check_redis_health():
    try:
        # Test Redis connection
        SESSION_REDIS.ping()
        
        # Test basic read/write operations
        test_key = "health_check"
        SESSION_REDIS.set(test_key, "ok", ex=10)  
        result = SESSION_REDIS.get(test_key)
        SESSION_REDIS.delete(test_key)
        
        if result == b"ok":
            return True
        else:
            raise Exception("Redis read/write test failed")
            
    except Exception as e:
        logger.critical(f"Redis health check failed: {e}")
        logger.critical("Multi-turn conversations will not work properly")
        return False

def validate_environment_vars():
    required_vars = ["OPENAI_API_KEY", "FLASK_SECRET_KEY", "REDIS_URL"]
    faulty_vars = []

    for var in required_vars:
        if not os.getenv(var):
            faulty_vars.append(var)

    if faulty_vars:
        logger.critical(f"Required environment variables not found: {faulty_vars}")
        logger.critical("Check your .env file for typos, correct variable names, and proper loading")
        sys.exit(1)

# Enable session management
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Load system prompts from files
def prompt_system():
    try:
        prompt_files = ["sys_prompt.txt", "behaviour_guidelines.txt", "knowledge_base_techmarkt.txt"]
        content_prompts = {}
        for file_name in prompt_files:
            with open(file_name, "r") as file:
                content_prompts[file_name] = file.read().strip()
        logger.info(f"System prompts loaded successfully.")
        return content_prompts
    except Exception as e:
        logger.error(f"Error loading system prompts: {e}")
        return {}

# Create Client for OpenAI API
def create_openai_connection():
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        client.models.list()  # Test connection to OpenAI API
        logger.info("OpenAI client created successfully.")
        return client
    except Exception as e:
        logger.critical(f"Cannot initialize OpenAI client: {e}")
        return None

# Check if the template file exists 
def check_template_file():
    if os.path.exists("templates/chat.html"):
        with open("templates/chat.html", "r") as f:
            content = f.read()  # Safe to open
    else:
        logger.critical("Template file missing!")
        sys.exit(1)

# Display the homepage with chat interface
@app.route("/")
def home():
    try:
        return render_template("chat.html")
    except Exception as e:
        logger.error(f"Error loading home page: {e}")
        return jsonify({"error": "Service temporarily unavailable. Try again later."}), 500

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        # If the user tries to access the chat page directly, redirect them to home
        logger.info("GET request - redirecting")
        return redirect(url_for("home"))
    elif request.method == "POST":
        logger.info("POST request received")

         # Check Redis health on every chat request to ensure no loss of conversation history
        if not check_redis_health():
            return jsonify({"error": "Service temporarily unavailable. Try again later."}), 500

        try:
            if not request.json:
                # Check if the request contains a JSON body
                logger.error("Non-JSON request received")
                return jsonify({"error": "Service temporarily unavailable. Try again later."}), 500
            elif "message" not in request.json:
                # Check if the request contains a 'message' key
                logger.error("KeyError:No message key found in JSON request")
                return jsonify({"error": "Service temporarily unavailable. Try again later."}), 500
            else:
            # Get user message from request
                user_message = request.json["message"]
                logger.info(f"User message received: {user_message}")
                 # Check validity of the received user message
                if len(user_message) > 1000:
                    logger.warning("User message too long")  
                    return jsonify({"error": "Message too long (max 1000 characters)"}), 400
        except Exception as e:
            logger.error(f"Error retrieving user message: {e}")
            return jsonify({"error": "Service temporarily unavailable. Try again later."}), 500

        # If no messages in session, initialize conversation and prompt system
        if "messages" not in session:
            logger.info("No messages in session, initializing conversation with system prompts.")
            # Load system prompts
            prompts = prompt_system()

            if prompts == {}:
                logger.error("EMPTY PROMPTS DETECTED - RETURNING ERROR TO USER")
                return jsonify({"error": "The chatbot, Rob, is currently giving unreliable responses. We are working on fixing it. Please excuse this inconvenience and try again later."}), 500

            # Start new conversation with system prompt and knowledge base
            session["messages"] = [
            {"role": "system", "content": prompts["sys_prompt.txt"]},
            {"role": "system", "content": prompts["behaviour_guidelines.txt"]},
            {"role": "assistant", "content": prompts["knowledge_base_techmarkt.txt"]},
            ]

        # Conversation storage
        messages = session["messages"]
    
        # Add user message to conversation
        messages.append({"role": "user", "content": user_message})
        logger.info(f"User message added to conversation: {user_message}")
    
        # Set up OpenAI 
        client = create_openai_connection()
        if client is None:
            return jsonify({"error": "Service temporarily unavailable. Try again later."}), 500
        

        # Send request to OpenAI  including conversation history
        try:
            start_time = time.time() # Start tracking response time

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_completion_tokens=800,
                temperature=0.7,
            )
            logger.info("OpenAI call successful.")

            end_time = time.time()  
            response_time = end_time - start_time # Calculate response time in seconds
            tokens_used = response.usage.total_tokens # Track tokens used
            basic_metrics.track_metrics(response_time, tokens_used, success=True) # Track metrics for successful requests
            logger.info(f"API call completed - Time: {response_time:.2f}s, Tokens: {tokens_used}")
            
            # Retrieve AI response
            ai_response = response.choices[0].message.content
            logger.info(f"AI response received: {ai_response}")
        except Exception as e:
            basic_metrics.track_metrics(0, 0, success=False) # Track metrics for failed requests
            logger.error(f"Error during OpenAI call: {e}")
            return jsonify({"error": "Service temporarily unavailable. Try again later."}), 500

        # Add AI response to conversation history
        messages.append({"role": "assistant", "content": ai_response})
        logger.info(f"AI response added to conversation history: {ai_response}")

        # Save updated conversation back to session
        session["messages"] = messages

        return jsonify({"response": ai_response})

# Endpoint to view current chatbot metrics
@app.route('/metrics')
def get_metrics():
    return jsonify(basic_metrics.get_metrics_summary())

if __name__ == "__main__":
    startup_validation()  
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)