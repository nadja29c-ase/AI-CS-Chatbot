import time
import redis
import logging

logger = logging.getLogger(__name__)

# Set the Redis client for metrics tracking
def initialize_metrics(redis_client):
    global r
    r = redis_client

# Track key performance metrics using Redis counters
def track_metrics(response_time, tokens_used, success=True):
    try:
        if success:
            r.incr("metrics:total_succ_requests")  # Count successful requests
            r.incr("metrics:total_tokens", tokens_used)  # Add tokens to running total
            r.incr("metrics:total_response_time_ms", int(response_time * 1000))  # Add response time in ms for redis
        else:
            r.incr("metrics:failed_requests")  # Count failed requests separately
            
    except Exception as e:
        logger.warning(f"Failed to track metrics: {e}")

# Calculate and return current metrics summary 
def get_metrics_summary():
    try:
        # Get raw counters from Redis (returns bytes, so convert to int)
        total_succ_requests = int(r.get("metrics:total_succ_requests") or 0)
        total_tokens = int(r.get("metrics:total_tokens") or 0)
        total_time_ms = int(r.get("metrics:total_response_time_ms") or 0)
        failed_requests = int(r.get("metrics:failed_requests") or 0)
        
        # Calculate averages
        if total_succ_requests > 0:
            avg_tokens = total_tokens / total_succ_requests
            avg_response_time = (total_time_ms / total_succ_requests) / 1000  # Convert back to seconds
            success_rate = (total_succ_requests / (total_succ_requests + failed_requests)) * 100
        else:
            avg_tokens = avg_response_time = success_rate = 0
            
        return {
            "total_succ_requests": total_succ_requests,
            "total_tokens": total_tokens,
            "failed_requests": failed_requests,
            "avg_tokens_per_request": round(avg_tokens, 1),
            "avg_response_time_seconds": round(avg_response_time, 2),
            "success_rate_percent": round(success_rate, 1)
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"error": "Unable to retrieve metrics"}