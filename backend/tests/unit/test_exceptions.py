"""
Unit tests for custom exception handling.
"""
import pytest
from fastapi import HTTPException

from core.exceptions import (
    BaseRAGException, ServiceInitializationError, DocumentProcessingError,
    RAGPipelineError, VectorStoreError, OllamaConnectionError,
    FileUploadError, ValidationError, AuthenticationError,
    AuthorizationError, RateLimitError, map_to_http_exception
)


@pytest.mark.unit
class TestBaseRAGException:
    """Test base exception functionality."""
    
    def test_base_exception_creation(self):
        """Test creating a base exception with default values."""
        exc = BaseRAGException("Test error message")
        
        assert exc.message == "Test error message"
        assert exc.error_code == "BaseRAGException"
        assert exc.details == {}
        assert exc.correlation_id is not None
        assert len(exc.correlation_id) > 0
    
    def test_base_exception_with_custom_values(self):
        """Test creating exception with custom values."""
        details = {"key": "value", "count": 42}
        correlation_id = "test-correlation-123"
        
        exc = BaseRAGException(
            message="Custom error",
            error_code="CUSTOM_ERROR",
            details=details,
            correlation_id=correlation_id
        )
        
        assert exc.message == "Custom error"
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == details
        assert exc.correlation_id == correlation_id
    
    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        details = {"error_detail": "Something went wrong"}
        exc = BaseRAGException(
            message="Test error",
            error_code="TEST_ERROR",
            details=details,
            correlation_id="test-123"
        )
        
        result = exc.to_dict()
        
        assert result["error_code"] == "TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["details"] == details
        assert result["correlation_id"] == "test-123"
    
    def test_exception_inheritance(self):
        """Test that exception inherits from Python Exception."""
        exc = BaseRAGException("Test")
        
        assert isinstance(exc, Exception)
        assert str(exc) == "Test"


@pytest.mark.unit
class TestSpecificExceptions:
    """Test specific exception types."""
    
    def test_service_initialization_error(self):
        """Test service initialization error."""
        exc = ServiceInitializationError(
            "Failed to initialize service",
            details={"service": "RAGService"}
        )
        
        assert exc.error_code == "ServiceInitializationError"
        assert exc.message == "Failed to initialize service"
        assert exc.details["service"] == "RAGService"
    
    def test_document_processing_error(self):
        """Test document processing error."""
        exc = DocumentProcessingError(
            "Failed to process document",
            details={"document_id": "doc-123", "file_type": ".pdf"}
        )
        
        assert exc.error_code == "DocumentProcessingError"
        assert exc.message == "Failed to process document"
        assert exc.details["document_id"] == "doc-123"
    
    def test_rag_pipeline_error(self):
        """Test RAG pipeline error."""
        exc = RAGPipelineError(
            "RAG query failed",
            details={"query": "test query", "step": "retrieval"}
        )
        
        assert exc.error_code == "RAGPipelineError"
        assert exc.message == "RAG query failed"
        assert exc.details["step"] == "retrieval"
    
    def test_vector_store_error(self):
        """Test vector store error."""
        exc = VectorStoreError(
            "Vector store connection failed",
            details={"store_type": "chromadb"}
        )
        
        assert exc.error_code == "VectorStoreError"
        assert exc.message == "Vector store connection failed"
    
    def test_ollama_connection_error(self):
        """Test Ollama connection error."""
        exc = OllamaConnectionError(
            "Cannot connect to Ollama",
            details={"url": "http://localhost:11434", "model": "gpt-oss:20b"}
        )
        
        assert exc.error_code == "OllamaConnectionError"
        assert exc.message == "Cannot connect to Ollama"
    
    def test_file_upload_error(self):
        """Test file upload error."""
        exc = FileUploadError(
            "File too large",
            details={"size_mb": 100, "max_size_mb": 50}
        )
        
        assert exc.error_code == "FileUploadError"
        assert exc.message == "File too large"
        assert exc.details["size_mb"] == 100
    
    def test_validation_error(self):
        """Test validation error."""
        exc = ValidationError(
            "Invalid input format",
            details={"field": "chunk_size", "value": 0, "min_value": 100}
        )
        
        assert exc.error_code == "ValidationError"
        assert exc.message == "Invalid input format"
    
    def test_authentication_error(self):
        """Test authentication error."""
        exc = AuthenticationError(
            "Invalid credentials",
            details={"user_id": "user-123"}
        )
        
        assert exc.error_code == "AuthenticationError"
        assert exc.message == "Invalid credentials"
    
    def test_authorization_error(self):
        """Test authorization error."""
        exc = AuthorizationError(
            "Access denied",
            details={"resource": "documents", "action": "delete"}
        )
        
        assert exc.error_code == "AuthorizationError"
        assert exc.message == "Access denied"
    
    def test_rate_limit_error(self):
        """Test rate limit error."""
        exc = RateLimitError(
            "Rate limit exceeded",
            details={"limit": 60, "window": "minute", "current": 75}
        )
        
        assert exc.error_code == "RateLimitError"
        assert exc.message == "Rate limit exceeded"


@pytest.mark.unit
class TestHTTPExceptionMapping:
    """Test mapping custom exceptions to HTTP exceptions."""
    
    def test_validation_error_mapping(self):
        """Test mapping ValidationError to HTTP 400."""
        exc = ValidationError("Invalid input")
        http_exc = map_to_http_exception(exc)
        
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 400
        assert http_exc.detail["error_code"] == "ValidationError"
        assert http_exc.detail["message"] == "Invalid input"
    
    def test_file_upload_error_mapping(self):
        """Test mapping FileUploadError to HTTP 400."""
        exc = FileUploadError("File too large")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 400
        assert http_exc.detail["error_code"] == "FileUploadError"
    
    def test_authentication_error_mapping(self):
        """Test mapping AuthenticationError to HTTP 401."""
        exc = AuthenticationError("Invalid token")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 401
        assert http_exc.detail["error_code"] == "AuthenticationError"
    
    def test_authorization_error_mapping(self):
        """Test mapping AuthorizationError to HTTP 403."""
        exc = AuthorizationError("Access denied")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 403
        assert http_exc.detail["error_code"] == "AuthorizationError"
    
    def test_rate_limit_error_mapping(self):
        """Test mapping RateLimitError to HTTP 429."""
        exc = RateLimitError("Too many requests")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 429
        assert http_exc.detail["error_code"] == "RateLimitError"
    
    def test_document_processing_error_mapping(self):
        """Test mapping DocumentProcessingError to HTTP 422."""
        exc = DocumentProcessingError("Processing failed")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 422
        assert http_exc.detail["error_code"] == "DocumentProcessingError"
    
    def test_rag_pipeline_error_mapping(self):
        """Test mapping RAGPipelineError to HTTP 500."""
        exc = RAGPipelineError("Pipeline failed")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 500
        assert http_exc.detail["error_code"] == "RAGPipelineError"
    
    def test_vector_store_error_mapping(self):
        """Test mapping VectorStoreError to HTTP 500."""
        exc = VectorStoreError("Store unavailable")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 500
        assert http_exc.detail["error_code"] == "VectorStoreError"
    
    def test_ollama_connection_error_mapping(self):
        """Test mapping OllamaConnectionError to HTTP 503."""
        exc = OllamaConnectionError("Service unavailable")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 503
        assert http_exc.detail["error_code"] == "OllamaConnectionError"
    
    def test_service_initialization_error_mapping(self):
        """Test mapping ServiceInitializationError to HTTP 503."""
        exc = ServiceInitializationError("Service not ready")
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.status_code == 503
        assert http_exc.detail["error_code"] == "ServiceInitializationError"
    
    def test_unknown_exception_mapping(self):
        """Test mapping unknown exception types to HTTP 500."""
        class CustomException(BaseRAGException):
            pass
        
        exc = CustomException("Unknown error")
        http_exc = map_to_http_exception(exc)
        
        # Should default to 500
        assert http_exc.status_code == 500
        assert http_exc.detail["error_code"] == "CustomException"
    
    def test_exception_detail_preservation(self):
        """Test that exception details are preserved in HTTP mapping."""
        details = {
            "field": "chunk_size",
            "value": 0,
            "min_value": 100,
            "max_value": 4000
        }
        correlation_id = "test-correlation-456"
        
        exc = ValidationError(
            "Invalid chunk size",
            details=details,
            correlation_id=correlation_id
        )
        
        http_exc = map_to_http_exception(exc)
        
        assert http_exc.detail["details"] == details
        assert http_exc.detail["correlation_id"] == correlation_id
        assert http_exc.detail["message"] == "Invalid chunk size"


@pytest.mark.unit
class TestExceptionChaining:
    """Test exception chaining and context preservation."""
    
    def test_exception_with_cause(self):
        """Test exception with underlying cause."""
        try:
            # Simulate an underlying error
            raise ValueError("Underlying error")
        except ValueError as e:
            # Create our custom exception with cause
            rag_exc = DocumentProcessingError(
                "Document processing failed",
                details={"underlying_error": str(e)}
            )
            
            assert "Underlying error" in rag_exc.details["underlying_error"]
            assert rag_exc.message == "Document processing failed"
    
    def test_correlation_id_propagation(self):
        """Test correlation ID propagation through exception chain."""
        correlation_id = "propagate-123"
        
        # First exception
        exc1 = VectorStoreError(
            "Store connection failed",
            correlation_id=correlation_id
        )
        
        # Second exception that should preserve correlation ID
        exc2 = DocumentProcessingError(
            "Processing failed due to store error",
            correlation_id=exc1.correlation_id,
            details={"underlying_error": exc1.error_code}
        )
        
        assert exc2.correlation_id == correlation_id
        assert exc2.details["underlying_error"] == "VectorStoreError"