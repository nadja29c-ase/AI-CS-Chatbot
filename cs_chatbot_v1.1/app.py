from flask import Flask, request, session, render_template, redirect, url_for, jsonify, Response
from flask_session import Session
import json
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
    required_vars = ["OPENAI_API_KEY", "FLASK_SECRET_KEY", "REDIS_URL", "DEPLOYMENT_ENV"]

    # First check base required vars (needed for all environments).
    missing_base_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_base_vars:
        logger.critical(f"Required environment variables not found: {missing_base_vars}")
        sys.exit(1)

    # Add production-specific requirements if in production mode.
    if os.getenv("DEPLOYMENT_ENV") == "production":
        production_vars = ["CHROMA_API_KEY", "CHROMA_TENANT", "CHROMA_DATABASE"]
        missing_production_vars = [var for var in production_vars if not os.getenv(var)]

        if missing_production_vars:
            logger.critical(f"Production environment requires: {missing_production_vars}")
            sys.exit(1)

    logger.info("All required environment variables found")

# Check if the template file exists and meets basic criteria.
def check_template_file():
    try:
        with open("templates/chat.html", "r") as f:
            content = f.read()
            if not content or not content.strip():
                logger.critical("Template file is empty!")
                sys.exit(1)
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
        # Test basic read/write operations.
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
    prompt_files = ["sys_prompt.txt", "behaviour_guidelines.txt"]  # Exclude knowledge_base_techmarkt.txt
    content_prompts = {}

    for file_name in prompt_files:
        try:
            with open(f"prompts/{file_name}", "r", encoding="utf-8") as file:
                content = file.read().strip()

                # Validate if file is empty or only whitespace.
                if not content:
                    logger.critical(f"Empty or whitespace-only file: {file_name}")
                    sys.exit(1)

                content_prompts[file_name] = content

        except FileNotFoundError:
            logger.critical(f"Prompt file not found: {file_name}")
            sys.exit(1)
        except PermissionError:
            logger.critical(f"Cannot read prompt file due to permissions: {file_name}")
            sys.exit(1)
        except UnicodeDecodeError:
            logger.critical(f"Encoding error in prompt file: {file_name}")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"Unexpected error loading {file_name}: {e}")
            sys.exit(1)

    # Validate all expected files were loaded.
    if len(content_prompts) < 2:
        logger.critical(f"Expected 2 prompt files, got {len(content_prompts)}")
        sys.exit(1)

    logger.info(f"All system prompts (v1.1) loaded successfully.")
    return content_prompts

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
        session["messages"] = conversation_service.initialize_conversation(prompts)

    # Build conversation with user message and relevant context: sys prompts + rag-retrieved context.
    messages = conversation_service.build_conversation_with_context(session["messages"], user_message)

    # Get AI response using service layer - exceptions bubble up to centralized handlers
    ai_response = conversation_service.get_ai_response(messages)

    # Add AI response to conversation using service.
    updated_messages = conversation_service.add_assistant_response(messages, ai_response)

    # Save updated conversation back to session for redis storage.
    session["messages"] = updated_messages

    return jsonify({"response": ai_response}) # send ai response to frontend

# Endpoint to view current chatbot metrics.
@app.route('/metrics')
def get_metrics():

    # Get metrics data and format as pretty JSON.
    metrics_data = basic_metrics.get_metrics_summary_v1_1()
    pretty_json = json.dumps(metrics_data, indent=2, ensure_ascii=False)

    # Return as formatted JSON response.
    return Response(pretty_json, mimetype='application/json')

# === CENTRALIZED ERROR HANDLERS ===

@app.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"Internal server error: {e}", exc_info=True) 
    basic_metrics.track_metrics_v1_1(0, 0, 0, success=False) 
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