import time
import redis
import logging
import tiktoken

logger = logging.getLogger(__name__)

# Set the Redis client for metrics tracking
def initialize_metrics(redis_client):
    global r
    r = redis_client

total_context_tokens_v1_0 = 0

# Calculate context tokens from loaded prompt content and store in Redis
def track_context_tokens(prompts):
    global total_context_tokens_v1_0 
    
    try:
        tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4o-mini uses cl100k_base
        
        # Extract content from the loaded prompts dictionary
        sys_prompt_content = prompts.get("sys_prompt.txt", "")
        behavior_content = prompts.get("behaviour_guidelines.txt", "")
        knowledge_content = prompts.get("knowledge_base_techmarkt.txt", "")

        # Calculate tokens for each component
        sys_prompt_tokens = len(tokenizer.encode(sys_prompt_content))
        behavior_tokens = len(tokenizer.encode(behavior_content))
        knowledge_tokens = len(tokenizer.encode(knowledge_content))
        total_context_tokens_v1_0 = sys_prompt_tokens + behavior_tokens + knowledge_tokens

        logger.info(f"Context tokens: sys={sys_prompt_tokens}, behavior={behavior_tokens}, knowledge={knowledge_tokens}, total={total_context_tokens_v1_0}")
        
        return total_context_tokens_v1_0

    except Exception as e:
        logger.error(f"Error calculating context tokens: {e}")
        return 0

# Track key performance metrics using Redis counters
def track_metrics(response_time_v1_0, tokens_used_v1_0, success=True):
    try:
        if success:
            r.incr("metrics:total_succ_requests_v1_0")  # Count successful requests
            r.incr("metrics:total_tokens_v1_0", tokens_used_v1_0)  # Add tokens to running total
            r.incr("metrics:total_response_time_ms_v1_0", int(response_time_v1_0 * 1000))  # Add response time in ms for redis
        else:
            r.incr("metrics:failed_requests_v1_0")  # Count failed requests separately

    except Exception as e:
        logger.warning(f"Failed to track metrics: {e}")

# Calculate and return current metrics summary 
def get_metrics_summary():
    try:
        # Get raw counters from Redis (returns bytes, so convert to int)
        total_succ_requests_v1_0 = int(r.get("metrics:total_succ_requests_v1_0") or 0)
        total_tokens_v1_0 = int(r.get("metrics:total_tokens_v1_0") or 0)
        total_time_ms_v1_0 = int(r.get("metrics:total_response_time_ms_v1_0") or 0)
        failed_requests_v1_0 = int(r.get("metrics:failed_requests_v1_0") or 0)

        # Calculate averages
        if total_succ_requests_v1_0 > 0:
            avg_tokens_v1_0 = total_tokens_v1_0 / total_succ_requests_v1_0
            avg_response_time_v1_0 = (total_time_ms_v1_0 / total_succ_requests_v1_0) / 1000  # Convert back to seconds
            success_rate_v1_0 = (total_succ_requests_v1_0 / (total_succ_requests_v1_0 + failed_requests_v1_0)) * 100
            
            # Calculate average cost per conversation (GPT-4o-mini pricing: $0.150 per 1M input tokens, $0.600 per 1M output tokens)
            # Assuming roughly 50% input/50% output split for simplicity
            avg_cost_per_conversation_v1_0 = (avg_tokens_v1_0 / 1_000_000) * ((0.150 + 0.600) / 2)
        else:
            avg_tokens_v1_0 = avg_response_time_v1_0 = success_rate_v1_0 = avg_cost_per_conversation_v1_0 = 0

        return {
            "total_succ_requests_v1_0": total_succ_requests_v1_0,
            "total_tokens_v1_0": total_tokens_v1_0,
            "failed_requests_v1_0": failed_requests_v1_0,
            "avg_tokens_per_request_v1_0": round(avg_tokens_v1_0, 1),
            "avg_response_time_seconds_v1_0": round(avg_response_time_v1_0, 2),
            "success_rate_percent_v1_0": round(success_rate_v1_0, 1),
            "avg_cost_per_conversation_v1_0": round(avg_cost_per_conversation_v1_0, 6),
            "total_context_tokens_v1_0": total_context_tokens_v1_0  
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"error": "Unable to retrieve metrics"}