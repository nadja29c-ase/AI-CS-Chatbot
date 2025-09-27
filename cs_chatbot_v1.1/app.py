from flask import Flask, request, session, render_template, redirect, url_for, jsonify
from flask_session import Session
from dotenv import load_dotenv
import os
import sys
import logging
from redis import Redis
import basic_metrics
from services.rag_service import RAGService
from services.conversation_service import ConversationService

app = Flask(__name__)

# === CONFIGURATION ===

# Configure root logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/chatbot.log"),    # Saves to file
        logging.StreamHandler()                # Shows in terminal
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables from .env file.
load_dotenv()

# Enable server-side sessions storage.
SESSION_TYPE = "redis"
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_REDIS = Redis.from_url(redis_url)
app.config.from_object(__name__)
Session(app)
basic_metrics.initialize_metrics(SESSION_REDIS)  # Initialize Redis client for metrics tracking

# Enable session management.
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Global. Declared here, initialized in startup.
conversation_service = None

# === STARTUP ===

# Validate critical components before starting the app.
def startup_validation():
    validate_environment_vars()
    check_template_file()  
    check_redis_health()
    prompt_system_v1_1()
    initialize_rag_service()
    logger.info("✅ Application validation successful")

# Check if environment variables exist.
def validate_environment_vars():
    required_vars = ["OPENAI_API_KEY", "FLASK_SECRET_KEY", "REDIS_URL"]
    faulty_vars = []

    for var in required_vars:
        if not os.getenv(var):
            faulty_vars.append(var)

    if faulty_vars:
        logger.critical(f"Required environment variables not found: {faulty_vars}")
        sys.exit(1)
    else:
        logger.info("All required environment variables found")

# Check if the template file exists.
def check_template_file():
    try:
        with open("templates/chat.html", "r") as f:
            f.read()  # verify if readable
        logger.info("Template file found and readable")
    except FileNotFoundError:
        logger.critical("Template file missing!")
        sys.exit(1)
    except PermissionError:
        logger.critical("Template file not readable due to permission error!")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Template validation failed. Unexpected error: {e}")
        sys.exit(1)

# Check if Redis is working for session storage.
def check_redis_health():
    try:
        # Test basic read/write operations
        test_key = "health_check"
        SESSION_REDIS.set(test_key, "ok", ex=10)  # Write: store "ok", expire in 10 seconds
        result = SESSION_REDIS.get(test_key)
        SESSION_REDIS.delete(test_key)
        
        if result == b"ok": # b"ok" is bytes (Redis returns bytes)
            logger.info("Redis health check passed")
            return True
        else:
            raise Exception("Redis read/write test failed")
            
    except Exception as e:
        logger.critical(f"Redis health check failed: {e}")
        sys.exit(1)

# Initialize and validate ConversationService with RAGService and ChromaDB connection. 
def initialize_rag_service():
    global conversation_service
    try:
        conversation_service = ConversationService(RAGService())
        logger.info("RAG Service initialized with Chroma DB connection successfully")
    except Exception as e:
        logger.critical(f"Failed to initialize RAG Service: {e}")
        sys.exit(1)

# === HELPER FUNCTIONS ===

# Load only static prompts (excluding knowledge base for RAG).
def prompt_system_v1_1():
    try:
        prompt_files = ["sys_prompt.txt", "behaviour_guidelines.txt"]  # Exclude knowledge_base_techmarkt.txt
        content_prompts = {}
        for file_name in prompt_files:
            with open(file_name, "r") as file:
                content = file.read().strip()
                content_prompts[file_name] = content
            
                # Validate if file is empty or only whitespace.
                if not content:
                    logger.critical(f"Empty or whitespace-only file: {file_name}")
                    sys.exit(1)
                
        # Validate all expected files were loaded.
        if len(content_prompts) < 2:
            logger.critical(f"Expected 2 prompt files, got {len(content_prompts)}")
            sys.exit(1)
             
        logger.info(f"All system prompts (v1.1) loaded successfully.")
        return content_prompts
    
    except Exception as e:
        logger.critical(f"Error loading system prompts (v1.1): {e}")
        sys.exit(1)

# === FLASK ROUTES ===

# Display the homepage with chat interface.
@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return redirect(url_for("home"))

    # Extract user message from request.
    user_message = request.json["message"]
    logger.info(f"User message received: {user_message}")

    # User Input validation.
    if len(user_message) > 1000:
        logger.warning("User message too long")
        return jsonify({"error": "Message too long (max 1000 characters)"}), 400

    # Initialize new conversation using ConversationService.
    if "messages" not in session:
        prompts = prompt_system_v1_1()  # Load static prompts
        basic_metrics.track_context_tokens(prompts) # Calculate and store context tokens
        session["messages"] = conversation_service.initialize_conversation(prompts)

    # Build conversation with user message and relevant context: sys prompts + rag-retrieved context.
    messages = conversation_service.build_conversation_with_context(session["messages"], user_message)

    # Get AI response using service layer - exceptions bubble up to centralized handlers
    ai_response, metrics_data = conversation_service.get_ai_response(messages)

    # Track metrics using data from service
    basic_metrics.track_metrics(
        metrics_data["response_time"],
        metrics_data["tokens_used"],
        success=metrics_data["success"]
    )

    # Add AI response to conversation using service.
    updated_messages = conversation_service.add_assistant_response(messages, ai_response)

    # Save updated conversation back to session for redis storage.
    session["messages"] = updated_messages

    return jsonify({"response": ai_response}) # send ai response to frontend

# Endpoint to view current chatbot metrics.
@app.route('/metrics')
def get_metrics():
    return jsonify(basic_metrics.get_metrics_summary())

# === CENTRALIZED ERROR HANDLERS ===

@app.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"Internal server error: {e}", exc_info=True) 
    basic_metrics.track_metrics(0, 0, success=False) 
    return jsonify({"error": "Service temporarily unavailable. Try again later."}), 500

@app.errorhandler(400)
def handle_bad_request(e):
    logger.error(f"Bad request: {e}", exc_info=True) 
    return jsonify({"error": "Invalid input/ request format."}), 400

@app.errorhandler(404)
def handle_not_found(e):
    logger.warning(f"Endpoint not found: {e}") 
    return jsonify({"error": "The path you requested doesn't exist."}), 404

@app.errorhandler(KeyError)
def handle_missing_json_key(e):
    logger.error(f"Missing required JSON key: {e}", exc_info=True)  
    return jsonify({"error": "Invalid request format."}), 400


if __name__ == "__main__":
    startup_validation()  
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)