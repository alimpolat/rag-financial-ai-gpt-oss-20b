"""
Custom exception classes for structured error handling.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException
import uuid


class BaseRAGException(Exception):
    """Base exception for RAG Financial AI application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None,
        correlation_id: str = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "correlation_id": self.correlation_id
        }


class ServiceInitializationError(BaseRAGException):
    """Raised when a service fails to initialize."""
    pass


class DocumentProcessingError(BaseRAGException):
    """Raised when document processing fails."""
    pass


class RAGPipelineError(BaseRAGException):
    """Raised when RAG pipeline operations fail."""
    pass


class VectorStoreError(BaseRAGException):
    """Raised when vector store operations fail."""
    pass


class OllamaConnectionError(BaseRAGException):
    """Raised when Ollama connection fails."""
    pass


class FileUploadError(BaseRAGException):
    """Raised when file upload operations fail."""
    pass


class ValidationError(BaseRAGException):
    """Raised when input validation fails."""
    pass


class AuthenticationError(BaseRAGException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(BaseRAGException):
    """Raised when authorization fails."""
    pass


class RateLimitError(BaseRAGException):
    """Raised when rate limits are exceeded."""
    pass


class CacheError(BaseRAGException):
    """Raised when cache operations fail."""
    pass


class ChatSessionError(BaseRAGException):
    """Raised when chat session operations fail."""
    pass


class MessageProcessingError(BaseRAGException):
    """Raised when message processing fails."""
    pass


class SessionNotFoundError(BaseRAGException):
    """Raised when a chat session is not found."""
    pass


class DocumentNotFoundError(BaseRAGException):
    """Raised when a document is not found."""
    pass


# HTTP Exception mappings
def map_to_http_exception(exc: BaseRAGException) -> HTTPException:
    """Map custom exceptions to HTTP exceptions."""
    
    status_code_mapping = {
        ValidationError: 400,
        FileUploadError: 400,
        SessionNotFoundError: 404,
        DocumentNotFoundError: 404,
        AuthenticationError: 401,
        AuthorizationError: 403,
        RateLimitError: 429,
        DocumentProcessingError: 422,
        MessageProcessingError: 422,
        RAGPipelineError: 500,
        VectorStoreError: 500,
        CacheError: 500,
        ChatSessionError: 500,
        OllamaConnectionError: 503,
        ServiceInitializationError: 503,
    }
    
    status_code = status_code_mapping.get(type(exc), 500)
    
    return HTTPException(
        status_code=status_code,
        detail=exc.to_dict()
    )