# CS Chatbot v1.1 - RAG-Optimized Implementation

![V1.1](https://img.shields.io/badge/version-v1.1-blue)
![Status](https://img.shields.io/badge/status-Production-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Technical Implementation](#technical-implementation)
- [Setup & Deployment](#setup--deployment)
- [Performance Metrics](#performance-metrics)
- [Development Insights](#development-insights)
- [Demo](#demo)

## Architecture Overview

v1.1 implements a RAG (Retrieval-Augmented Generation) system for optimized token usage and cost efficiency while maintaining production quality.

**Note**: v1.1 maintains all v1.0 user-facing features (bilingual support, multi-turn conversations, product knowledge) while optimizing internal architecture for token efficiency and cost reduction.

### Core Design Decisions
- **Incremental RAG Integration**: Preserves all v1.0 infrastructure (Redis sessions, Flask routing) while adding modular RAG layer and refactoring to service architecture - ensures stability and backwards compatibility
- **Three-Layer Service Architecture**: Separation of concerns (Flask for HTTP/validation, Conversation Service for orchestration and OpenAI API calls, RAG Service for knowledge retrieval)
- **Session Management**: Redis for persistent multi-turn conversation history (preserved from v1.0)
- **Vector Storage**: Environment-aware deployment (local ChromaDB persistence in development, Chroma Cloud in production)
- **Metrics Storage**: JSON-based persistence solves Redis free plan limitations from v1.0

### Architecture Diagram
```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Flask App (Routes, Validation, Error Handling) │
└───────┬─────────────────────────────────────────┘
        │
        ▼
┌───────────────┐         ┌──────────────────────┐
│ Redis         │◄────────┤ Conversation Service │
│ (Sessions)    │         │  (Orchestration)     │
└───────────────┘         └──────┬───────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │                         │
                    ▼                         ▼
         ┌─────────────────────┐   ┌──────────────────┐
         │  RAG Service        │   │  OpenAI API      │
         │  (LangChain)        │   │  (GPT-4o-mini)   │
         └──────┬──────────────┘   └────────┬─────────┘
                │                           │
                ▼                           │
         ┌─────────────────┐                │
         │  Chroma DB      │                │
         │  (Vectors)      │                │
         └─────────────────┘                │
                                            ▼
                                   ┌─────────────────┐
                                   │ Metrics Storage │
                                   │ (JSON File)     │
                                   └─────────────────┘
```

## Technical Implementation

### RAG Implementation
- **LangChain Framework** orchestrates the entire RAG pipeline:
  - `TextLoader` for knowledge base ingestion with UTF-8 encoding
  - `RecursiveCharacterTextSplitter` for intelligent document chunking
  - `Chroma` vectorstore wrapper with automatic embedding integration
  - `as_retriever()` for similarity-based search with score thresholds
- **ChromaDB** with environment-aware deployment (local dev / Chroma Cloud production)
- **Semantic Chunking Strategy** with custom separators for FAQ, products, policies
- **Smart Intent Detection** triggers RAG only for information-seeking queries
- **Empty Retrieval Tracking** logs queries with no relevant knowledge for gap analysis

### AI Integration
- **OpenAI GPT-4o-mini** with context-optimized prompting
- **Dynamic Context Assembly** (static prompts + RAG-retrieved chunks)
- **Bilingual Support** (German/English) with native-quality responses
- **Multi-turn Conversations** with Redis session management

### Production Features
- **Persistent Metrics Tracking** with JSON file storage (no Redis dependency)
- **Robust Error Handling** with explicit exception types
- **Chroma Cloud Integration** for scalable vector storage

### Metrics Dashboard
Comprehensive performance monitoring with v1.0 comparison:
- Token usage and cost analysis (context size tracking)
- Response time monitoring
- Success rate tracking
- Empty retrieval analysis for knowledge gap identification

### Core Technologies
```
Backend:        Flask 3.1.1
AI API:         OpenAI 1.97.1 (GPT-4o-mini)
AI Framework:   LangChain 0.3.0
Vector DB:      ChromaDB 1.0.20 + Chroma Cloud
Embeddings:     OpenAI text-embedding-3-small
Session DB:     Redis 6.4.0
Token Count:    tiktoken 0.8.0
Frontend:       HTML/CSS/JavaScript
Deployment:     Render
Dependency Mgmt: Poetry 2.2.1
```

### Security
- Environment variables for all sensitive data (API keys, credentials)
- UTF-8 encoding for cross-platform compatibility
- Input validation (1000 character message limit)
- Redis session isolation per user
- No credentials in code or version control

## Setup & Deployment

### Prerequisites
```bash
Python 3.10+
OpenAI API key
Redis instance (local or cloud)
Chroma Cloud account (for production)
Poetry (dependency management)
```

### Local Development
```bash
# Clone and navigate
git clone <repository>
cd cs_chatbot_v1.1

# Install dependencies with Poetry
poetry install

# Create .env file with required variables
OPENAI_API_KEY=sk-your-key-here
FLASK_SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379
DEPLOYMENT_ENV=development

# Create logs directory
mkdir logs

# Run application
poetry run python app.py
```

### Deployment (Render + Chroma Cloud)
1. **Set up Chroma Cloud**:
   - Create account at [Chroma Cloud](https://www.trychroma.com/)
   - Create new database
   - Note: API key, tenant ID, database name

2. **Configure Render**:
   - Connect GitHub repository
   - Set Root Directory: `cs_chatbot_v1.1`
   - Build Command: `pip install poetry && poetry install --only main --no-root`
   - Start Command: `poetry run python app.py`

3. **Environment Variables** (Render Dashboard):
   ```
   OPENAI_API_KEY=sk-your-key-here
   FLASK_SECRET_KEY=your-secret-key-here
   REDIS_URL=redis://your-redis-cloud-url
   DEPLOYMENT_ENV=production
   CHROMA_API_KEY=your-chroma-api-key
   CHROMA_TENANT=your-tenant-id
   CHROMA_DATABASE=cs_chatbot_v1.1
   ```

4. Deploy with automatic builds on push

## Performance Metrics

### Production Stats (v1.1)
```
Total Requests:           17
Average Response Time:    3.06 seconds
Success Rate:             100.0%
Average Token Usage:      3,629.4 tokens/conversation
Average Context Size:     1,604.9 tokens
Cost per Conversation:    $0.001361
Empty Retrievals:         3 (knowledge gaps identified)
```

### v1.0 vs v1.1 Comparison

| Metric | v1.0 | v1.1 | Improvement |
|--------|------|------|-------------|
| **Context Size** | 2,483 tokens | 1,604.9 tokens | **-35.4%** ✅ |
| **Response Time** | 2.35s | 3.06s | +30.2% ⚠️ |
| **Cost/Conversation** | $0.00144 | $0.001361 | **-5.5%** ✅ |
| **Token Usage** | 3,840 tokens | 3,629.4 tokens | **-5.5%** ✅ |
| **Metrics Persistence** | No (Redis) | Yes (JSON) | **✅** |

**Analysis**: v1.1 achieved **35.4% context reduction** (878.1 tokens saved), enabling more conversation history in the same context window. Response time increased 30.2% due to RAG retrieval and vector search overhead, but the 5.5% cost reduction and persistent metrics tracking make this trade-off acceptable for the learning objectives.

### Empty Retrieval Insights
Knowledge gaps identified in production:
1. "I am a software developer and i need a complete homeoffice setup" - Complex multi-product queries
2. "kann ich es in raten abbezahlen?" - Payment plan information
3. "Hey, i need a present for my dad.. he is into sports" - Out-of-domain requests

## Development Insights

### AI-Assisted Development
This project was built using **Claude Code** for:
- Architecture design and technical decisions
- Code generation and debugging
- Learning full-stack development and AI integration
- Problem-solving and optimization strategies

### Chunking and Retrieval:
Analysis revealed semantic gaps in retrieval (cosine distances 1.0-1.5), which could be improved by extending the knowledge base and product metadata. Current implementation achieves acceptable performance with controlled hallucinations and meets the primary goal of 35% context reduction.

## Demo

**Live Application:** [TechMarkt CS Chatbot v1.1](https://ai-chatbot-us1u.onrender.com)
**Metrics Dashboard:** [Performance Analytics v1.1](https://ai-chatbot-us1u.onrender.com/metrics)

---

**Previous:** [v1.0 Static Implementation](../cs_chatbot_v1.0/)
