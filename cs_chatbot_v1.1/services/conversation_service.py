import logging
import os
import time
from typing import List, Dict
from services.rag_service import RAGService
from openai import OpenAI
import basic_metrics

logger = logging.getLogger(__name__)

# === CONFIGURATION ===

def create_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)

# === HELPER FUNCTIONS ===

def needs_rag_retrieval(user_query: str) -> bool:
    """Detect if query needs RAG retrieval using flexible OR conditions."""

    # German question/intent indicators.
    german_indicators = [
        # Question words
        "was", "wie", "warum", "wo", "wann", "welche", "welcher", "welches",
        # Intent phrases
        "ich brauche", "ich suche", "suche nach", "zeig mir", "zeige mir",
        "empfehlung", "empfiehl", "kaufen", "möchte", "will haben",
        "gibt es", "haben sie", "können sie", "kannst du"
    ]

    # English question/intent indicators.
    english_indicators = [
        # Question words.
        "what", "how", "why", "where", "when", "which", "who",
        # Intent phrases.
        "i need", "i want", "looking for", "show me", "recommend",
        "buy", "purchase", "do you have", "can you", "is there"
    ]

    # Product/tech domain words.
    product_indicators = [
        "laptop", "smartphone", "tablet", "monitor", "computer", "gaming",
        "programming", "tech", "device", "machine", "electronic", "homeoffice"
    ]

    query_lower = user_query.lower().strip()

    # Check conditions: question mark OR intent words OR product words.
    return ("?" in user_query or
            any(word in query_lower for word in german_indicators) or
            any(word in query_lower for word in english_indicators) or
            any(word in query_lower for word in product_indicators))

# === BUSINESS LOGIC ===

class ConversationService:
    def __init__(self, rag_service: RAGService):
        # Enable conversation service with RAG capabilities.
        self.rag_service = rag_service
        self.openai_client = create_openai_client()
        self.rag_content = None  # Store RAG content for metrics tracking.

    def initialize_conversation(self, prompts: Dict[str, str]) -> List[Dict]:
        # Initialize new conversation with static prompts only.
        conversation = [
            {"role": "system", "content": prompts["sys_prompt.txt"]},
            {"role": "system", "content": prompts["behaviour_guidelines.txt"]},
        ]

        logger.info("New conversation session initialized with system prompts.")
        return conversation

    def build_conversation_with_context(self, conversation: List[Dict], user_message: str) -> List[Dict]:
        # Add user message to conversation.
        conversation.append({"role": "user", "content": user_message})

        # Only trigger knowledge retrieval if user query needs RAG.
        if needs_rag_retrieval(user_message):
            relevant_knowledge = self.rag_service.get_relevant_knowledge(user_message)
            if relevant_knowledge:
                conversation.append({"role": "system", "content": relevant_knowledge})
                self.rag_content = relevant_knowledge  # Store for metrics
            else:
                # Track empty retrieval only for actual information requests.
                basic_metrics.track_empty_retrieval_v1_1(user_message)
                self.rag_content = None
        else:
            # Skip RAG entirely for conversational messages (thank you, hello, etc.).
            self.rag_content = None

        return conversation

    def get_ai_response(self, messages: List[Dict]) -> str:
        """Get AI response from OpenAI API. Extraxt open ai call data for metrics tracking.

        Args:
            messages: Complete conversation including system prompts, context, and user message

        Returns:
            AI response string. Metrics are tracked internally via basic_metrics module.
        """
        start_time = time.time()

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_completion_tokens=800,
                temperature=0.7,
            )

            # Extract AI response from OpenAI response.
            ai_response = response.choices[0].message.content
            logger.info(f"AI response generated: {ai_response[:50]}... (truncated)")

            # Extract openai call data for metrics tracking.
            end_time = time.time()
            response_time = end_time - start_time
            conversation_tokens = response.usage.total_tokens

            # Track successful request metrics - pass conversation data for token calculation.
            basic_metrics.track_metrics_v1_1(
                response_time,
                conversation_tokens,
                conversation_messages=messages,
                rag_content=self.rag_content,
                success=True
            )

            return ai_response

        except Exception as e:
            # Track failed request.
            basic_metrics.track_metrics_v1_1(0, 0, success=False)
            raise

    def add_assistant_response(self, conversation: List[Dict], ai_response: str) -> List[Dict]:
        # Add AI response to conversation history.
        conversation.append({"role": "assistant", "content": ai_response})
        return conversation