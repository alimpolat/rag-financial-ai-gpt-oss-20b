"""
Custom middleware for request handling, correlation IDs, and metrics.
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import set_correlation_id, get_logger, log_with_context
from core.exceptions import BaseRAGException, map_to_http_exception

logger = get_logger("middleware")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs for request tracing."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID."""
        
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging and timing."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details and timing."""
        
        start_time = time.time()
        
        # Log incoming request
        log_with_context(
            logger,
            "info",
            "Incoming request",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            log_with_context(
                logger,
                "info",
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=round(process_time, 3),
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(round(process_time, 3))
            
            return response
            
        except Exception as e:
            # Calculate processing time for errors too
            process_time = time.time() - start_time
            
            # Log error
            log_with_context(
                logger,
                "error",
                "Request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                process_time=round(process_time, 3),
            )
            
            raise


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for global exception handling."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle exceptions globally."""
        
        try:
            return await call_next(request)
            
        except BaseRAGException as e:
            # Handle custom exceptions
            log_with_context(
                logger,
                "warning",
                "Application exception",
                error_code=e.error_code,
                message=e.message,
                details=e.details,
            )
            
            http_exc = map_to_http_exception(e)
            return JSONResponse(
                status_code=http_exc.status_code,
                content=http_exc.detail
            )
            
        except Exception as e:
            # Handle unexpected exceptions
            log_with_context(
                logger,
                "error",
                "Unhandled exception",
                error=str(e),
                error_type=type(e).__name__,
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "correlation_id": request.headers.get("X-Correlation-ID"),
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to responses."""
        
        response = await call_next(request)
        
        # Add security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response