# CS Chatbot v1.0 - Static Knowledge Base Implementation

![V1.0](https://img.shields.io/badge/version-v1.0-blue)
![Status](https://img.shields.io/badge/status-Production-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Key Features](#key-features)
- [Technical Implementation](#technical-implementation)
- [Setup & Deployment](#setup--deployment)
- [Performance Metrics](#performance-metrics)
- [Demo](#demo)

## Architecture Overview

v1.0 implements a production-ready chatbot with comprehensive metrics tracking and session management.

### Core Design Decisions
- **Static Knowledge Base**: TechMarkt's product information, policies, and FAQ data are directly included in the system prompt text. The complete context (system prompt + behavior guidelines + knowledge base) totaling 2,483 tokens is passed with every API call, creating a consistent but token-intensive approach
- **Session Management**: Redis-based conversation memory with automatic cleanup
- **Metrics Tracking**: Essential performance monitoring for optimization analysis
- **Error Handling**: Graceful fallbacks and detailed logging for production reliability

### Architecture Diagram
```
User Request → Flask App → OpenAI API → Response
                ↓ ↑              ↓
        Redis (Sessions + Metrics) ← Metrics Collection
                ↓
        Metrics Dashboard (/metrics)
```

## Key Features

### AI Integration
- **OpenAI GPT-4o-mini** with optimized prompt engineering
- **Multi-turn conversations** with context retention across sessions
- **Bilingual support** (German/English) with native-quality responses
- **Controlled hallucinations** within business constraints for realistic demos

### Production Features
- **Redis session management** for scalability and persistence
- **Real-time metrics tracking** (tokens, costs, response times, success rates)
- **Error handling and logging** with graceful failure recovery
- **Responsive web interface** with real-time chat experience

### Metrics Dashboard
Essential performance monitoring for production operations and v1.1 optimization comparison:
- Token usage and cost analysis
- Response time monitoring  
- Success rate tracking
- Request volume monitoring

## Technical Implementation

### Core Technologies
```
Backend:     Flask 3.1.1
AI API:      OpenAI 1.97.1 (GPT-4o-mini)
Database:    Redis 6.4.0 (sessions + metrics)
Token Count: tiktoken 0.11.0
Frontend:    HTML/CSS/JavaScript
Deployment:  Render (with Redis Cloud)
```

### Security
- Environment variables for sensitive data (API keys, secrets)
- Input validation (1000 character message limit)
- No API keys stored in code
- Redis session isolation per user
- Graceful error handling without exposing internal details

## Setup & Deployment

### Prerequisites
```bash
Python 3.10+
OpenAI API key
Redis instance (local or cloud)
```

### Local Development
```bash
# Clone and navigate
git clone <repository>
cd cs_chatbot_v1.0

# Install dependencies
pip install -r requirements.txt

# Create .env file with required variables
OPENAI_API_KEY=sk-your-key-here
FLASK_SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379

# Run application
python app.py
```

### Deployment (Render)
1. Connect GitHub repository
2. Set up Redis Cloud instance 
3. Set environment variables in Render dashboard (including Redis Cloud URL)
4. Deploy with automatic builds on push

## Performance Metrics

### Current Production Stats
```
Average Response Time:     2.35 seconds
Success Rate:             100.0% (17/17 requests)
Average Token Usage:       3,840 tokens/conversation
Cost per Conversation:    $0.00144 average
Context Size:             2,483 tokens (static baseline)
Total Requests:           17 successful
```

*Note: Metrics reset periodically due to Redis Cloud free plan limitations (no data persistence). Persistent metrics tracking is implemented in v1.1.*

### Metrics Collection
Real-time performance tracking available at `/metrics` endpoint.

## Demo

** Live Application:** [TechMarkt CS Chatbot](https://ai-chatbot-us1u.onrender.com)  
** Metrics Dashboard:** [Performance Analytics](https://ai-chatbot-us1u.onrender.com/metrics)

---

**Next:** Explore [v1.1 RAG optimization](../cs_chatbot_v1.1-rag/) for token efficiency improvements.

### v1.0 → v1.1 Improvements:
1. **Token optimization** (RAG vs static knowledge)
2. **Faster response times** (smaller prompts → reduced processing time)
3. **Persistent metrics** (solving the Redis free plan limitation)  
4. **Better cost analysis** (accurate long-term tracking)