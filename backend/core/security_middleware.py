"""
Security middleware for FastAPI application.
"""
from fastapi import Request, HTTPException
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import uuid

from core.security import rate_limiter, get_client_id
from core.logging import get_logger

logger = get_logger("security_middleware")


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for rate limiting and security headers."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._rate_limit_enabled = True
        self._security_headers_enabled = True
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security middleware."""
        start_time = time.time()
        
        # Generate correlation ID if not present
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Rate limiting
        if self._rate_limit_enabled:
            client_id = get_client_id(request)
            if not rate_limiter.is_allowed(client_id):
                logger.warning(f"Rate limit exceeded for client: {client_id}")
                return Response(
                    content="Rate limit exceeded",
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": str(rate_limiter._max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time() + 60)),
                        "Retry-After": "60"
                    }
                )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        if self._security_headers_enabled:
            response.headers.update({
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "X-Correlation-ID": correlation_id,
            })
        
        # Add rate limit headers
        if self._rate_limit_enabled:
            client_id = get_client_id(request)
            remaining = rate_limiter.get_remaining_requests(client_id)
            response.headers.update({
                "X-RateLimit-Limit": str(rate_limiter._max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time() + 60))
            })
        
        # Log request
        processing_time = time.time() - start_time
        logger.info(
            f"Request processed: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {processing_time:.3f}s - "
            f"Correlation-ID: {correlation_id}"
        )
        
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for input validation and sanitization."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Process request through input validation."""
        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > 50 * 1024 * 1024:  # 50MB limit
                    raise HTTPException(
                        status_code=413,
                        detail="Request too large"
                    )
            except ValueError:
                pass
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type:
                # Allow multipart/form-data for file uploads
                if not request.url.path.endswith("/upload"):
                    raise HTTPException(
                        status_code=400,
                        detail="Content-Type header required"
                    )
        
        # Process request
        response = await call_next(request)
        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security considerations."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Process request through CORS middleware."""
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            response.headers.update({
                "Access-Control-Allow-Origin": "*",  # Configure based on your needs
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Correlation-ID",
                "Access-Control-Max-Age": "86400",
            })
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers to response
        response.headers.update({
            "Access-Control-Allow-Origin": "*",  # Configure based on your needs
            "Access-Control-Allow-Credentials": "true",
        })
        
        return response
