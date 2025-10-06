import logging
import tiktoken
import json
import os
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# === CONFIGURATION ===

# File to store metrics persistently.
METRICS_JSON_FILE = "metrics_v1_1.json"

# Same tokenizer as v1.0 for comparable metrics.
TOKENIZER = tiktoken.get_encoding("cl100k_base")

# Default metrics structure template.
DEFAULT_METRICS_STRUCTURE = {
    "total_requests_v1_1": 0,
    "successful_requests_v1_1": 0,
    "total_response_time_v1_1": 0,
    "total_conversation_tokens_v1_1": 0,
    "total_context_tokens_v1_1": 0,
    "total_cost_v1_1": 0.0,
    "empty_retrieval_count_v1_1": 0,
    "empty_retrieval_queries_v1_1": [],
    "last_updated": ""  # Will be set when creating
}

# === INFRASTRUCTURE/VALIDATION ===

# Load metrics from JSON file or create default structure.
def load_json_metrics() -> Dict[str, Any]:
    try:
        if os.path.exists(METRICS_JSON_FILE):
            with open(METRICS_JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Migration: Add missing fields from DEFAULT_METRICS_STRUCTURE.
            updated = False
            for key, default_value in DEFAULT_METRICS_STRUCTURE.items():
                if key not in data:
                    data[key] = default_value
                    updated = True
                    logger.info(f"Added missing field to metrics: {key}")

            if updated:
                save_json_metrics(data)

            return data
        else:
            # File doesn't exist, create default structure.
            default_metrics = DEFAULT_METRICS_STRUCTURE.copy()
            default_metrics["last_updated"] = datetime.now().isoformat()
            save_json_metrics(default_metrics)
            logger.info("Created default v1.1 metrics JSON file")
            return default_metrics

    except (json.JSONDecodeError, PermissionError) as e:
        if isinstance(e, json.JSONDecodeError):
            error_type = "corrupted"
            logger.error(f"JSON metrics file corrupted: {e}")
        else:  # PermissionError
            error_type = "permission_error"
            logger.critical(f"Permission denied accessing metrics file: {e}")

        # Try to backup problematic file before creating new one.
        try:
            backup_name = f"{METRICS_JSON_FILE}.{error_type}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(METRICS_JSON_FILE, backup_name)
            logger.warning(f"Problematic file backed up as: {backup_name}")
        except Exception as backup_error:
            logger.error(f"Failed to backup problematic file: {backup_error}")

        # Create fresh default structure.
        default_metrics = DEFAULT_METRICS_STRUCTURE.copy()
        default_metrics["last_updated"] = datetime.now().isoformat()
        save_json_metrics(default_metrics)
        logger.info(f"Created new metrics file after {error_type} recovery")
        return default_metrics

# Save metrics to JSON file.
def save_json_metrics(metrics_data: Dict[str, Any]):
    try:
        metrics_data["last_updated"] = datetime.now().isoformat()
        with open(METRICS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save JSON metrics: {e}")

# === HELPER FUNCTIONS ===

# Calculate static prompts tokens (first two system messages).
def calculate_static_prompts_tokens_v1_1(conversation_messages: List[Dict[str, str]]) -> int:
    try:
        # Combine first two system messages into one string.
        static_content = conversation_messages[0]["content"] + conversation_messages[1]["content"]

        tokens = len(TOKENIZER.encode(static_content))
        logger.info(f"Static prompts tokens: {tokens}")
        return tokens

    except Exception as e:
        logger.error(f"Error calculating static prompt tokens: {e}")
        return 0

# Calculate RAG context tokens from retrieved knowledge.
def calculate_rag_tokens_v1_1(rag_content: str) -> int:
    try:
        tokens = len(TOKENIZER.encode(rag_content))
        logger.info(f"RAG context tokens: {tokens}")
        return tokens

    except Exception as e:
        logger.error(f"Error calculating RAG tokens: {e}")
        return 0

# === BUSINESS LOGIC ===

# Store and increment metrics using JSON persistence.
def track_metrics_v1_1(response_time, conversation_tokens, conversation_messages=None, rag_content=None, success=True):
    try:
        # Load current data.
        data = load_json_metrics()

        # Update raw counters.
        data["total_requests_v1_1"] += 1
        if success:
            data["successful_requests_v1_1"] += 1
            data["total_conversation_tokens_v1_1"] += conversation_tokens
            data["total_response_time_v1_1"] += response_time

            # Calculate context tokens and increment (static prompts + RAG).
            static_tokens = calculate_static_prompts_tokens_v1_1(conversation_messages) if conversation_messages else 0
            rag_tokens = calculate_rag_tokens_v1_1(rag_content) if rag_content else 0
            context_tokens = static_tokens + rag_tokens
            data["total_context_tokens_v1_1"] += context_tokens

            # Calculate cost (GPT-4o-mini pricing: $0.150 per 1M input, $0.600 per 1M output).
            # Assuming 50% input/50% output split for simplicity and comparability with v1.0.
            cost = (conversation_tokens / 1_000_000) * ((0.150 + 0.600) / 2)
            data["total_cost_v1_1"] += cost

        # Save updated data.
        save_json_metrics(data)

    except Exception as e:
        logger.warning(f"Failed to track v1.1 metrics: {e}")

# Track empty RAG retrievals with user query logging.
def track_empty_retrieval_v1_1(user_query: str):
    try:
        # Load current data.
        data = load_json_metrics()

        # Increment empty retrieval counter.
        data["empty_retrieval_count_v1_1"] += 1

        # Add query to log with timestamp.
        query_entry = {
            "query": user_query,
            "timestamp": datetime.now().isoformat()
        }

        data["empty_retrieval_queries_v1_1"].append(query_entry)

        # Keep only last 1000 entries (rotate old ones).
        if len(data["empty_retrieval_queries_v1_1"]) > 1000:
            data["empty_retrieval_queries_v1_1"] = data["empty_retrieval_queries_v1_1"][-1000:]

        # Save immediately (important for analysis).
        save_json_metrics(data)

        logger.info(f"Tracked empty retrieval for query: '{user_query[:50]}{'...' if len(user_query) > 50 else ''}'")

    except Exception as e:
        logger.error(f"Failed to track empty retrieval: {e}")

# Get metrics summary with calculated averages. 
def get_metrics_summary_v1_1():
    try:
        data = load_json_metrics()
        total_requests = data["total_requests_v1_1"]
        successful_requests = data["successful_requests_v1_1"]

        # Calculate averages.
        if successful_requests > 0:
            avg_response_time = data["total_response_time_v1_1"] / successful_requests
            avg_conversation_tokens = data["total_conversation_tokens_v1_1"] / successful_requests
            avg_context = data["total_context_tokens_v1_1"] / successful_requests
            avg_cost = data["total_cost_v1_1"] / successful_requests
            success_rate = (successful_requests / total_requests) * 100
        else:
            avg_response_time = avg_conversation_tokens = avg_context = avg_cost = success_rate = 0

        return {
            "total_requests_v1_1": total_requests,
            "average_response_time_v1_1": round(avg_response_time, 2),
            "success_rate_v1_1": round(success_rate, 1),
            "average_tokens_per_conversation_v1_1": round(avg_conversation_tokens, 1),
            "average_context_size_v1_1": round(avg_context, 1),
            "average_cost_per_conversation_v1_1": round(avg_cost, 6),
            "empty_retrieval_count_v1_1": data["empty_retrieval_count_v1_1"],
            "empty_retrieval_queries_v1_1": data["empty_retrieval_queries_v1_1"],
            "last_updated": data["last_updated"]
        }

    except Exception as e:
        logger.error(f"Error getting v1.1 metrics: {e}")
        return {"error": "Unable to retrieve v1.1 metrics"}
