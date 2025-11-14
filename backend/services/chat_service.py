"""
Chat service for handling user interactions.
"""
from typing import List, Optional, Dict, Any
import time
import uuid
import logging

from services.rag_service import RAGService
from core.logging import get_logger
from core.exceptions import RAGPipelineError

logger = get_logger("chat_service")


class ChatService:
    """Service for handling chat interactions."""
    
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.conversation_history = {}
    
    async def initialize(self):
        """Initialize the chat service."""
        logger.info("Initializing chat service...")
        # RAG service is already initialized via dependency injection
        logger.info("Chat service initialized successfully")
    
    async def process_message(
        self,
        message: str,
        context_docs: Optional[List[str]] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response.
        
        Args:
            message: User message
            context_docs: Optional list of document IDs for context
            conversation_id: Optional conversation ID for maintaining context
            
        Returns:
            Dictionary containing response and metadata
        """
        start_time = time.time()
        
        try:
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            # Process message through RAG pipeline
            rag_result = await self.rag_service.process_query(
                query=message,
                top_k=5,
                score_threshold=0.7
            )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Store in conversation history
            self._update_conversation_history(
                conversation_id=conversation_id,
                user_message=message,
                ai_response=rag_result["response"],
                sources=rag_result["sources"]
            )
            
            return {
                "response": rag_result["response"],
                "sources": rag_result["sources"],
                "confidence": rag_result["confidence"],
                "processing_time": processing_time,
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            raise
    
    def _update_conversation_history(
        self,
        conversation_id: str,
        user_message: str,
        ai_response: str,
        sources: List[str]
    ):
        """Update conversation history."""
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        self.conversation_history[conversation_id].append({
            "timestamp": time.time(),
            "user_message": user_message,
            "ai_response": ai_response,
            "sources": sources
        })
        
        # Keep only last 10 exchanges per conversation
        if len(self.conversation_history[conversation_id]) > 10:
            self.conversation_history[conversation_id] = \
                self.conversation_history[conversation_id][-10:]
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a given conversation ID."""
        return self.conversation_history.get(conversation_id, [])
    
    def clear_conversation_history(self, conversation_id: Optional[str] = None):
        """Clear conversation history."""
        if conversation_id:
            self.conversation_history.pop(conversation_id, None)
        else:
            self.conversation_history.clear()
