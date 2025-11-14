"""
Chat endpoints for RAG interactions.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import logging

from services.rag_service import RAGService
from services.chat_service import ChatService
from core.dependencies import get_rag_service, get_chat_service
from core.logging import get_logger
from core.exceptions import RAGPipelineError
from core.auth import get_current_user, get_current_user_optional, TokenData, check_rate_limit

router = APIRouter()
logger = get_logger("chat_routes")


class ChatMessage(BaseModel):
    """Chat message model."""
    message: str
    context_docs: Optional[List[str]] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    sources: List[str]
    confidence: float
    processing_time: float


@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_message: ChatMessage,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: Optional[TokenData] = Depends(get_current_user_optional)  # Made optional for testing
):
    """
    Process a chat message using RAG pipeline.
    """
    try:
        logger.info(f"Processing chat message: {chat_message.message[:100]}...")
        
        response = await chat_service.process_message(
            message=chat_message.message,
            context_docs=chat_message.context_docs
        )
        
        return response
        
    except RAGPipelineError as e:
        logger.warning(f"RAG pipeline error: {e}")
        raise HTTPException(status_code=422, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Unexpected error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")


@router.get("/chat/history")
async def get_chat_history():
    """Get chat history."""
    # TODO: Implement chat history retrieval
    return {"history": []}


@router.delete("/chat/history")
async def clear_chat_history():
    """Clear chat history."""
    # TODO: Implement chat history clearing
    return {"message": "Chat history cleared"}
