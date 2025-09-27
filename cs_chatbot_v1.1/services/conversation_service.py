import logging
import os
import time
from typing import List, Dict, Any, Tuple
from services.rag_service import RAGService
from openai import OpenAI

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, rag_service: RAGService):
        # Enable conversation service with RAG capabilities.
        self.rag_service = rag_service
        self.openai_client = self.create_openai_client()

    def initialize_conversation(self, prompts: Dict[str, str]) -> List[Dict]:
        # Initialize new conversation with static prompts only.
        conversation = [
            {"role": "system", "content": prompts["sys_prompt.txt"]},
            {"role": "system", "content": prompts["behaviour_guidelines.txt"]},
        ]
        logger.info("New conversation session initialized with system prompts")
        return conversation

    def build_conversation_with_context(self, conversation: List[Dict], user_message: str) -> List[Dict]:
        # Add user message and relevant knowledge context to conversation.
        conversation.append({"role": "user", "content": user_message})

        # Retrieve and add relevant knowledge context - let RAG failures bubble up to centralized handlers.
        relevant_knowledge = self.rag_service.get_relevant_knowledge(user_message)
        if relevant_knowledge:
            conversation.append({"role": "system", "content": relevant_knowledge})
        
        return conversation

    def add_assistant_response(self, conversation: List[Dict], ai_response: str) -> List[Dict]:
        # Add AI response to conversation history.
        conversation.append({"role": "assistant", "content": ai_response})
        return conversation

    def create_openai_client(self) -> OpenAI:
        # Create OpenAI client with API key.
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        return client

    def get_ai_response(self, messages: List[Dict]) -> Tuple[str, Dict[str, Any]]:
        """Get AI response and return both response and metrics data.

        Args:
            messages: Complete conversation including system prompts, context, and user message

        Returns:
            Tuple of (ai_response, metrics_data) where metrics_data contains:
            - response_time: Time taken for API call
            - tokens_used: Total tokens used in request
            - success: Boolean indicating if request succeeded.
        """
        start_time = time.time()

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_completion_tokens=800,
            temperature=0.7,
        )

        end_time = time.time()
        response_time = end_time - start_time
        tokens_used = response.usage.total_tokens

        ai_response = response.choices[0].message.content
        logger.info(f"AI response generated: {ai_response[:50]}... (truncated)")

        metrics_data = {
            "response_time": response_time,
            "tokens_used": tokens_used,
            "success": True
        }

        return ai_response, metrics_data