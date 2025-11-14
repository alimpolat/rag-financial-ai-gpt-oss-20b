"""
Security utilities and validation functions.
"""
import os
import re
import hashlib
import mimetypes
from typing import List, Optional, Tuple
from fastapi import HTTPException, UploadFile
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

from core.config import settings
from core.logging import get_logger

logger = get_logger("security")


class SecurityValidator:
    """Security validation utilities."""
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """
        Validate filename for security.
        
        Args:
            filename: The filename to validate
            
        Returns:
            True if filename is valid, False otherwise
        """
        if not filename or len(filename) > 255:
            return False
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in filename for char in dangerous_chars):
            return False
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    @staticmethod
    def validate_file_content(file_content: bytes, filename: str) -> Tuple[bool, str]:
        """
        Validate file content using magic numbers and other checks.
        
        Args:
            file_content: The file content as bytes
            filename: The filename for context
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_content:
            return False, "File is empty"
        
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            return False, f"File size {file_size_mb:.2f}MB exceeds limit of {settings.MAX_FILE_SIZE_MB}MB"
        
        # Get file extension
        file_extension = os.path.splitext(filename)[1].lower()
        
        # Validate file type using magic numbers if available
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_buffer(file_content, mime=True)
                logger.info(f"Detected MIME type: {mime_type} for file: {filename}")
                
                # Map allowed extensions to MIME types
                allowed_mime_types = {
                    '.pdf': ['application/pdf'],
                    '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                    '.txt': ['text/plain'],
                    '.html': ['text/html'],
                    '.md': ['text/markdown', 'text/plain']
                }
                
                if file_extension in allowed_mime_types:
                    expected_mime_types = allowed_mime_types[file_extension]
                    if mime_type not in expected_mime_types:
                        return False, f"File content doesn't match expected type for {file_extension}"
                else:
                    return False, f"File extension {file_extension} not allowed"
                    
            except Exception as e:
                logger.warning(f"Could not determine MIME type for {filename}: {e}")
                # Fall back to extension validation
                if file_extension not in settings.ALLOWED_FILE_TYPES:
                    return False, f"File type {file_extension} not allowed"
        else:
            # Fall back to extension validation when magic is not available
            logger.info(f"Magic library not available, using extension validation for {filename}")
            if file_extension not in settings.ALLOWED_FILE_TYPES:
                return False, f"File type {file_extension} not allowed"
        
        # Additional security checks
        if SecurityValidator._contains_suspicious_content(file_content):
            return False, "File contains suspicious content"
        
        return True, ""
    
    @staticmethod
    def _contains_suspicious_content(content: bytes) -> bool:
        """
        Check for suspicious content in file.
        
        Args:
            content: File content as bytes
            
        Returns:
            True if suspicious content is found
        """
        # Convert to string for pattern matching
        try:
            content_str = content.decode('utf-8', errors='ignore')
        except:
            content_str = str(content)
        
        # Check for potential script injection
        script_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'eval\s*\(',
            r'exec\s*\(',
        ]
        
        for pattern in script_patterns:
            if re.search(pattern, content_str, re.IGNORECASE):
                return True
        
        # Check for potential command injection
        command_patterns = [
            r'rm\s+-rf',
            r'del\s+/s',
            r'format\s+',
            r'chmod\s+777',
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, content_str, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe storage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path components
        filename = os.path.basename(filename)
        
        # Replace dangerous characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)
        
        # Remove multiple dots
        filename = re.sub(r'\.+', '.', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self._requests = {}
        self._max_requests = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self._window_seconds = 60
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed for the client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            True if request is allowed
        """
        import time
        current_time = time.time()
        
        if client_id not in self._requests:
            self._requests[client_id] = []
        
        # Remove old requests outside the window
        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id]
            if current_time - req_time < self._window_seconds
        ]
        
        # Check if under limit
        if len(self._requests[client_id]) < self._max_requests:
            self._requests[client_id].append(current_time)
            return True
        
        return False
    
    def get_remaining_requests(self, client_id: str) -> int:
        """
        Get remaining requests for the client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Number of remaining requests
        """
        import time
        current_time = time.time()
        
        if client_id not in self._requests:
            return self._max_requests
        
        # Remove old requests outside the window
        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id]
            if current_time - req_time < self._window_seconds
        ]
        
        return max(0, self._max_requests - len(self._requests[client_id]))


# Global rate limiter instance
rate_limiter = RateLimiter()


def validate_upload_file(file: UploadFile) -> None:
    """
    Validate uploaded file for security.
    
    Args:
        file: The uploaded file
        
    Raises:
        HTTPException: If file is invalid
    """
    # Validate filename
    if not SecurityValidator.validate_filename(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )
    
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not allowed. Allowed types: {settings.ALLOWED_FILE_TYPES}"
        )


def get_client_id(request) -> str:
    """
    Get unique client identifier for rate limiting.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client identifier string
    """
    # Try to get from X-Forwarded-For header first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Fall back to client host
    return request.client.host if request.client else "unknown"
