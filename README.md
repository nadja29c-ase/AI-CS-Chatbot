# 🤖 AI Customer Support Chatbot
**TechMarkt Customer Service Chatbot - "Rob"**

Multi-version chatbot project demonstrating AI solution development and technical evolution, built as a hands-on learning journey in modern AI development practices.
*Note: TechMarkt is a fictional company created for this portfolio project to demonstrate real-world AI solution development.*

![Status](https://img.shields.io/badge/status-Active%20Development-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![AI](https://img.shields.io/badge/AI-OpenAI%20GPT--4o--mini-orange)

## 📋 Table of Contents

- [Description](#description)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Development Approach](#development-approach)
- [Getting Started](#getting-started)
- [License](#license)

## Description

TechMarkt, a leading German online retailer specializing in consumer electronics and household appliances, faces a critical challenge in their digital-first business model: providing personalized customer consultation at scale.

### Business Problem

As an online-only retailer, TechMarkt identified that customers often feel overwhelmed by their extensive product catalog and require expert guidance during the purchase decision process. Without physical stores or accessible consultation services, many customers struggle to make confident purchase decisions, particularly non-technical customers who need simplified product recommendations tailored to their specific needs.


### Solution and Value Proposition

Rob, an AI-powered customer service chatbot, addresses this challenge by providing:
- **Instant Product Consultation** - Personalized recommendations based on customer requirements
- **Simplified Technical Guidance** - Complex product specifications translated into customer-friendly language  
- **Order Support** - Streamlined assistance with order fulfillment and tracking
- **24/7 FAQ Resolution** - Immediate responses to common customer inquiries

### Business Impact

This solution enables TechMarkt to offer the consultation experience that customers need but typically can't access online, delivering improved purchase confidence, higher customer conversion rates (hypothesis to be proven), and customer support relief by automating routine inquiries.

## Technology Stack

**Core Technologies:**
- **Backend**: Python (Flask web framework)  
- **AI Integration**: OpenAI GPT-4o-mini API
- **Database**: Redis for session management and metrics
- **Frontend**: HTML/CSS/JavaScript
- **Deployment**: Render

| Version | AI Framework | Database | Key Learning |
|---------|-------------|----------|--------------|
| v1.0 | OpenAI API | Redis | Production web apps with AI |
| v1.1 | OpenAI API + LangChain | Redis + ChromaDB/Chroma Cloud | RAG, vector databases & semantic retrieval |

## Project Structure
```
AI-CS-Chatbot/
├── LICENSE
├── README.md                    # Project overview and context
├── cs_chatbot_v1.0/            # Static knowledge base implementation
│   ├── app.py
│   ├── requirements.txt
│   └── README.md               # v1.0 overview and setup instructions
└── cs_chatbot_v1.1/            # RAG-optimized implementation
    ├── app.py
    ├── services/
    │   ├── conversation_service.py
    │   └── rag_service.py
    └── README.md               # v1.1 overview and setup instructions
```

## Development Approach

- Built using AI-assisted development practices
- Leveraged Claude/ChatGPT for code generation and debugging
- Used AI as a learning tutor for full-stack development and AI integration
- Applied AI tools for architecture decisions and problem-solving

## Getting Started

**Prerequisite**: OpenAI API key

Each version is self-contained with its own setup instructions:

1. **[v1.0](./cs_chatbot_v1.0/)** - Complete production chatbot
2. **[v1.1](./cs_chatbot_v1.1/)** - RAG-optimized implementation with 35.4% context reduction

**Live Demo:**
- [🚀 TechMarkt CS Chatbot v1.1](https://ai-chatbot-us1u.onrender.com)
- [📊 Performance Analytics](https://ai-chatbot-us1u.onrender.com/metrics)

## License

MIT License - see LICENSE file for details.

