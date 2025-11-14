"""
Unit tests for security module.
"""
import pytest
from unittest.mock import Mock
from fastapi import UploadFile, HTTPException

from core.security import SecurityValidator, validate_upload_file, rate_limiter, get_client_id


class TestSecurityValidator:
    """Test security validation functions."""
    
    def test_validate_filename_valid(self):
        """Test valid filename validation."""
        valid_filenames = [
            "document.pdf",
            "financial_report.docx",
            "data.txt",
            "report_2024.html",
            "README.md"
        ]
        
        for filename in valid_filenames:
            assert SecurityValidator.validate_filename(filename) is True
    
    def test_validate_filename_invalid(self):
        """Test invalid filename validation."""
        invalid_filenames = [
            "",  # Empty
            "a" * 300,  # Too long
            "../document.pdf",  # Path traversal
            "document<>.pdf",  # Dangerous characters
            "CON.txt",  # Reserved name
            "document.pdf/",  # Path separator
        ]
        
        for filename in invalid_filenames:
            assert SecurityValidator.validate_filename(filename) is False
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("../document.pdf", "document.pdf"),
            ("file<>:\"|?*.txt", "file_______.txt"),
            ("multiple...dots.txt", "multiple.dots.txt"),
            ("normal_file.pdf", "normal_file.pdf"),
        ]
        
        for input_name, expected in test_cases:
            result = SecurityValidator.sanitize_filename(input_name)
            assert result == expected
    
    def test_validate_file_content_valid(self):
        """Test valid file content validation."""
        # Mock PDF content (minimal PDF header)
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        
        is_valid, error = SecurityValidator.validate_file_content(pdf_content, "test.pdf")
        assert is_valid is True
        assert error == ""
    
    def test_validate_file_content_empty(self):
        """Test empty file content validation."""
        is_valid, error = SecurityValidator.validate_file_content(b"", "test.pdf")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_validate_file_content_suspicious(self):
        """Test suspicious content detection."""
        suspicious_content = b"<script>alert('xss')</script>"
        is_valid, error = SecurityValidator.validate_file_content(suspicious_content, "test.txt")
        assert is_valid is False
        assert "suspicious" in error.lower()
    
    def test_contains_suspicious_content(self):
        """Test suspicious content detection."""
        suspicious_patterns = [
            b"<script>alert('xss')</script>",
            b"javascript:alert('xss')",
            b"eval('malicious')",
            b"rm -rf /",
            b"del /s *.*",
        ]
        
        for content in suspicious_patterns:
            assert SecurityValidator._contains_suspicious_content(content) is True
        
        # Test normal content
        normal_content = b"This is a normal document with no suspicious content."
        assert SecurityValidator._contains_suspicious_content(normal_content) is False


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_initial_state(self):
        """Test rate limiter initial state."""
        client_id = "test_client"
        assert rate_limiter.is_allowed(client_id) is True
        assert rate_limiter.get_remaining_requests(client_id) == 59  # 60 - 1
    
    def test_rate_limiter_exceed_limit(self):
        """Test rate limiter when limit is exceeded."""
        client_id = "test_client_2"
        
        # Make maximum allowed requests
        for _ in range(60):
            rate_limiter.is_allowed(client_id)
        
        # Next request should be blocked
        assert rate_limiter.is_allowed(client_id) is False
        assert rate_limiter.get_remaining_requests(client_id) == 0


class TestUploadFileValidation:
    """Test upload file validation."""
    
    def test_validate_upload_file_valid(self):
        """Test valid upload file validation."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "valid_document.pdf"
        
        # Should not raise exception
        validate_upload_file(mock_file)
    
    def test_validate_upload_file_invalid_filename(self):
        """Test invalid filename validation."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "../malicious.pdf"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_file(mock_file)
        
        assert exc_info.value.status_code == 400
        assert "Invalid filename" in str(exc_info.value.detail)
    
    def test_validate_upload_file_invalid_extension(self):
        """Test invalid file extension validation."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.exe"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_file(mock_file)
        
        assert exc_info.value.status_code == 400
        assert "not allowed" in str(exc_info.value.detail)


class TestClientIdentification:
    """Test client identification for rate limiting."""
    
    def test_get_client_id_from_forwarded_for(self):
        """Test getting client ID from X-Forwarded-For header."""
        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        mock_request.client = None
        
        client_id = get_client_id(mock_request)
        assert client_id == "192.168.1.1"
    
    def test_get_client_id_from_client_host(self):
        """Test getting client ID from client host."""
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.100"
        
        client_id = get_client_id(mock_request)
        assert client_id == "192.168.1.100"
    
    def test_get_client_id_fallback(self):
        """Test getting client ID fallback."""
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = None
        
        client_id = get_client_id(mock_request)
        assert client_id == "unknown"
